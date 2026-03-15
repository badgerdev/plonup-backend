from django.core.management.base import BaseCommand

from announcements.geocoding import geocode_city
from announcements.models import Announcement


class Command(BaseCommand):
    help = "Backfill lat/lng for announcements missing geocoordinates. Use --force to re-geocode all."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-geocode all announcements, not just those with missing coordinates",
        )

    def handle(self, *args, **options):
        qs = Announcement.objects.all() if options["force"] else Announcement.objects.filter(lat__isnull=True)
        total = qs.count()
        self.stdout.write(f"Processing {total} announcements...")

        updated = 0
        skipped = 0
        for ann in qs:
            coords = geocode_city(ann.location)
            if coords:
                ann.lat, ann.lng = coords
                ann.save(update_fields=["lat", "lng"])
                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Updated: {updated}, skipped (city not found): {skipped}."
        ))
