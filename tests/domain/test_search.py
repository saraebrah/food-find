from app.domain.search import (
    CommonFood,
    Cuisine,
    MinimumRating,
    SearchFilters,
    SearchSort,
)


def test_search_filters_have_no_place_type_dimension() -> None:
    filters = SearchFilters()

    assert not hasattr(filters, "place_types")
    assert filters.open_now is False
    assert filters.minimum_rating is None
    assert filters.dine_in is False
    assert filters.takeout is False


def test_search_rating_contract_uses_supported_thresholds_and_order() -> None:
    assert [rating.value for rating in MinimumRating] == [3.0, 3.5, 4.0, 4.5]
    assert SearchSort.RATING.value == "rating"


def test_cuisine_contract_includes_the_expanded_supported_options() -> None:
    assert [cuisine.value for cuisine in Cuisine] == [
        "chinese",
        "italian",
        "persian",
        "thai",
        "indian",
        "mexican",
        "japanese",
        "korean",
        "vietnamese",
        "mediterranean",
    ]


def test_common_food_contract_includes_the_expanded_options() -> None:
    assert [food.value for food in CommonFood] == [
        "pizza",
        "burger",
        "steak",
        "ramen",
        "kebab",
        "shawarma",
        "ice_cream",
        "dessert",
        "sweets",
        "drinks",
        "sushi",
        "taco",
        "salad",
        "soup",
        "pasta",
    ]


def test_search_filters_allow_cuisine_and_common_food_together() -> None:
    filters = SearchFilters(
        cuisines=(Cuisine.ITALIAN,),
        common_foods=(CommonFood.PIZZA,),
    )

    assert filters.cuisines == (Cuisine.ITALIAN,)
    assert filters.common_foods == (CommonFood.PIZZA,)
