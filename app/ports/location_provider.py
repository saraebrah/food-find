from collections.abc import Sequence
from typing import Protocol

from app.domain.location import LocationSuggestion, SelectedLocation


class LocationProvider(Protocol):
    async def suggest(
        self,
        *,
        query: str,
        session_token: str,
    ) -> Sequence[LocationSuggestion]: ...

    async def resolve(
        self,
        *,
        suggestion: LocationSuggestion,
        session_token: str,
    ) -> SelectedLocation: ...
