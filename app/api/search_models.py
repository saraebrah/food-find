from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.location import SelectedLocation
from app.domain.place import Coordinates
from app.domain.search import (
    DEFAULT_PLACE_TYPES,
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
)


class SelectedLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    label: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    provider: str | None = Field(default=None, max_length=50)
    provider_place_id: str | None = Field(default=None, max_length=500)

    def to_domain(self) -> SelectedLocation:
        return SelectedLocation(
            label=self.label,
            coordinates=Coordinates(
                latitude=self.latitude,
                longitude=self.longitude,
            ),
            provider=self.provider,
            provider_place_id=self.provider_place_id,
        )


class SearchFiltersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place_types: tuple[PlaceType, ...] = Field(
        default=DEFAULT_PLACE_TYPES,
        min_length=1,
        max_length=len(PlaceType),
    )
    cuisines: tuple[Cuisine, ...] = Field(default=(), max_length=len(Cuisine))
    common_foods: tuple[CommonFood, ...] = Field(
        default=(),
        max_length=len(CommonFood),
    )
    open_now: bool = False
    minimum_rating: MinimumRating | None = None
    dine_in: bool = False
    takeout: bool = False

    @field_validator("place_types")
    @classmethod
    def place_types_must_be_unique(
        cls,
        place_types: tuple[PlaceType, ...],
    ) -> tuple[PlaceType, ...]:
        if len(set(place_types)) != len(place_types):
            raise ValueError("Place types must be unique")
        return place_types

    @field_validator("cuisines")
    @classmethod
    def cuisines_must_be_unique(
        cls,
        cuisines: tuple[Cuisine, ...],
    ) -> tuple[Cuisine, ...]:
        if len(set(cuisines)) != len(cuisines):
            raise ValueError("Cuisines must be unique")
        return cuisines

    @field_validator("common_foods")
    @classmethod
    def common_foods_must_be_unique(
        cls,
        common_foods: tuple[CommonFood, ...],
    ) -> tuple[CommonFood, ...]:
        if len(set(common_foods)) != len(common_foods):
            raise ValueError("Common foods must be unique")
        return common_foods

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


class DescriptiveRequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=200)
    kind: DescriptiveRequirementKind

    def to_domain(self) -> DescriptiveRequirement:
        return DescriptiveRequirement(text=self.text, kind=self.kind)


class AvailabilityWindowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def end_must_not_precede_start(self) -> "AvailabilityWindowRequest":
        if self.ends_at < self.starts_at:
            raise ValueError("Availability window must not end before it starts")
        return self

    def to_domain(self) -> AvailabilityWindow:
        return AvailabilityWindow(
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        )


class SearchCriteriaRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    location: SelectedLocationRequest
    radius_meters: float = Field(ge=100, le=50_000)
    filters: SearchFiltersRequest = Field(default_factory=SearchFiltersRequest)
    sort: SearchSort = SearchSort.PROVIDER_DEFAULT

    def to_domain(self) -> SearchCriteria:
        return SearchCriteria(
            location=self.location.to_domain(),
            radius_meters=self.radius_meters,
            filters=self.filters.to_domain(),
            sort=self.sort,
        )


class SearchPlacesRequest(SearchCriteriaRequest):
    descriptive_requirements: tuple[DescriptiveRequirementRequest, ...] = Field(
        default=(),
        max_length=20,
    )
    availability_window: AvailabilityWindowRequest | None = None

    def descriptive_requirements_to_domain(
        self,
    ) -> tuple[DescriptiveRequirement, ...]:
        return tuple(
            requirement.to_domain()
            for requirement in self.descriptive_requirements
        )

    def availability_window_to_domain(self) -> AvailabilityWindow | None:
        return (
            self.availability_window.to_domain()
            if self.availability_window is not None
            else None
        )
