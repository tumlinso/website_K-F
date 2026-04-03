from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from .models import Contact


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_RECIPIENT_EMAIL='studio@example.com',
    DEFAULT_FROM_EMAIL='noreply@example.com',
    CONTACT_AUTORESPONDER_ENABLED=False,
    RECAPTCHA_SITE_KEY='test-site-key',
    RECAPTCHA_SECRET_KEY='test-secret-key',
    RECAPTCHA_ENABLED=True,
)
class ContactViewTests(TestCase):
    @patch('gym_app.views._verify_contact_recaptcha', return_value=(True, None))
    def test_valid_submission_saves_contact_and_sends_admin_email_only_when_autoresponder_disabled(
        self,
        _mock_recaptcha,
    ):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
                'g-recaptcha-response': 'test-token',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['studio@example.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['max@example.com'])

    @override_settings(CONTACT_AUTORESPONDER_ENABLED=True)
    @patch('gym_app.views._verify_contact_recaptcha', return_value=(True, None))
    def test_valid_submission_saves_contact_and_sends_two_emails_when_autoresponder_enabled(
        self,
        _mock_recaptcha,
    ):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
                'g-recaptcha-response': 'test-token',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ['studio@example.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['max@example.com'])
        self.assertEqual(mail.outbox[1].to, ['max@example.com'])

    @patch('gym_app.views._verify_contact_recaptcha', return_value=(True, None))
    def test_invalid_submission_shows_errors_without_sending_email(self, _mock_recaptcha):
        response = self.client.post(
            reverse('contact'),
            {
                'name': '',
                'email': 'invalid-email',
                'message': '',
                'g-recaptcha-response': 'test-token',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bitte prüfen Sie die markierten Felder.')
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch(
        'gym_app.views._verify_contact_recaptcha',
        return_value=(False, 'Bitte bestätigen Sie, dass Sie kein Roboter sind.'),
    )
    def test_invalid_captcha_blocks_submission_and_autoresponder(self, _mock_recaptcha):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
                'g-recaptcha-response': 'bad-token',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bitte bestätigen Sie, dass Sie kein Roboter sind.')
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_submission_without_recaptcha_token_is_rejected(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bitte bestätigen Sie, dass Sie kein Roboter sind.')
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(RECAPTCHA_SITE_KEY='', RECAPTCHA_SECRET_KEY='', RECAPTCHA_ENABLED=False)
    def test_get_contact_page_shows_configuration_warning_when_recaptcha_missing(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reCAPTCHA ist noch nicht eingerichtet.')

    @patch('gym_app.views.ContactForm.save', side_effect=Exception('database unavailable'))
    @patch('gym_app.views._verify_contact_recaptcha', return_value=(True, None))
    def test_save_failure_returns_service_unavailable_without_sending_email(
        self,
        _mock_recaptcha,
        _mock_save,
    ):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
                'g-recaptcha-response': 'test-token',
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertContains(
            response,
            'Ihre Nachricht konnte gerade nicht gespeichert werden.',
        )
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
