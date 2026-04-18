import os
from io import StringIO
from pathlib import Path
import tempfile

import pandas as pd
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.conf import settings as django_settings
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from . import live_status, trainer_calendar
from .autoparse_cal import sync_calendar
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


class DiscoverPageTests(TestCase):
    def test_entdecken_renders_trainer_cards_with_quotes(self):
        response = self.client.get(reverse('entdecken'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gavin Tumlinson')
        self.assertContains(response, 'Alea iacta est.')
        self.assertContains(response, 'trainer/Gavin/B9D9DC3A-70D5-4992-8CF5-737C1EAD49DE.jpeg')


class CalendarSyncTests(TestCase):
    def test_sync_calendar_uses_env_google_calendar_url_and_15_min_default(self):
        calendar_df = pd.DataFrame(
            [
                {
                    'name': 'Felix Gansmeier',
                    'start': pd.Timestamp('2026-04-01T10:00:00Z'),
                    'end': pd.Timestamp('2026-04-01T12:00:00Z'),
                }
            ]
        )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            internal_ics_path = Path(temp_dir) / 'calendar.ics'
            processed_csv_path = Path(temp_dir) / 'processed_calendar.csv'

            with patch.dict(
                os.environ,
                {
                    'TRAINER_CALENDAR_ICS_URL': 'https://calendar.google.com/calendar/ical/test/basic.ics',
                    'TRAINER_CALENDAR_TIMEOUT_SECONDS': '7.5',
                },
                clear=False,
            ), patch(
                'gym_app.autoparse_cal._file_is_fresh',
                return_value=False,
            ) as mock_file_is_fresh, patch(
                'gym_app.autoparse_cal.download_web_calendar_ics',
                return_value=True,
            ) as mock_download, patch(
                'gym_app.autoparse_cal.parse_ics_file',
                return_value=calendar_df,
            ):
                result = sync_calendar(
                    internal_ics_path=internal_ics_path,
                    processed_csv=processed_csv_path,
                )
                self.assertTrue(processed_csv_path.exists())

        mock_file_is_fresh.assert_called_once_with(processed_csv_path, 900)
        mock_download.assert_called_once_with(
            'https://calendar.google.com/calendar/ical/test/basic.ics',
            internal_ics_path,
        )
        self.assertEqual(len(result), 1)


class CalendarSyncCommandTests(TestCase):
    @patch('gym_app.management.commands.sync_trainer_calendar.warm_live_status_calendar_snapshot_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.warm_trainer_calendar_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.clear_live_status_calendar_snapshot_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.clear_trainer_calendar_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.sync_calendar')
    def test_force_command_bypasses_freshness_window(
        self,
        mock_sync_calendar,
        mock_clear_trainer_cache,
        mock_clear_live_status_cache,
        mock_warm_trainer_cache,
        mock_warm_live_status_cache,
    ):
        mock_sync_calendar.return_value = pd.DataFrame(
            [
                {
                    'name': 'Felix Gansmeier',
                    'start': pd.Timestamp('2026-04-01T10:00:00Z'),
                    'end': pd.Timestamp('2026-04-01T12:00:00Z'),
                }
            ]
        )
        stdout = StringIO()

        call_command('sync_trainer_calendar', '--force', stdout=stdout)

        mock_sync_calendar.assert_called_once_with(sync_interval_seconds=0)
        mock_clear_trainer_cache.assert_called_once_with()
        mock_clear_live_status_cache.assert_called_once_with()
        mock_warm_trainer_cache.assert_called_once_with()
        mock_warm_live_status_cache.assert_called_once_with()
        self.assertIn('Synced 1 trainer calendar entries.', stdout.getvalue())

    @patch('gym_app.management.commands.sync_trainer_calendar.warm_live_status_calendar_snapshot_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.warm_trainer_calendar_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.clear_live_status_calendar_snapshot_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.clear_trainer_calendar_cache')
    @patch('gym_app.management.commands.sync_trainer_calendar.sync_calendar')
    def test_reload_command_clears_files_and_forces_fresh_sync(
        self,
        mock_sync_calendar,
        mock_clear_trainer_cache,
        mock_clear_live_status_cache,
        mock_warm_trainer_cache,
        mock_warm_live_status_cache,
    ):
        mock_sync_calendar.return_value = pd.DataFrame(columns=['name', 'start', 'end'])

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            internal_ics = Path(temp_dir) / 'calendar.ics'
            processed_csv = Path(temp_dir) / 'processed_calendar.csv'
            internal_ics.write_text('old ics', encoding='utf-8')
            processed_csv.write_text('name,start,end\n', encoding='utf-8')
            stdout = StringIO()

            with patch(
                'gym_app.management.commands.sync_trainer_calendar.internal_ics_path',
                internal_ics,
            ), patch(
                'gym_app.management.commands.sync_trainer_calendar.processed_csv_path',
                processed_csv,
            ):
                call_command('sync_trainer_calendar', '--reload', stdout=stdout)

            self.assertFalse(internal_ics.exists())
            self.assertFalse(processed_csv.exists())

        mock_clear_trainer_cache.assert_called_once_with()
        mock_clear_live_status_cache.assert_called_once_with()
        mock_sync_calendar.assert_called_once_with(sync_interval_seconds=0)
        mock_warm_trainer_cache.assert_called_once_with()
        mock_warm_live_status_cache.assert_called_once_with()
        self.assertIn('Synced 0 trainer calendar entries.', stdout.getvalue())

class CacheSettingsTests(TestCase):
    def test_default_cache_uses_filebased_backend(self):
        self.assertEqual(
            django_settings.CACHES['default']['BACKEND'],
            'django.core.cache.backends.filebased.FileBasedCache',
        )


@override_settings(GYM_TIMEZONE='UTC', TRAINER_CALENDAR_VIEW_DAYS=10)
class CalendarCacheInvalidationTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_trainer_calendar_cache_refreshes_when_processed_csv_changes(self):
        now = pd.Timestamp.now(tz='UTC')
        first_df = pd.DataFrame(
            [
                {
                    'name': 'Thomas Gansmeier',
                    'start': now + pd.Timedelta(hours=1),
                    'end': now + pd.Timedelta(hours=2),
                }
            ]
        )
        second_df = pd.DataFrame(
            [
                {
                    'name': 'Gavin Tumlinson',
                    'start': now + pd.Timedelta(hours=3),
                    'end': now + pd.Timedelta(hours=4),
                }
            ]
        )

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            processed_csv = Path(temp_dir) / 'processed_calendar.csv'
            processed_csv.write_text('first', encoding='utf-8')

            with patch(
                'gym_app.trainer_calendar.processed_csv_path',
                processed_csv,
            ), patch(
                'gym_app.trainer_calendar._load_calendar_df',
                side_effect=[first_df, second_df],
            ) as mock_load_calendar_df:
                first_result = trainer_calendar.get_trainer_calendar_days(limit_days=10)
                processed_csv.write_text('second', encoding='utf-8')
                second_result = trainer_calendar.get_trainer_calendar_days(limit_days=10)

        first_day_with_events = next(day for day in first_result if day['events'])
        second_day_with_events = next(day for day in second_result if day['events'])

        self.assertEqual(mock_load_calendar_df.call_count, 2)
        self.assertEqual(first_day_with_events['events'][0]['trainer_name'], 'Thomas')
        self.assertEqual(second_day_with_events['events'][0]['trainer_name'], 'Gavin')

    def test_live_status_cache_refreshes_when_processed_csv_changes(self):
        first_snapshot = {'state': 'ok', 'events': [{'summary': 'Felix Gansmeier'}]}
        second_snapshot = {'state': 'ok', 'events': [{'summary': 'Thomas Gansmeier'}]}

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            processed_csv = Path(temp_dir) / 'processed_calendar.csv'
            processed_csv.write_text('first', encoding='utf-8')

            with patch(
                'gym_app.live_status.processed_csv_path',
                processed_csv,
            ), patch(
                'gym_app.live_status._get_dataframe_calendar_snapshot',
                side_effect=[first_snapshot, second_snapshot],
            ) as mock_get_snapshot:
                first_result = live_status._get_calendar_snapshot()
                processed_csv.write_text('second', encoding='utf-8')
                second_result = live_status._get_calendar_snapshot()

        self.assertEqual(mock_get_snapshot.call_count, 2)
        self.assertEqual(first_result['events'][0]['summary'], 'Felix Gansmeier')
        self.assertEqual(second_result['events'][0]['summary'], 'Thomas Gansmeier')
