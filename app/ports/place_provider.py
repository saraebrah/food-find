from collections.abc import Sequence
from typing import Protocol

from app.domain.place import Place


class PlaceProvider(Protocol):
    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> Sequence[Place]: ...
