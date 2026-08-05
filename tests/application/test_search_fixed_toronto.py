import pytest

from app.application.search_fixed_toronto import (
    TORONTO_CITY_HALL,
    TORONTO_SEARCH_RADIUS_METERS,
    SearchFixedTorontoPlaces,
)
from app.domain.search import SearchFilters, SearchSort
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
)
from app.ports.place_provider import PlaceSearchPage


class RecordingPlaceProvider:
    def __init__(self) -> None:
        self.searches: list[dict[str, object]] = []

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
        continuation_token: str | None = None,
    ) -> PlaceSearchPage:
        self.searches.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "filters": filters,
                "sort": sort,
            }
        )
        return PlaceSearchPage(places=())


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
            "filters": SearchFilters(),
            "sort": SearchSort.PROVIDER_DEFAULT,
        }
    ]
