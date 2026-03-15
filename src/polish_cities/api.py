from typing import List

from ninja_extra import api_controller, http_get

from .models import PolishCity


@api_controller("/cities", tags=["Cities"])
class PolishCitiesController:

    @http_get("/autocomplete", response=List[str])
    def autocomplete(self, q: str = "") -> List[str]:
        if len(q) < 2:
            return []
        return list(
            PolishCity.objects.filter(name__istartswith=q)
            .values_list("name", flat=True)
            .distinct()[:8]
        )
