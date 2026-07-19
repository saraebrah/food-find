from collections.abc import Sequence
from dataclasses import replace

from app.domain.place import Place
from app.domain.search import (
    DEFAULT_PLACE_TYPES,
    SearchCriteria,
    SearchSort,
    straight_line_distance_meters,
)
from app.ports.place_provider import PlaceProvider


DEFAULT_SEARCH_TYPES = DEFAULT_PLACE_TYPES
EXCLUDED_BUSINESS_STATUSES = frozenset(
    ("temporarily_closed", "permanently_closed")
)


class SearchPlaces:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._place_provider = place_provider

    async def execute(self, *, criteria: SearchCriteria) -> Sequence[Place]:
        places = await self._place_provider.search_nearby(
            latitude=criteria.location.coordinates.latitude,
            longitude=criteria.location.coordinates.longitude,
            radius_meters=criteria.radius_meters,
            filters=criteria.filters,
            sort=criteria.sort,
        )
        normalized_places = [
            replace(
                place,
                distance_meters=straight_line_distance_meters(
                    criteria.location.coordinates,
                    place.coordinates,
                ),
            )
            for place in places
            if place.business_status not in EXCLUDED_BUSINESS_STATUSES
            and (not criteria.filters.open_now or place.open_now is True)
            and (not criteria.filters.dine_in or place.dine_in is True)
            and (not criteria.filters.takeout or place.takeout is True)
            and (
                criteria.filters.minimum_rating is None
                or place.rating is not None
                and place.rating >= criteria.filters.minimum_rating.value
            )
        ]
        if criteria.sort is SearchSort.RATING:
            return sorted(
                normalized_places,
                key=lambda place: (
                    place.rating is None,
                    -(place.rating or 0),
                ),
            )
        return normalized_places
