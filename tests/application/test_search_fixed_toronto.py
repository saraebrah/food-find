from collections.abc import Sequence

import pytest

from app.application.search_fixed_toronto import (
    TORONTO_CITY_HALL,
    TORONTO_SEARCH_RADIUS_METERS,
    TORONTO_SEARCH_TYPES,
    SearchFixedTorontoPlaces,
)
from app.domain.place import Place


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
async def test_fixed_toronto_search_calls_provider_once_with_fixed_criteria() -> None:
    provider = RecordingPlaceProvider()
    search = SearchFixedTorontoPlaces(place_provider=provider)

    places = await search.execute()

    assert places == []
    assert provider.searches == [
        {
            "latitude": TORONTO_CITY_HALL.latitude,
            "longitude": TORONTO_CITY_HALL.longitude,
            "radius_meters": TORONTO_SEARCH_RADIUS_METERS,
            "included_types": TORONTO_SEARCH_TYPES,
        }
    ]
