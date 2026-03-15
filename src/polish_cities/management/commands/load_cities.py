import csv
import io
import urllib.request
import zipfile

from django.core.management.base import BaseCommand

from polish_cities.models import PolishCity

ZIP_URL = "https://download.geonames.org/export/dump/PL.zip"

import re

# Priority order for disambiguation (lower index = higher priority)
FEATURE_CODE_PRIORITY = ["PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPL"]

# Latin script + Polish diacritics — excludes Cyrillic, Arabic, CJK etc.
_LATIN_RE = re.compile(r"^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-\.\']+$")


def is_latin(name: str) -> bool:
    return bool(_LATIN_RE.match(name))


class Command(BaseCommand):
    help = "Load Polish populated places from GeoNames dump PL.zip"

    def handle(self, *args, **options):
        self.stdout.write("Downloading PL.zip from GeoNames dump...")
        with urllib.request.urlopen(ZIP_URL) as response:
            zip_data = response.read()

        self.stdout.write("Extracting PL.txt...")
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            with zf.open("PL.txt") as f:
                content = f.read().decode("utf-8")

        reader = csv.reader(io.StringIO(content), delimiter="\t")

        to_create = []
        for row in reader:
            if len(row) < 8 or row[6] != "P":
                continue

            name = row[1]
            lat = float(row[4])
            lng = float(row[5])
            feature_code = row[7]
            alternates = [a.strip() for a in row[3].split(",") if a.strip()] if row[3] else []

            # Always import the main name
            to_create.append(PolishCity(name=name, lat=lat, lng=lng, feature_code=feature_code))

            # Also import Polish alternate names (e.g. "Warszawa" when main is "Warsaw")
            for alt in alternates:
                if is_latin(alt) and alt != name:
                    to_create.append(PolishCity(name=alt, lat=lat, lng=lng, feature_code=feature_code))

        self.stdout.write(f"Inserting {len(to_create)} records...")
        created = PolishCity.objects.bulk_create(to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f"Done. Inserted {len(created)} records (duplicates skipped)."
        ))
