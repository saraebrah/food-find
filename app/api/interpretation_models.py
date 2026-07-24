from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.location_models import SelectedLocationResponse
from app.api.search_models import SearchCriteriaRequest
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
    DescriptiveRequirementKind,
    SearchIntent,
)


class InterpretSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=1_000)
    search_criteria: SearchCriteriaRequest
    timezone: str = Field(min_length=1, max_length=100)

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_known(cls, timezone: str) -> str:
        try:
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error
        return timezone


class SearchFiltersResponse(BaseModel):
    place_types: list[PlaceType]
    cuisines: list[Cuisine]
    common_foods: list[CommonFood]
    open_now: bool
    minimum_rating: MinimumRating | None
    dine_in: bool
    takeout: bool

    @classmethod
    def from_domain(cls, filters: SearchFilters) -> "SearchFiltersResponse":
        return cls(
            place_types=list(filters.place_types),
            cuisines=list(filters.cuisines),
            common_foods=list(filters.common_foods),
            open_now=filters.open_now,
            minimum_rating=filters.minimum_rating,
            dine_in=filters.dine_in,
            takeout=filters.takeout,
        )


class SearchCriteriaResponse(BaseModel):
    location: SelectedLocationResponse
    radius_meters: float
    filters: SearchFiltersResponse
    sort: SearchSort

    @classmethod
    def from_domain(cls, criteria: SearchCriteria) -> "SearchCriteriaResponse":
        return cls(
            location=SelectedLocationResponse.from_domain(criteria.location),
            radius_meters=criteria.radius_meters,
            filters=SearchFiltersResponse.from_domain(criteria.filters),
            sort=criteria.sort,
        )


class DescriptiveRequirementResponse(BaseModel):
    text: str
    kind: DescriptiveRequirementKind


class AvailabilityWindowResponse(BaseModel):
    starts_at: datetime
    ends_at: datetime


class ResolvedAssumptionResponse(BaseModel):
    source_text: str
    interpretation: str


class UnsupportedCriterionResponse(BaseModel):
    text: str
    reason: str


class SearchIntentResponse(BaseModel):
    search_criteria: SearchCriteriaResponse
    descriptive_requirements: list[DescriptiveRequirementResponse]
    availability_window: AvailabilityWindowResponse | None
    assumptions: list[ResolvedAssumptionResponse]
    unsupported_criteria: list[UnsupportedCriterionResponse]
    timezone: str

    @classmethod
    def from_domain(
        cls,
        *,
        intent: SearchIntent,
        timezone: str,
    ) -> "SearchIntentResponse":
        return cls(
            search_criteria=SearchCriteriaResponse.from_domain(
                intent.search_criteria
            ),
            descriptive_requirements=[
                DescriptiveRequirementResponse(
                    text=requirement.text,
                    kind=requirement.kind,
                )
                for requirement in intent.descriptive_requirements
            ],
            availability_window=(
                AvailabilityWindowResponse(
                    starts_at=intent.availability_window.starts_at,
                    ends_at=intent.availability_window.ends_at,
                )
                if intent.availability_window is not None
                else None
            ),
            assumptions=[
                ResolvedAssumptionResponse(
                    source_text=assumption.source_text,
                    interpretation=assumption.interpretation,
                )
                for assumption in intent.assumptions
            ],
            unsupported_criteria=[
                UnsupportedCriterionResponse(
                    text=criterion.text,
                    reason=criterion.reason,
                )
                for criterion in intent.unsupported_criteria
            ],
            timezone=timezone,
        )
