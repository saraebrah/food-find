from collections.abc import Sequence

from app.domain.place import Coordinates, Place
from app.ports.place_provider import PlaceProvider


TORONTO_CITY_HALL = Coordinates(latitude=43.6532, longitude=-79.3832)
TORONTO_SEARCH_RADIUS_METERS = 1_000
TORONTO_SEARCH_TYPES = ("restaurant", "cafe")


class SearchFixedTorontoPlaces:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._place_provider = place_provider

    async def execute(self) -> Sequence[Place]:
        return await self._place_provider.search_nearby(
            latitude=TORONTO_CITY_HALL.latitude,
            longitude=TORONTO_CITY_HALL.longitude,
            radius_meters=TORONTO_SEARCH_RADIUS_METERS,
            included_types=TORONTO_SEARCH_TYPES,
        )
