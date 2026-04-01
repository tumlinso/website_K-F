from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from .models import Contact


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CONTACT_RECIPIENT_EMAIL='studio@example.com',
    DEFAULT_FROM_EMAIL='noreply@example.com',
)
class ContactViewTests(TestCase):
    def test_valid_submission_saves_contact_and_sends_two_emails(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ['studio@example.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['max@example.com'])
        self.assertEqual(mail.outbox[1].to, ['max@example.com'])

    def test_invalid_submission_shows_errors_without_sending_email(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': '',
                'email': 'invalid-email',
                'message': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bitte prüfen Sie die markierten Felder.')
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @patch('gym_app.views.ContactForm.save', side_effect=Exception('database unavailable'))
    def test_save_failure_returns_service_unavailable_without_sending_email(self, _mock_save):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Max Mustermann',
                'email': 'max@example.com',
                'message': 'Ich interessiere mich für eine Mitgliedschaft.',
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertContains(
            response,
            'Ihre Nachricht konnte gerade nicht gespeichert werden.',
        )
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)
