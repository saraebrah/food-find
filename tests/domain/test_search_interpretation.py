from datetime import datetime, timezone

import pytest

from app.domain.search import CommonFood, Cuisine, MinimumRating, PlaceType, SearchSort
from app.domain.search_interpretation import (
    FOODFIND_SEARCH_CAPABILITIES,
    SearchInterpretationContext,
)
from app.domain.search_intent import DescriptiveRequirementKind


def test_context_exposes_local_date_time_and_supported_capabilities() -> None:
    context = SearchInterpretationContext(
        current_datetime=datetime(
            2026,
            7,
            23,
            15,
            30,
            tzinfo=timezone.utc,
        ),
        timezone_name="America/Toronto",
    )

    assert context.local_datetime.isoformat() == "2026-07-23T11:30:00-04:00"
    assert context.current_date.isoformat() == "2026-07-23"
    assert context.capabilities is FOODFIND_SEARCH_CAPABILITIES
    assert context.capabilities.place_types == tuple(PlaceType)
    assert context.capabilities.cuisines == tuple(Cuisine)
    assert context.capabilities.common_foods == tuple(CommonFood)
    assert context.capabilities.minimum_ratings == tuple(MinimumRating)
    assert context.capabilities.sort_options == tuple(SearchSort)
    assert context.capabilities.descriptive_requirement_kinds == tuple(
        DescriptiveRequirementKind
    )
    assert context.capabilities.open_now is True
    assert context.capabilities.dine_in is True
    assert context.capabilities.takeout is True
    assert context.capabilities.time_aware_availability is True
    assert context.capabilities.availability_horizon_days == 7
    assert context.capabilities.device_location is False


def test_context_rejects_timezone_free_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SearchInterpretationContext(
            current_datetime=datetime(2026, 7, 23, 11, 30),
            timezone_name="America/Toronto",
        )


def test_context_rejects_unknown_timezone() -> None:
    with pytest.raises(ValueError, match="Unknown timezone"):
        SearchInterpretationContext(
            current_datetime=datetime(
                2026,
                7,
                23,
                15,
                30,
                tzinfo=timezone.utc,
            ),
            timezone_name="Toronto/Unknown",
        )
