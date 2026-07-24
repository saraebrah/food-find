from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.application.search_intent_output import SearchIntentOutput
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
from app.domain.search_intent import DescriptiveRequirementKind


TORONTO = ZoneInfo("America/Toronto")


def make_base_criteria() -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="318 King St E, Toronto",
            coordinates=Coordinates(latitude=43.6519, longitude=-79.3642),
        ),
        radius_meters=1_000,
    )


def test_validated_output_converts_to_provider_independent_intent() -> None:
    output = SearchIntentOutput.model_validate(
        {
            "radius_meters": 3_000,
            "filters": {
                "place_types": ["restaurant"],
                "cuisines": ["persian"],
                "common_foods": ["kebab"],
                "open_now": False,
                "minimum_rating": 4.5,
                "dine_in": True,
                "takeout": False,
            },
            "sort": "distance",
            "descriptive_requirements": [
                {"text": "quiet atmosphere", "kind": "atmosphere"},
            ],
            "availability_window": {
                "starts_at": "2026-07-23T18:00:00-04:00",
                "ends_at": "2026-07-24T00:00:00-04:00",
            },
            "assumptions": [
                {
                    "source_text": "highly rated",
                    "interpretation": "Minimum rating of 4.5",
                }
            ],
            "unsupported_criteria": [
                {
                    "text": "not crowded",
                    "reason": "Current crowd levels are unavailable",
                }
            ],
        }
    )

    intent = output.to_domain(base_criteria=make_base_criteria())

    assert intent.search_criteria.location == make_base_criteria().location
    assert intent.search_criteria.radius_meters == 3_000
    assert intent.search_criteria.filters == SearchFilters(
        place_types=(PlaceType.RESTAURANT,),
        cuisines=(Cuisine.PERSIAN,),
        common_foods=(CommonFood.KEBAB,),
        minimum_rating=MinimumRating.FOUR_AND_HALF,
        dine_in=True,
    )
    assert intent.search_criteria.sort is SearchSort.DISTANCE
    assert intent.descriptive_requirements[0].text == "quiet atmosphere"
    assert (
        intent.descriptive_requirements[0].kind
        is DescriptiveRequirementKind.ATMOSPHERE
    )
    assert intent.availability_window is not None
    assert intent.availability_window.starts_at == datetime(
        2026,
        7,
        23,
        18,
        tzinfo=TORONTO,
    )
    assert intent.assumptions[0].source_text == "highly rated"
    assert intent.unsupported_criteria[0].text == "not crowded"


@pytest.mark.parametrize(
    "payload_update",
    (
        {"radius_meters": 50},
        {"filters": {"place_types": []}},
        {"filters": {"place_types": ["food_truck"]}},
        {"sort": "price"},
        {"unexpected": "value"},
    ),
)
def test_output_rejects_values_outside_foodfind_contract(
    payload_update: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "radius_meters": 1_000,
        "filters": {
            "place_types": ["restaurant"],
            "cuisines": [],
            "common_foods": [],
            "open_now": False,
            "minimum_rating": None,
            "dine_in": False,
            "takeout": False,
        },
        "sort": "provider_default",
        "descriptive_requirements": [],
        "availability_window": None,
        "assumptions": [],
        "unsupported_criteria": [],
    }
    payload.update(payload_update)

    with pytest.raises(ValidationError):
        SearchIntentOutput.model_validate(payload)


def test_output_rejects_timezone_free_availability_window() -> None:
    with pytest.raises(ValidationError):
        SearchIntentOutput.model_validate(
            {
                "radius_meters": 1_000,
                "filters": {
                    "place_types": ["restaurant"],
                    "cuisines": [],
                    "common_foods": [],
                    "open_now": False,
                    "minimum_rating": None,
                    "dine_in": False,
                    "takeout": False,
                },
                "sort": "provider_default",
                "descriptive_requirements": [],
                "availability_window": {
                    "starts_at": "2026-07-23T18:00:00",
                    "ends_at": "2026-07-24T00:00:00",
                },
                "assumptions": [],
                "unsupported_criteria": [],
            }
        )


def test_output_accepts_equal_times_for_an_exact_time_request() -> None:
    output = SearchIntentOutput.model_validate(
        {
            "radius_meters": 1_000,
            "filters": {
                "place_types": ["restaurant"],
                "cuisines": [],
                "common_foods": [],
                "open_now": False,
                "minimum_rating": None,
                "dine_in": False,
                "takeout": False,
            },
            "sort": "provider_default",
            "descriptive_requirements": [],
            "availability_window": {
                "starts_at": "2026-07-23T19:00:00-04:00",
                "ends_at": "2026-07-23T19:00:00-04:00",
            },
            "assumptions": [],
            "unsupported_criteria": [],
        }
    )

    assert output.availability_window is not None
    assert (
        output.availability_window.starts_at
        == output.availability_window.ends_at
    )
