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
        return [
            Place(
                provider="google",
                provider_place_id="google-place-1",
                name="Example Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="1 Front Street, Toronto, ON",
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
            ),
            Place(
                provider="google",
                provider_place_id="google-place-2",
                name="Temporarily Closed Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="2 Front Street, Toronto, ON",
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="temporarily_closed",
            ),
            Place(
                provider="google",
                provider_place_id="google-place-3",
                name="Permanently Closed Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="3 Front Street, Toronto, ON",
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="permanently_closed",
            ),
            Place(
                provider="google",
                provider_place_id="google-place-4",
                name="Unconfirmed Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="4 Front Street, Toronto, ON",
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status=None,
            ),
        ]


@pytest.mark.anyio
async def test_search_uses_selected_location_and_adds_distance() -> None:
    provider = RecordingPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    location = SelectedLocation(
        label="Union Station coordinates",
        coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
    )
    criteria = SearchCriteria(location=location, radius_meters=2_000)

    places = await search.execute(criteria=criteria)

    assert places == [
        Place(
            provider="google",
            provider_place_id="google-place-1",
            name="Example Restaurant",
            category="Restaurant",
            category_code="restaurant",
            address="1 Front Street, Toronto, ON",
            coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
            business_status="operational",
            distance_meters=14,
        ),
        Place(
            provider="google",
            provider_place_id="google-place-4",
            name="Unconfirmed Restaurant",
            category="Restaurant",
            category_code="restaurant",
            address="4 Front Street, Toronto, ON",
            coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
            business_status=None,
            distance_meters=14,
        ),
    ]
    assert provider.searches == [
        {
            "latitude": 43.6453,
            "longitude": -79.3806,
            "radius_meters": 2_000,
            "included_types": DEFAULT_SEARCH_TYPES,
        }
    ]
