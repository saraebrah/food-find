from collections.abc import Sequence

from app.application.search_places import (
    DEFAULT_SEARCH_TYPES,
    SearchPlaces,
)
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates, Place
from app.domain.search import SearchCriteria
from app.ports.place_provider import PlaceProvider


TORONTO_CITY_HALL = Coordinates(latitude=43.6532, longitude=-79.3832)
TORONTO_SEARCH_RADIUS_METERS = 1_000
TORONTO_SEARCH_TYPES = DEFAULT_SEARCH_TYPES


class SearchFixedTorontoPlaces:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._search = SearchPlaces(place_provider=place_provider)

    async def execute(self) -> Sequence[Place]:
        return await self._search.execute(
            criteria=SearchCriteria(
                location=SelectedLocation(
                    label="Toronto City Hall",
                    coordinates=TORONTO_CITY_HALL,
                ),
                radius_meters=TORONTO_SEARCH_RADIUS_METERS,
            )
        )
