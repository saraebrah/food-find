from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta

from app.application.match_reasons import build_match_reasons
from app.domain.place import Place
from app.domain.search import (
    RatingComparison,
    SearchCriteria,
    SearchSort,
    straight_line_distance_meters,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
)
from app.ports.place_provider import (
    PlaceProvider,
    PlaceProviderError,
)


EXCLUDED_BUSINESS_STATUSES = frozenset(
    ("temporarily_closed", "permanently_closed")
)
AVAILABILITY_HORIZON_DAYS = 7
RESULT_TARGET = 20
MAX_PROVIDER_REQUESTS = 3


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
        normalized_places: list[Place] = []
        seen_place_ids: set[tuple[str, str]] = set()
        used_continuation_tokens: set[str] = set()
        continuation_token: str | None = None

        for request_index in range(MAX_PROVIDER_REQUESTS):
            try:
                page = await self._place_provider.search_nearby(
                    latitude=criteria.location.coordinates.latitude,
                    longitude=criteria.location.coordinates.longitude,
                    radius_meters=criteria.radius_meters,
                    filters=criteria.filters,
                    sort=criteria.sort,
                    descriptive_requirements=descriptive_requirements,
                    availability_window=availability_window,
                    continuation_token=continuation_token,
                )
            except PlaceProviderError:
                if request_index == 0:
                    raise
                break

            for place in page.places:
                place_key = (place.provider, place.provider_place_id)
                if place_key in seen_place_ids:
                    continue
                seen_place_ids.add(place_key)

                normalized_place = _normalize_place(
                    place=place,
                    criteria=criteria,
                    descriptive_requirements=descriptive_requirements,
                    availability_window=availability_window,
                )
                if normalized_place is not None:
                    normalized_places.append(normalized_place)

            continuation_token = page.continuation_token
            if (
                len(normalized_places) >= RESULT_TARGET
                or continuation_token is None
                or continuation_token in used_continuation_tokens
            ):
                break
            used_continuation_tokens.add(continuation_token)

        if criteria.sort is SearchSort.RATING:
            normalized_places.sort(
                key=lambda place: (
                    place.rating is None,
                    -(place.rating or 0),
                )
            )
        elif criteria.sort is SearchSort.DISTANCE:
            normalized_places.sort(
                key=lambda place: place.distance_meters
                if place.distance_meters is not None
                else float("inf")
            )
        return normalized_places[:RESULT_TARGET]


def _normalize_place(
    *,
    place: Place,
    criteria: SearchCriteria,
    descriptive_requirements: tuple[DescriptiveRequirement, ...],
    availability_window: AvailabilityWindow | None,
) -> Place | None:
    distance_meters = straight_line_distance_meters(
        criteria.location.coordinates,
        place.coordinates,
    )
    if distance_meters > criteria.radius_meters:
        return None
    if place.business_status in EXCLUDED_BUSINESS_STATUSES:
        return None
    if criteria.filters.open_now and place.open_now is not True:
        return None
    if criteria.filters.dine_in and place.dine_in is not True:
        return None
    if criteria.filters.takeout and place.takeout is not True:
        return None
    if (
        criteria.filters.minimum_rating is not None
        and (
            place.rating is None
            or (
                criteria.filters.rating_comparison
                is RatingComparison.AT_LEAST
                and place.rating < criteria.filters.minimum_rating
            )
            or (
                criteria.filters.rating_comparison
                is RatingComparison.GREATER_THAN
                and place.rating <= criteria.filters.minimum_rating
            )
        )
    ):
        return None
    if (
        availability_window is not None
        and not _is_available_during(
            place=place,
            requested_window=availability_window,
        )
    ):
        return None
    return replace(
        place,
        distance_meters=distance_meters,
        match_reasons=build_match_reasons(
            place=place,
            criteria=criteria,
            descriptive_requirements=descriptive_requirements,
            availability_window=availability_window,
        ),
    )


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
