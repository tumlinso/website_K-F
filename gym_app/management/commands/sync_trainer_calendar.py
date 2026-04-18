from django.core.management.base import BaseCommand, CommandError

from gym_app.autoparse_cal import internal_ics_path, processed_csv_path, sync_calendar
from gym_app.live_status import clear_live_status_calendar_snapshot_cache
from gym_app.trainer_calendar import clear_trainer_calendar_cache


class Command(BaseCommand):
    help = "Sync the trainer calendar from the configured Google Calendar ICS feed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Bypass the freshness window and fetch the feed immediately.",
        )
        parser.add_argument(
            "--reload",
            action="store_true",
            help="Delete local calendar files and reload fresh data from Google Calendar.",
        )

    def handle(self, *args, **options):
        try:
            if options["reload"]:
                for path in (internal_ics_path, processed_csv_path):
                    if path.exists():
                        path.unlink()

                clear_trainer_calendar_cache()
                clear_live_status_calendar_snapshot_cache()

            df = sync_calendar(
                sync_interval_seconds=0 if options["force"] or options["reload"] else None,
            )
        except Exception as exc:
            raise CommandError(f"Calendar sync failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {len(df)} trainer calendar entries."
            )
        )
