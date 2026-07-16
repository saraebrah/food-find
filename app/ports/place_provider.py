from collections.abc import Sequence
from typing import Protocol

from app.domain.place import Place, PlaceDetails


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
        included_types: Sequence[str],
    ) -> Sequence[Place]: ...

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails: ...
