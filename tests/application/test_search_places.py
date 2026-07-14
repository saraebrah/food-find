from collections.abc import Sequence

import pytest

from app.application.search_places import (
    DEFAULT_SEARCH_TYPES,
    SearchPlaces,
)
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates, Place
from app.domain.search import SearchCriteria


class RecordingPlaceProvider:
    def __init__(self) -> None:
        self.searches: list[dict[str, object]] = []

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> Sequence[Place]:
        self.searches.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "included_types": tuple(included_types),
            }
        )
        return []


@pytest.mark.anyio
async def test_search_uses_selected_location_coordinates() -> None:
    provider = RecordingPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    location = SelectedLocation(
        label="Union Station coordinates",
        coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
    )
    criteria = SearchCriteria(location=location, radius_meters=2_000)

    places = await search.execute(criteria=criteria)

    assert places == []
    assert provider.searches == [
        {
            "latitude": 43.6453,
            "longitude": -79.3806,
            "radius_meters": 2_000,
            "included_types": DEFAULT_SEARCH_TYPES,
        }
    ]
