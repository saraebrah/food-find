from collections.abc import Sequence

import pytest

from app.application.search_places import SearchPlaces
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates, Place
from app.domain.search import (
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchCriteria,
    SearchFilters,
    SearchSort,
)


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
    ) -> Sequence[Place]:
        self.searches.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "filters": filters,
                "sort": sort,
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
                open_now=True,
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
                open_now=True,
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
                open_now=True,
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
                open_now=None,
            ),
            Place(
                provider="google",
                provider_place_id="outside-radius",
                name="Outside Radius Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="Outside the selected area",
                coordinates=Coordinates(latitude=43.70, longitude=-79.3805),
                business_status="operational",
                open_now=True,
            ),
        ]


class RatingPlaceProvider(RecordingPlaceProvider):
    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
    ) -> Sequence[Place]:
        self.searches.append({"filters": filters, "sort": sort})
        return [
            Place(
                provider="google",
                provider_place_id="rated-3-5",
                name="Rated 3.5",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                rating=3.5,
            ),
            Place(
                provider="google",
                provider_place_id="rated-4-8",
                name="Rated 4.8",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                rating=4.8,
            ),
            Place(
                provider="google",
                provider_place_id="unrated",
                name="Unrated",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                rating=None,
            ),
        ]


class ServicePlaceProvider(RecordingPlaceProvider):
    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
    ) -> Sequence[Place]:
        self.searches.append({"filters": filters, "sort": sort})
        return [
            Place(
                provider="google",
                provider_place_id="both",
                name="Both services",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                dine_in=True,
                takeout=True,
            ),
            Place(
                provider="google",
                provider_place_id="takeout-only",
                name="Takeout only",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                dine_in=False,
                takeout=True,
            ),
            Place(
                provider="google",
                provider_place_id="unknown",
                name="Unknown services",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                dine_in=None,
                takeout=None,
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
    criteria = SearchCriteria(
        location=location,
        radius_meters=2_000,
        filters=SearchFilters(
            place_types=(PlaceType.BAR, PlaceType.BAKERY),
            cuisines=(Cuisine.ITALIAN,),
        ),
        sort=SearchSort.DISTANCE,
    )

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
            open_now=True,
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
            open_now=None,
            distance_meters=14,
        ),
    ]
    assert provider.searches == [
        {
            "latitude": 43.6453,
            "longitude": -79.3806,
            "radius_meters": 2_000,
            "filters": criteria.filters,
            "sort": SearchSort.DISTANCE,
        }
    ]


@pytest.mark.anyio
async def test_open_now_keeps_only_places_explicitly_reported_open() -> None:
    provider = RecordingPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    criteria = SearchCriteria(
        location=SelectedLocation(
            label="Union Station coordinates",
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        ),
        radius_meters=2_000,
        filters=SearchFilters(open_now=True),
    )

    places = await search.execute(criteria=criteria)

    assert [place.provider_place_id for place in places] == ["google-place-1"]
    assert provider.searches[0]["filters"] == criteria.filters
    assert provider.searches == [
        {
            "latitude": 43.6453,
            "longitude": -79.3806,
            "radius_meters": 2_000,
            "filters": criteria.filters,
            "sort": SearchSort.PROVIDER_DEFAULT,
        }
    ]


@pytest.mark.anyio
async def test_minimum_rating_excludes_lower_and_missing_ratings() -> None:
    provider = RatingPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    criteria = SearchCriteria(
        location=SelectedLocation(
            label="Union Station coordinates",
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        ),
        radius_meters=2_000,
        filters=SearchFilters(minimum_rating=MinimumRating.FOUR),
    )

    places = await search.execute(criteria=criteria)

    assert [place.provider_place_id for place in places] == ["rated-4-8"]


@pytest.mark.anyio
async def test_rating_sort_is_highest_first_with_missing_ratings_last() -> None:
    provider = RatingPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    criteria = SearchCriteria(
        location=SelectedLocation(
            label="Union Station coordinates",
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        ),
        radius_meters=2_000,
        sort=SearchSort.RATING,
    )

    places = await search.execute(criteria=criteria)

    assert [place.provider_place_id for place in places] == [
        "rated-4-8",
        "rated-3-5",
        "unrated",
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filters", "expected_place_ids"),
    (
        (SearchFilters(dine_in=True), ["both"]),
        (SearchFilters(takeout=True), ["both", "takeout-only"]),
        (SearchFilters(dine_in=True, takeout=True), ["both"]),
    ),
)
async def test_service_filters_require_explicit_provider_confirmation(
    filters: SearchFilters,
    expected_place_ids: list[str],
) -> None:
    provider = ServicePlaceProvider()
    search = SearchPlaces(place_provider=provider)
    criteria = SearchCriteria(
        location=SelectedLocation(
            label="Union Station coordinates",
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        ),
        radius_meters=2_000,
        filters=filters,
    )

    places = await search.execute(criteria=criteria)

    assert [place.provider_place_id for place in places] == expected_place_ids
    assert provider.searches == [
        {"filters": filters, "sort": SearchSort.PROVIDER_DEFAULT}
    ]
