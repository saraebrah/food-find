from typing import Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

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


class SearchFiltersOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place_types: tuple[PlaceType, ...] = Field(
        min_length=1,
        max_length=len(PlaceType),
    )
    cuisines: tuple[Cuisine, ...] = Field(max_length=len(Cuisine))
    common_foods: tuple[CommonFood, ...] = Field(max_length=len(CommonFood))
    open_now: bool
    minimum_rating: MinimumRating | None
    dine_in: bool
    takeout: bool

    @field_validator("place_types", "cuisines", "common_foods")
    @classmethod
    def values_must_be_unique(
        cls,
        values: tuple[Any, ...],
    ) -> tuple[Any, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Filter values must be unique")
        return values

    def to_domain(self) -> SearchFilters:
        return SearchFilters(
            place_types=self.place_types,
            cuisines=self.cuisines,
            common_foods=self.common_foods,
            open_now=self.open_now,
            minimum_rating=self.minimum_rating,
            dine_in=self.dine_in,
            takeout=self.takeout,
        )


class DescriptiveRequirementOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=200)
    kind: DescriptiveRequirementKind

    def to_domain(self) -> DescriptiveRequirement:
        return DescriptiveRequirement(text=self.text, kind=self.kind)


class ResolvedAssumptionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_text: str = Field(min_length=1, max_length=200)
    interpretation: str = Field(min_length=1, max_length=300)

    def to_domain(self) -> ResolvedAssumption:
        return ResolvedAssumption(
            source_text=self.source_text,
            interpretation=self.interpretation,
        )


class UnsupportedCriterionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=300)

    def to_domain(self) -> UnsupportedCriterion:
        return UnsupportedCriterion(text=self.text, reason=self.reason)


class AvailabilityWindowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "AvailabilityWindowOutput":
        if self.ends_at < self.starts_at:
            raise ValueError("Availability window must not end before it starts")
        return self

    def to_domain(self) -> AvailabilityWindow:
        return AvailabilityWindow(
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        )


class SearchIntentOutput(BaseModel):
    """Validated, provider-neutral structured output from an LLM adapter."""

    model_config = ConfigDict(extra="forbid")

    radius_meters: float = Field(ge=100, le=50_000, allow_inf_nan=False)
    filters: SearchFiltersOutput
    sort: SearchSort
    descriptive_requirements: tuple[DescriptiveRequirementOutput, ...] = Field(
        max_length=20
    )
    availability_window: AvailabilityWindowOutput | None
    assumptions: tuple[ResolvedAssumptionOutput, ...] = Field(max_length=20)
    unsupported_criteria: tuple[UnsupportedCriterionOutput, ...] = Field(
        max_length=20
    )

    def to_domain(self, *, base_criteria: SearchCriteria) -> SearchIntent:
        return SearchIntent(
            search_criteria=SearchCriteria(
                location=base_criteria.location,
                radius_meters=self.radius_meters,
                filters=self.filters.to_domain(),
                sort=self.sort,
            ),
            descriptive_requirements=tuple(
                requirement.to_domain()
                for requirement in self.descriptive_requirements
            ),
            availability_window=(
                self.availability_window.to_domain()
                if self.availability_window is not None
                else None
            ),
            assumptions=tuple(
                assumption.to_domain() for assumption in self.assumptions
            ),
            unsupported_criteria=tuple(
                criterion.to_domain()
                for criterion in self.unsupported_criteria
            ),
        )
