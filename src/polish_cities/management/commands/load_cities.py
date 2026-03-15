import csv
import io
import urllib.request
import zipfile

from django.core.management.base import BaseCommand

from polish_cities.models import PolishCity
from announcements.geocoding import haversine

DUMP_URL = "https://download.geonames.org/export/dump/PL.zip"
POSTAL_URL = "https://download.geonames.org/export/zip/PL.zip"

FEATURE_CODE_PRIORITY = ["PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPL"]

# GeoNames admin1 code → Polish voivodeship name
ADMIN1_MAP = {
    "72": "dolnośląskie",
    "73": "kujawsko-pomorskie",
    "74": "łódzkie",
    "75": "lubelskie",
    "76": "lubuskie",
    "77": "małopolskie",
    "78": "mazowieckie",
    "79": "opolskie",
    "80": "podkarpackie",
    "81": "podlaskie",
    "82": "pomorskie",
    "83": "śląskie",
    "84": "świętokrzyskie",
    "85": "warmińsko-mazurskie",
    "86": "wielkopolskie",
    "87": "zachodniopomorskie",
}


def is_latin(name: str) -> bool:
    return bool(_LATIN_RE.match(name))


class Command(BaseCommand):
    help = "Load Polish populated places from GeoNames dump PL.zip, then enrich with postal codes"

    def handle(self, *args, **options):
        # ── Phase 1: place names ──────────────────────────────────────────────
        self.stdout.write("Downloading PL.zip from GeoNames dump...")
        with urllib.request.urlopen(DUMP_URL) as response:
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
            try:
                population = int(row[14]) if len(row) > 14 and row[14].strip() else None
            except (ValueError, IndexError):
                population = None

            admin1_code = row[10].strip() if len(row) > 10 else ""
            admin1 = ADMIN1_MAP.get(admin1_code, "")

            to_create.append(PolishCity(
                name=name, lat=lat, lng=lng,
                feature_code=feature_code, population=population,
                admin1=admin1,
            ))

        self.stdout.write("Clearing existing records...")
        PolishCity.objects.all().delete()

        self.stdout.write(f"Inserting {len(to_create)} records...")
        created = PolishCity.objects.bulk_create(to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Done. Inserted {len(created)} records."))

        # ── Phase 2: postal codes ─────────────────────────────────────────────
        self.stdout.write("Downloading postal codes from GeoNames zip/PL.zip...")
        with urllib.request.urlopen(POSTAL_URL) as response:
            postal_zip_data = response.read()

        with zipfile.ZipFile(io.BytesIO(postal_zip_data)) as zf:
            with zf.open("PL.txt") as f:
                postal_content = f.read().decode("utf-8")

        # Build in-memory lookup: name_lower → list of city dicts
        all_cities = list(PolishCity.objects.values("id", "name", "lat", "lng"))
        city_by_name: dict = {}
        for c in all_cities:
            key = c["name"].lower()
            city_by_name.setdefault(key, []).append(c)

        self.stdout.write(f"Matching postal codes to {len(all_cities)} cities...")
        postal_reader = csv.reader(io.StringIO(postal_content), delimiter="\t")
        updates: dict = {}  # city_id → postal_code

        for row in postal_reader:
            if len(row) < 11:
                continue
            postal_code = row[1].strip()
            place_name = row[2].strip()
            try:
                plat = float(row[9])
                plng = float(row[10])
            except (ValueError, IndexError):
                continue

            for c in city_by_name.get(place_name.lower(), []):
                if haversine(plat, plng, c["lat"], c["lng"]) < 5.0:
                    if c["id"] not in updates:
                        updates[c["id"]] = postal_code
                    break

        cities_to_update = [
            PolishCity(id=city_id, postal_code=code)
            for city_id, code in updates.items()
        ]
        PolishCity.objects.bulk_update(cities_to_update, ["postal_code"], batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f"Assigned postal codes to {len(cities_to_update)} cities."
        ))
