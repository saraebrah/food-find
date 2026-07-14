import math

import pytest
from pydantic import ValidationError

from app.api.search_models import SearchPlacesRequest, SelectedLocationRequest


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
