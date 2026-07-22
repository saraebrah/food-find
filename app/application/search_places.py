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
        normalized_places: list[Place] = []
        for place in places:
            distance_meters = straight_line_distance_meters(
                criteria.location.coordinates,
                place.coordinates,
            )
            if distance_meters > criteria.radius_meters:
                continue
            if place.business_status in EXCLUDED_BUSINESS_STATUSES:
                continue
            if criteria.filters.open_now and place.open_now is not True:
                continue
            if criteria.filters.dine_in and place.dine_in is not True:
                continue
            if criteria.filters.takeout and place.takeout is not True:
                continue
            if (
                criteria.filters.minimum_rating is not None
                and (
                    place.rating is None
                    or place.rating < criteria.filters.minimum_rating.value
                )
            ):
                continue
            normalized_places.append(
                replace(place, distance_meters=distance_meters)
            )
        if criteria.sort is SearchSort.RATING:
            return sorted(
                normalized_places,
                key=lambda place: (
                    place.rating is None,
                    -(place.rating or 0),
                ),
            )
        return normalized_places
