from dataclasses import dataclass, field
from enum import Enum
from math import asin, cos, radians, sin, sqrt

from app.domain.location import SelectedLocation
from app.domain.place import Coordinates


EARTH_RADIUS_METERS = 6_371_000


class Cuisine(str, Enum):
    CHINESE = "chinese"
    ITALIAN = "italian"
    PERSIAN = "persian"
    THAI = "thai"
    INDIAN = "indian"
    MEXICAN = "mexican"
    JAPANESE = "japanese"
    KOREAN = "korean"
    VIETNAMESE = "vietnamese"
    MEDITERRANEAN = "mediterranean"


class CommonFood(str, Enum):
    PIZZA = "pizza"
    BURGER = "burger"
    STEAK = "steak"
    RAMEN = "ramen"
    KEBAB = "kebab"
    SHAWARMA = "shawarma"
    ICE_CREAM = "ice_cream"
    DESSERT = "dessert"
    SWEETS = "sweets"
    DRINKS = "drinks"
    SUSHI = "sushi"
    TACO = "taco"
    SALAD = "salad"
    SOUP = "soup"
    PASTA = "pasta"


class MinimumRating(float, Enum):
    THREE = 3.0
    THREE_AND_HALF = 3.5
    FOUR = 4.0
    FOUR_AND_HALF = 4.5


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Normalized filters supported by the current search implementation."""

    cuisines: tuple[Cuisine, ...] = ()
    common_foods: tuple[CommonFood, ...] = ()
    open_now: bool = False
    minimum_rating: MinimumRating | None = None
    dine_in: bool = False
    takeout: bool = False

    def __post_init__(self) -> None:
        if len(set(self.cuisines)) != len(self.cuisines):
            raise ValueError("Cuisines must be unique")
        if len(set(self.common_foods)) != len(self.common_foods):
            raise ValueError("Common foods must be unique")


class SearchSort(str, Enum):
    PROVIDER_DEFAULT = "provider_default"
    DISTANCE = "distance"
    RATING = "rating"


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchCriteria:
    location: SelectedLocation
    radius_meters: float
    filters: SearchFilters = field(default_factory=SearchFilters)
    sort: SearchSort = SearchSort.PROVIDER_DEFAULT


def straight_line_distance_meters(
    origin: Coordinates,
    destination: Coordinates,
) -> int:
    latitude_delta = radians(destination.latitude - origin.latitude)
    longitude_delta = radians(destination.longitude - origin.longitude)
    origin_latitude = radians(origin.latitude)
    destination_latitude = radians(destination.latitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(origin_latitude)
        * cos(destination_latitude)
        * sin(longitude_delta / 2) ** 2
    )
    arc = 2 * asin(sqrt(min(1, haversine)))
    return round(EARTH_RADIUS_METERS * arc)
