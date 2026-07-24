from dataclasses import dataclass
from datetime import datetime
from enum import Enum
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
class OpeningPeriod:
    """A provider-confirmed period when a place is open."""

    starts_at: datetime
    ends_at: datetime | None

    def __post_init__(self) -> None:
        if self.starts_at.utcoffset() is None:
            raise ValueError("Opening period start must be timezone-aware")
        if self.ends_at is not None:
            if self.ends_at.utcoffset() is None:
                raise ValueError("Opening period end must be timezone-aware")
            if self.ends_at <= self.starts_at:
                raise ValueError("Opening period end must be after its start")


class MatchReasonKind(str, Enum):
    CONFIRMED = "confirmed"
    RELEVANCE = "relevance"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchReason:
    """An honest, deterministic explanation for including a place."""

    kind: MatchReasonKind
    text: str

    def __post_init__(self) -> None:
        normalized = self.text.strip()
        if not normalized:
            raise ValueError("Match reason text must not be blank")
        object.__setattr__(self, "text", normalized)


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
    open_now: bool | None = None
    rating: float | None = None
    dine_in: bool | None = None
    takeout: bool | None = None
    distance_meters: int | None = None
    opening_periods: tuple[OpeningPeriod, ...] | None = None
    match_reasons: tuple[MatchReason, ...] = ()


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
