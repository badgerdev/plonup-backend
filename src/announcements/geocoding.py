import math
from typing import Optional, Tuple

FEATURE_CODE_PRIORITY = ["PPLC", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPL"]


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Returns distance in km between two lat/lng points."""
    R = 6371.0
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def geocode_city(city_name: str, postal_code: str = "") -> Optional[Tuple[float, float]]:
    """
    Returns (lat, lng) for a Polish city name.

    Disambiguation strategy:
    1. Prefer by feature_code priority: PPLC > PPLA > PPLA2 > PPLA3 > PPLA4 > PPL
    2. When multiple PPL candidates share a name, pick the one with the highest
       population — this correctly resolves ambiguous village names (e.g. "Iłowa"
       near Żagań vs small hamlets with the same name elsewhere).
    """
    from polish_cities.models import PolishCity

    candidates = list(
        PolishCity.objects.filter(name__iexact=city_name)
        .values("lat", "lng", "feature_code", "population")
    )
    if not candidates:
        return None

    for code in FEATURE_CODE_PRIORITY:
        matches = [c for c in candidates if c["feature_code"] == code]
        if matches:
            # Among same feature_code, prefer highest population
            best = max(matches, key=lambda c: c["population"] or 0)
            return (best["lat"], best["lng"])

    # Fallback: highest population overall
    best = max(candidates, key=lambda c: c["population"] or 0)
    return (best["lat"], best["lng"])
