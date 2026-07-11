from dataclasses import dataclass


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
