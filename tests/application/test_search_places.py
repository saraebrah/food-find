from collections.abc import Sequence
from datetime import datetime

import pytest

from app.application.search_places import (
    SearchPlaces,
    UnsupportedAvailabilityWindowError,
)
from app.domain.location import SelectedLocation
from app.domain.place import (
    Coordinates,
    MatchReason,
    MatchReasonKind,
    OpeningPeriod,
    Place,
)
from app.domain.search import (
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchCriteria,
    SearchFilters,
    SearchSort,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
    DescriptiveRequirementKind,
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
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
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
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
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
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
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
            match_reasons=(
                MatchReason(
                    kind=MatchReasonKind.CONFIRMED,
                    text="Category: Restaurant.",
                ),
                MatchReason(
                    kind=MatchReasonKind.CONFIRMED,
                    text="Inside your selected 2 km radius.",
                ),
                MatchReason(
                    kind=MatchReasonKind.RELEVANCE,
                    text=(
                        "Italian influenced Google text relevance; "
                        "the cuisine is not independently verified."
                    ),
                ),
            ),
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
            match_reasons=(
                MatchReason(
                    kind=MatchReasonKind.CONFIRMED,
                    text="Category: Restaurant.",
                ),
                MatchReason(
                    kind=MatchReasonKind.CONFIRMED,
                    text="Inside your selected 2 km radius.",
                ),
                MatchReason(
                    kind=MatchReasonKind.RELEVANCE,
                    text=(
                        "Italian influenced Google text relevance; "
                        "the cuisine is not independently verified."
                    ),
                ),
            ),
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


class AvailabilityPlaceProvider(RecordingPlaceProvider):
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
    ) -> Sequence[Place]:
        self.searches.append(
            {
                "descriptive_requirements": descriptive_requirements,
                "availability_window": availability_window,
            }
        )
        common = {
            "provider": "google",
            "category": "Restaurant",
            "category_code": "restaurant",
            "address": None,
            "coordinates": Coordinates(latitude=43.6454, longitude=-79.3805),
            "business_status": "operational",
        }
        return [
            Place(
                **common,
                provider_place_id="overlaps",
                name="Open During Part of Tonight",
                opening_periods=(
                    OpeningPeriod(
                        starts_at=datetime.fromisoformat(
                            "2026-07-23T17:00:00-04:00"
                        ),
                        ends_at=datetime.fromisoformat(
                            "2026-07-23T23:00:00-04:00"
                        ),
                    ),
                ),
            ),
            Place(
                **common,
                provider_place_id="before",
                name="Closes Before Tonight",
                opening_periods=(
                    OpeningPeriod(
                        starts_at=datetime.fromisoformat(
                            "2026-07-23T09:00:00-04:00"
                        ),
                        ends_at=datetime.fromisoformat(
                            "2026-07-23T17:00:00-04:00"
                        ),
                    ),
                ),
            ),
            Place(
                **common,
                provider_place_id="missing",
                name="Hours Missing",
                opening_periods=None,
            ),
        ]


class ConfirmedFilterPlaceProvider(RecordingPlaceProvider):
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
    ) -> Sequence[Place]:
        self.searches.append(
            {
                "filters": filters,
                "descriptive_requirements": descriptive_requirements,
            }
        )
        return [
            Place(
                provider="google",
                provider_place_id="confirmed",
                name="Confirmed Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address=None,
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
                business_status="operational",
                open_now=True,
                rating=4.6,
            )
        ]


