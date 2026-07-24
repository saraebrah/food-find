from collections.abc import Sequence
from typing import Protocol

from app.domain.place import Place, PlaceDetails
from app.domain.search import SearchFilters, SearchSort
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
)


class PlaceProviderError(RuntimeError):
    """A place provider could not complete a requested operation."""


class PlaceProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
    ) -> Sequence[Place]: ...

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails: ...
