from dataclasses import dataclass
from typing import Literal


BusinessStatus = Literal[
    "operational",
    "temporarily_closed",
    "permanently_closed",
]


@dataclass(frozen=True, slots=True, kw_only=True)
class Coordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True, kw_only=True)
class Place:
    provider: str
    provider_place_id: str
    name: str
    category: str | None
    category_code: str | None
    address: str | None
    coordinates: Coordinates
    business_status: BusinessStatus | None = None
    distance_meters: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PlaceDetails:
    provider: str
    provider_place_id: str
    rating: float | None
    user_rating_count: int | None
    open_now: bool | None
    opening_hours: tuple[str, ...]
    phone_number: str | None
    website_uri: str | None
