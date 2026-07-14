from collections.abc import Sequence

from app.domain.place import Place
from app.domain.search import SearchCriteria
from app.ports.place_provider import PlaceProvider


DEFAULT_SEARCH_TYPES = ("restaurant", "cafe")


class SearchPlaces:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._place_provider = place_provider

    async def execute(self, *, criteria: SearchCriteria) -> Sequence[Place]:
        return await self._place_provider.search_nearby(
            latitude=criteria.location.coordinates.latitude,
            longitude=criteria.location.coordinates.longitude,
            radius_meters=criteria.radius_meters,
            included_types=DEFAULT_SEARCH_TYPES,
        )
