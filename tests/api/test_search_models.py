import math

import pytest
from pydantic import ValidationError

from app.api.search_models import SearchPlacesRequest, SelectedLocationRequest
from app.domain.search import (
    CommonFood,
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchCriteria,
    SearchFilters,
    SearchSort,
)


@pytest.mark.parametrize("invalid_value", (math.nan, math.inf, -math.inf))
def test_selected_location_rejects_non_finite_coordinates(
    invalid_value: float,
) -> None:
    with pytest.raises(ValidationError):
        SelectedLocationRequest(
            label="Invalid coordinates",
            latitude=invalid_value,
            longitude=-79.3832,
        )


def test_selected_location_rejects_a_whitespace_only_label() -> None:
    with pytest.raises(ValidationError):
        SelectedLocationRequest(
            label="   ",
            latitude=43.6532,
            longitude=-79.3832,
        )


@pytest.mark.parametrize("radius_meters", (99, 50_001))
def test_search_request_rejects_out_of_range_radius(radius_meters: int) -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=radius_meters,
        )


@pytest.mark.parametrize("radius_meters", (math.nan, math.inf, -math.inf))
def test_search_request_rejects_non_finite_radius(radius_meters: float) -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=radius_meters,
        )


def test_search_request_creates_the_normalized_default_search_state() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={},
        sort="provider_default",
    )

    assert request.to_domain() == SearchCriteria(
        location=request.location.to_domain(),
        radius_meters=1_000,
        filters=SearchFilters(),
        sort=SearchSort.PROVIDER_DEFAULT,
    )


def test_search_request_normalizes_service_filters() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={"dine_in": True, "takeout": True},
        sort="provider_default",
    )

    filters = request.to_domain().filters
    assert filters.dine_in is True
    assert filters.takeout is True


def test_search_request_normalizes_open_now() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={"open_now": True},
    )

    assert request.to_domain().filters.open_now is True


def test_search_request_normalizes_minimum_rating_and_rating_sort() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={"minimum_rating": 4.5},
        sort="rating",
    )

    criteria = request.to_domain()
    assert criteria.filters.minimum_rating is MinimumRating.FOUR_AND_HALF
    assert criteria.sort is SearchSort.RATING


def test_search_request_normalizes_selected_place_types() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={"place_types": ["bar", "bakery"]},
        sort="provider_default",
    )

    assert request.to_domain().filters == SearchFilters(
        place_types=(PlaceType.BAR, PlaceType.BAKERY)
    )


def test_search_request_normalizes_cuisine_and_distance_sort() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={
            "place_types": ["restaurant"],
            "cuisines": ["italian", "persian"],
            "common_foods": [],
        },
        sort="distance",
    )

    criteria = request.to_domain()
    assert criteria.filters == SearchFilters(
        place_types=(PlaceType.RESTAURANT,),
        cuisines=(Cuisine.ITALIAN, Cuisine.PERSIAN),
    )
    assert criteria.sort is SearchSort.DISTANCE


def test_search_request_normalizes_cuisine_and_common_food_together() -> None:
    request = SearchPlacesRequest(
        location=SelectedLocationRequest(
            label="Toronto City Hall",
            latitude=43.6532,
            longitude=-79.3832,
        ),
        radius_meters=1_000,
        filters={
            "place_types": ["restaurant"],
            "cuisines": ["persian"],
            "common_foods": ["pizza", "ramen"],
        },
    )

    assert request.to_domain().filters.cuisines == (Cuisine.PERSIAN,)
    assert request.to_domain().filters.common_foods == (
        CommonFood.PIZZA,
        CommonFood.RAMEN,
    )


@pytest.mark.parametrize(
    "place_types",
    (
        [],
        ["restaurant", "restaurant"],
        ["food_truck"],
    ),
)
def test_search_request_rejects_invalid_place_types(
    place_types: list[str],
) -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=1_000,
            filters={"place_types": place_types},
            sort="provider_default",
        )


@pytest.mark.parametrize(
    "filters",
    (
        {"cuisines": ["canadian"]},
        {"common_foods": ["pasta"]},
        {"cuisines": ["italian", "italian"]},
        {"common_foods": ["pizza", "pizza"]},
    ),
)
def test_search_request_rejects_unsupported_or_duplicate_specialties(
    filters: dict[str, list[str]],
) -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=1_000,
            filters=filters,
        )


@pytest.mark.parametrize("minimum_rating", (2.5, 3.7, 5.0))
def test_search_request_rejects_an_unsupported_minimum_rating(
    minimum_rating: float,
) -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=1_000,
            filters={"minimum_rating": minimum_rating},
        )


def test_search_request_rejects_an_unsupported_sort() -> None:
    with pytest.raises(ValidationError):
        SearchPlacesRequest(
            location=SelectedLocationRequest(
                label="Toronto City Hall",
                latitude=43.6532,
                longitude=-79.3832,
            ),
            radius_meters=1_000,
            filters={},
            sort="price",
        )
