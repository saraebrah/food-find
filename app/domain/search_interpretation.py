from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.search import CommonFood, Cuisine, MinimumRating, PlaceType, SearchSort
from app.domain.search_intent import DescriptiveRequirementKind


@dataclass(frozen=True, slots=True)
class SearchCapabilities:
    """FoodFind-owned behavior the interpreter may express."""

    place_types: tuple[PlaceType, ...]
    cuisines: tuple[Cuisine, ...]
    common_foods: tuple[CommonFood, ...]
    minimum_ratings: tuple[MinimumRating, ...]
    sort_options: tuple[SearchSort, ...]
    descriptive_requirement_kinds: tuple[DescriptiveRequirementKind, ...]
    minimum_radius_meters: int
    maximum_radius_meters: int
    open_now: bool
    dine_in: bool
    takeout: bool
    selected_location_reference: bool
    explicit_location_resolution: bool
    time_aware_availability: bool
    availability_horizon_days: int
    device_location: bool


FOODFIND_SEARCH_CAPABILITIES = SearchCapabilities(
    place_types=tuple(PlaceType),
    cuisines=tuple(Cuisine),
    common_foods=tuple(CommonFood),
    minimum_ratings=tuple(MinimumRating),
    sort_options=tuple(SearchSort),
    descriptive_requirement_kinds=tuple(DescriptiveRequirementKind),
    minimum_radius_meters=100,
    maximum_radius_meters=50_000,
    open_now=True,
    dine_in=True,
    takeout=True,
    selected_location_reference=True,
    explicit_location_resolution=False,
    time_aware_availability=True,
    availability_horizon_days=7,
    device_location=False,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchInterpretationContext:
    """One immutable time and capability snapshot for an interpretation."""

    current_datetime: datetime
    timezone_name: str
    capabilities: SearchCapabilities = FOODFIND_SEARCH_CAPABILITIES

    def __post_init__(self) -> None:
        if self.current_datetime.utcoffset() is None:
            raise ValueError("Current datetime must be timezone-aware")

        timezone_name = self.timezone_name.strip()
        try:
            ZoneInfo(timezone_name)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ValueError(f"Unknown timezone: {timezone_name}") from error
        object.__setattr__(self, "timezone_name", timezone_name)

    @property
    def local_datetime(self) -> datetime:
        return self.current_datetime.astimezone(ZoneInfo(self.timezone_name))

    @property
    def current_date(self) -> date:
        return self.local_datetime.date()
