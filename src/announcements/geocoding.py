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


def geocode_city(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Returns (lat, lng) for a Polish city name.

    Disambiguation strategy: when multiple places share a name, prefer by
    feature_code priority: PPLC > PPLA > PPLA2 > PPLA3 > PPLA4 > PPL.
    This ensures e.g. "Zielona Góra" (PPLA - province capital) wins over
    a small village of the same name.
    """
    from polish_cities.models import PolishCity

    candidates = list(
        PolishCity.objects.filter(name__iexact=city_name).values("lat", "lng", "feature_code")
    )
    if not candidates:
        return None

    for code in FEATURE_CODE_PRIORITY:
        matches = [c for c in candidates if c["feature_code"] == code]
        if matches:
            return (matches[0]["lat"], matches[0]["lng"])

    # Fallback: first record
    return (candidates[0]["lat"], candidates[0]["lng"])
