import re
from typing import List, Optional

from ninja_extra import api_controller, http_get
from ninja import Schema

from .models import PolishCity
from announcements.geocoding import haversine

NEAREST_FEATURE_CODES = {"PPLA", "PPLA2", "PPLA3", "PPLC", "PPL"}
POSTAL_RE = re.compile(r"^\d{2}-\d{3}$")


class CityOptionSchema(Schema):
    name: str
    admin1: str
    lat: float
    lng: float


class NearestCitySchema(Schema):
    name: str
    admin1: str
    lat: float
    lng: float
    distance_km: float


@api_controller("/cities", tags=["Cities"])
class PolishCitiesController:

    @http_get("/autocomplete", response=List[CityOptionSchema])
    def autocomplete(self, q: str = "") -> List[CityOptionSchema]:
        if POSTAL_RE.match(q):
            candidates = list(
                PolishCity.objects.filter(postal_code=q)
                .order_by("name", "admin1", "-population")
                .values("name", "admin1", "lat", "lng", "population")[:80]
            )
        elif len(q) < 2:
            return []
        else:
            candidates = list(
                PolishCity.objects.filter(name__istartswith=q)
                .order_by("name", "admin1", "-population")
                .values("name", "admin1", "lat", "lng", "population")[:80]
            )

        seen: set = set()
        results = []
        for c in candidates:
            key = (c["name"], c["admin1"])
            if key not in seen:
                seen.add(key)
                results.append(CityOptionSchema(
                    name=c["name"],
                    admin1=c["admin1"],
                    lat=c["lat"],
                    lng=c["lng"],
                ))
            if len(results) >= 8:
                break

        return results

    @http_get("/nearest", response=Optional[NearestCitySchema], auth=None)
    def nearest(self, lat: float, lng: float) -> Optional[NearestCitySchema]:
        candidates = list(
            PolishCity.objects.filter(
                feature_code__in=NEAREST_FEATURE_CODES,
                population__gt=500,
            ).values("name", "admin1", "lat", "lng")
        )
        if not candidates:
            return None

        best = min(candidates, key=lambda c: haversine(lat, lng, c["lat"], c["lng"]))
        dist = haversine(lat, lng, best["lat"], best["lng"])
        return NearestCitySchema(
            name=best["name"],
            admin1=best["admin1"],
            lat=best["lat"],
            lng=best["lng"],
            distance_km=round(dist, 1),
        )
