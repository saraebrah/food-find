from app.application.match_reasons import build_match_reasons
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates, Place
from app.domain.search import (
    CommonFood,
    Cuisine,
    SearchCriteria,
    SearchFilters,
)
from app.domain.search_intent import (
    DescriptiveRequirement,
    DescriptiveRequirementKind,
)


def criteria_with(*, filters: SearchFilters) -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="Toronto",
            coordinates=Coordinates(latitude=43.65, longitude=-79.38),
        ),
        radius_meters=1_000,
        filters=filters,
    )


def place() -> Place:
    return Place(
        provider="google",
        provider_place_id="place-1",
        name="Example",
        category="Restaurant",
        category_code="restaurant",
        address=None,
        coordinates=Coordinates(latitude=43.65, longitude=-79.38),
    )


def test_structured_food_collapses_a_duplicate_dish_requirement() -> None:
    reasons = build_match_reasons(
        place=place(),
        criteria=criteria_with(
            filters=SearchFilters(common_foods=(CommonFood.KEBAB,))
        ),
        descriptive_requirements=(
            DescriptiveRequirement(
                text="serves kebabs",
                kind=DescriptiveRequirementKind.DISH,
            ),
        ),
        availability_window=None,
    )

    texts = [reason.text for reason in reasons]
    assert texts.count(
        "Kebab availability is not verified—check the menu or call."
    ) == 1
    assert all("serves kebabs" not in text for text in texts)


def test_relevance_reasons_do_not_claim_cuisine_or_dietary_facts() -> None:
    reasons = build_match_reasons(
        place=place(),
        criteria=criteria_with(
            filters=SearchFilters(
                cuisines=(Cuisine.PERSIAN, Cuisine.ITALIAN),
            )
        ),
        descriptive_requirements=(
            DescriptiveRequirement(
                text="halal options",
                kind=DescriptiveRequirementKind.DIETARY,
            ),
        ),
        availability_window=None,
    )

    relevance_texts = [
        reason.text for reason in reasons if reason.kind == "relevance"
    ]
    assert relevance_texts == [
        (
            "Persian or Italian influenced Google text relevance; "
            "the cuisine is not independently verified."
        ),
        (
            "“halal options” influenced Google text relevance; "
            "confirm dietary requirements with the business."
        ),
    ]
