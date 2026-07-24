from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.domain.location import SelectedLocation
from app.domain.place import Coordinates
from app.domain.search import (
    CommonFood,
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
    ResolvedAssumption,
    SearchIntent,
    UnsupportedCriterion,
)


TORONTO = ZoneInfo("America/Toronto")


def make_search_criteria() -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="318 King St E, Toronto",
            coordinates=Coordinates(latitude=43.6519, longitude=-79.3642),
        ),
        radius_meters=2_000,
        filters=SearchFilters(
            place_types=(PlaceType.RESTAURANT,),
            cuisines=(Cuisine.PERSIAN,),
            common_foods=(CommonFood.KEBAB,),
            minimum_rating=MinimumRating.FOUR,
        ),
        sort=SearchSort.PROVIDER_DEFAULT,
    )


def test_search_intent_keeps_executable_and_intent_only_criteria() -> None:
    criteria = make_search_criteria()
    window = AvailabilityWindow(
        starts_at=datetime(2026, 7, 22, 18, tzinfo=TORONTO),
        ends_at=datetime(2026, 7, 23, 0, tzinfo=TORONTO),
    )
    requirement = DescriptiveRequirement(
        text="serves kebab",
        kind=DescriptiveRequirementKind.DISH,
    )
    assumption = ResolvedAssumption(
        source_text="good rated",
        interpretation="Minimum rating of 4.0",
    )
    unsupported = UnsupportedCriterion(
        text="not crowded",
        reason="Current crowd levels are not available",
    )

    intent = SearchIntent(
        search_criteria=criteria,
        availability_window=window,
        descriptive_requirements=(requirement,),
        assumptions=(assumption,),
        unsupported_criteria=(unsupported,),
    )

    assert intent.search_criteria is criteria
    assert intent.availability_window is window
    assert intent.descriptive_requirements == (requirement,)
    assert intent.assumptions == (assumption,)
    assert intent.unsupported_criteria == (unsupported,)


def test_search_intent_can_represent_manual_criteria_without_interpretation() -> None:
    intent = SearchIntent(search_criteria=make_search_criteria())

    assert intent.availability_window is None
    assert intent.descriptive_requirements == ()
    assert intent.assumptions == ()
    assert intent.unsupported_criteria == ()


@pytest.mark.parametrize(
    ("model", "arguments"),
    (
        (
            DescriptiveRequirement,
            {"text": "   ", "kind": DescriptiveRequirementKind.OTHER},
        ),
        (
            ResolvedAssumption,
            {"source_text": "", "interpretation": "Selected location"},
        ),
        (
            ResolvedAssumption,
            {"source_text": "near me", "interpretation": "  "},
        ),
        (
            UnsupportedCriterion,
            {"text": "not crowded", "reason": ""},
        ),
    ),
)
def test_search_intent_text_values_must_not_be_blank(
    model: type[object],
    arguments: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        model(**arguments)


@pytest.mark.parametrize(
    ("starts_at", "ends_at"),
    (
        (
            datetime(2026, 7, 22, 18),
            datetime(2026, 7, 23, 0),
        ),
        (
            datetime(2026, 7, 22, 19, tzinfo=TORONTO),
            datetime(2026, 7, 22, 18, tzinfo=TORONTO),
        ),
    ),
)
def test_availability_window_requires_aware_non_decreasing_datetimes(
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    with pytest.raises(ValueError):
        AvailabilityWindow(starts_at=starts_at, ends_at=ends_at)


def test_availability_window_allows_an_exact_time() -> None:
    exact_time = datetime(2026, 7, 22, 19, tzinfo=TORONTO)

    window = AvailabilityWindow(
        starts_at=exact_time,
        ends_at=exact_time,
    )

    assert window.starts_at == window.ends_at == exact_time
