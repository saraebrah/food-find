import pytest

from app.domain.search import (
    DEFAULT_PLACE_TYPES,
    CommonFood,
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchFilters,
    SearchSort,
)


def test_search_filters_default_to_restaurant_and_cafe() -> None:
    filters = SearchFilters()

    assert filters.place_types == DEFAULT_PLACE_TYPES
    assert filters.open_now is False
    assert filters.minimum_rating is None
    assert filters.dine_in is False
    assert filters.takeout is False


def test_search_rating_contract_uses_supported_thresholds_and_order() -> None:
    assert [rating.value for rating in MinimumRating] == [3.0, 3.5, 4.0, 4.5]
    assert SearchSort.RATING.value == "rating"


@pytest.mark.parametrize(
    "place_types",
    (
        (),
        (PlaceType.RESTAURANT, PlaceType.RESTAURANT),
    ),
)
def test_search_filters_require_unique_non_empty_place_types(
    place_types: tuple[PlaceType, ...],
) -> None:
    with pytest.raises(ValueError):
        SearchFilters(place_types=place_types)


def test_search_filters_allow_cuisine_and_common_food_together() -> None:
    filters = SearchFilters(
        cuisines=(Cuisine.ITALIAN,),
        common_foods=(CommonFood.PIZZA,),
    )

    assert filters.cuisines == (Cuisine.ITALIAN,)
    assert filters.common_foods == (CommonFood.PIZZA,)
