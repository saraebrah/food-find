from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from app.application.match_reasons import build_match_reasons
from app.domain.place import Place
from app.domain.search import (
    DEFAULT_PLACE_TYPES,
    SearchCriteria,
    SearchSort,
    straight_line_distance_meters,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
)
from app.ports.place_provider import PlaceProvider


DEFAULT_SEARCH_TYPES = DEFAULT_PLACE_TYPES
EXCLUDED_BUSINESS_STATUSES = frozenset(
    ("temporarily_closed", "permanently_closed")
)
AVAILABILITY_HORIZON_DAYS = 7


class UnsupportedAvailabilityWindowError(ValueError):
    """The provider cannot confirm the requested availability window."""


class SearchPlaces:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._place_provider = place_provider

    async def execute(
        self,
        *,
        criteria: SearchCriteria,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
        current_datetime: datetime | None = None,
    ) -> Sequence[Place]:
        if availability_window is not None:
            _validate_availability_window(
                requested_window=availability_window,
                current_datetime=current_datetime,
            )
        places = await self._place_provider.search_nearby(
            latitude=criteria.location.coordinates.latitude,
            longitude=criteria.location.coordinates.longitude,
            radius_meters=criteria.radius_meters,
            filters=criteria.filters,
            sort=criteria.sort,
            descriptive_requirements=descriptive_requirements,
            availability_window=availability_window,
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
            if (
                availability_window is not None
                and not _is_available_during(
                    place=place,
                    requested_window=availability_window,
                )
            ):
                continue
            normalized_places.append(
                replace(
                    place,
                    distance_meters=distance_meters,
                    match_reasons=build_match_reasons(
                        place=place,
                        criteria=criteria,
                        descriptive_requirements=descriptive_requirements,
                        availability_window=availability_window,
                    ),
                )
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


def _is_available_during(
    *,
    place: Place,
    requested_window: AvailabilityWindow,
) -> bool:
    """Return true only when provider hours confirm the requested time."""

    if not place.opening_periods:
        return False

    exact_time = requested_window.starts_at == requested_window.ends_at
    for period in place.opening_periods:
        if exact_time:
            if (
                period.starts_at <= requested_window.starts_at
                and (
                    period.ends_at is None
                    or requested_window.starts_at < period.ends_at
                )
            ):
                return True
            continue

        if (
            period.starts_at < requested_window.ends_at
            and (
                period.ends_at is None
                or requested_window.starts_at < period.ends_at
            )
        ):
            return True
    return False


def _validate_availability_window(
    *,
    requested_window: AvailabilityWindow,
    current_datetime: datetime | None,
) -> None:
    if current_datetime is None or current_datetime.utcoffset() is None:
        raise ValueError(
            "A timezone-aware current datetime is required for availability"
        )
    if requested_window.ends_at < current_datetime:
        raise UnsupportedAvailabilityWindowError(
            "Requested availability is outside the seven-day hours range"
        )

    request_timezone = requested_window.starts_at.tzinfo
    local_current_date = current_datetime.astimezone(
        request_timezone
    ).date()
    last_supported_date = local_current_date + timedelta(
        days=AVAILABILITY_HORIZON_DAYS - 1
    )
    local_end_date = requested_window.ends_at.astimezone(
        request_timezone
    ).date()
    if local_end_date > last_supported_date:
        raise UnsupportedAvailabilityWindowError(
            "Requested availability is outside the seven-day hours range"
        )
