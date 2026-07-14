from dataclasses import dataclass

from app.domain.place import Coordinates


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationSuggestion:
    provider: str
    provider_place_id: str
    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectedLocation:
    label: str
    coordinates: Coordinates
    provider: str | None = None
    provider_place_id: str | None = None