@pytest.mark.anyio
async def test_reviewed_requirements_reach_provider_and_availability_is_confirmed() -> None:
    provider = AvailabilityPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    requirement = DescriptiveRequirement(
        text="quiet atmosphere",
        kind=DescriptiveRequirementKind.ATMOSPHERE,
    )
    window = AvailabilityWindow(
        starts_at=datetime.fromisoformat("2026-07-23T18:00:00-04:00"),
        ends_at=datetime.fromisoformat("2026-07-24T00:00:00-04:00"),
    )
    criteria = SearchCriteria(
        location=SelectedLocation(
            label="Union Station coordinates",
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        ),
        radius_meters=2_000,
    )

    places = await search.execute(
        criteria=criteria,
        descriptive_requirements=(requirement,),
        availability_window=window,
        current_datetime=datetime.fromisoformat(
            "2026-07-23T12:00:00-04:00"
        ),
    )

    assert [place.provider_place_id for place in places] == ["overlaps"]
    assert places[0].match_reasons == (
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Category: Restaurant.",
        ),
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Inside your selected 2 km radius.",
        ),
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Google hours overlap your requested time.",
        ),
        MatchReason(
            kind=MatchReasonKind.RELEVANCE,
            text=(
                "“quiet atmosphere” influenced Google text relevance; "
                "it is not independently verified."
            ),
        ),
    )
    assert provider.searches == [
        {
            "descriptive_requirements": (requirement,),
            "availability_window": window,
        }
    ]


@pytest.mark.anyio
async def test_exact_availability_time_must_fall_inside_an_opening_period() -> None:
    provider = AvailabilityPlaceProvider()
    search = SearchPlaces(place_provider=provider)
    exact_time = datetime.fromisoformat("2026-07-23T23:00:00-04:00")

    places = await search.execute(
        criteria=SearchCriteria(
            location=SelectedLocation(
                label="Union Station coordinates",
                coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
            ),
            radius_meters=2_000,
        ),
        availability_window=AvailabilityWindow(
            starts_at=exact_time,
            ends_at=exact_time,
        ),
        current_datetime=datetime.fromisoformat(
            "2026-07-23T12:00:00-04:00"
        ),
    )

    assert places == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    "window",
    (
        AvailabilityWindow(
            starts_at=datetime.fromisoformat("2026-07-22T18:00:00-04:00"),
            ends_at=datetime.fromisoformat("2026-07-22T22:00:00-04:00"),
        ),
        AvailabilityWindow(
            starts_at=datetime.fromisoformat("2026-07-29T18:00:00-04:00"),
            ends_at=datetime.fromisoformat("2026-07-30T00:00:00-04:00"),
        ),
    ),
)
async def test_unsupported_availability_does_not_call_provider(
    window: AvailabilityWindow,
) -> None:
    provider = AvailabilityPlaceProvider()

    with pytest.raises(
        UnsupportedAvailabilityWindowError,
        match="seven-day",
    ):
        await SearchPlaces(place_provider=provider).execute(
            criteria=SearchCriteria(
                location=SelectedLocation(
                    label="Union Station coordinates",
                    coordinates=Coordinates(
                        latitude=43.6453,
                        longitude=-79.3806,
                    ),
                ),
                radius_meters=2_000,
            ),
            availability_window=window,
            current_datetime=datetime.fromisoformat(
                "2026-07-23T12:00:00-04:00"
            ),
        )

    assert provider.searches == []


@pytest.mark.anyio
async def test_match_reasons_use_active_confirmed_filters_without_extra_calls() -> None:
    provider = ConfirmedFilterPlaceProvider()
    search = SearchPlaces(place_provider=provider)

    places = await search.execute(
        criteria=SearchCriteria(
            location=SelectedLocation(
                label="Union Station coordinates",
                coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
            ),
            radius_meters=2_000,
            filters=SearchFilters(
                open_now=True,
                minimum_rating=MinimumRating.FOUR,
            ),
        ),
        descriptive_requirements=(
            DescriptiveRequirement(
                text="serves kebab",
                kind=DescriptiveRequirementKind.DISH,
            ),
        ),
    )

    assert len(provider.searches) == 1
    assert places[0].match_reasons == (
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Category: Restaurant.",
        ),
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Inside your selected 2 km radius.",
        ),
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Google reports this place open now.",
        ),
        MatchReason(
            kind=MatchReasonKind.CONFIRMED,
            text="Google rating 4.6 meets your 4.0 minimum.",
        ),
        MatchReason(
            kind=MatchReasonKind.RELEVANCE,
            text=(
                "“serves kebab” influenced Google text relevance; "
                "availability is not verified—check the menu or call."
            ),
        ),
    )
