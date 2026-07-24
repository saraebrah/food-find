import re

from app.domain.place import MatchReason, MatchReasonKind, Place
from app.domain.search import SearchCriteria
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
    DescriptiveRequirementKind,
)


def build_match_reasons(
    *,
    place: Place,
    criteria: SearchCriteria,
    descriptive_requirements: tuple[DescriptiveRequirement, ...],
    availability_window: AvailabilityWindow | None,
) -> tuple[MatchReason, ...]:
    """Explain a match from submitted criteria and already-returned data."""

    confirmed: list[MatchReason] = []
    relevance: list[MatchReason] = []
    provider_name = _provider_name(place.provider)

    if place.category:
        category = place.category.strip().rstrip(".")
        confirmed.append(
            _reason(MatchReasonKind.CONFIRMED, f"Category: {category}.")
        )

    confirmed.append(
        _reason(
            MatchReasonKind.CONFIRMED,
            (
                "Inside your selected "
                f"{_format_radius(criteria.radius_meters)} radius."
            ),
        )
    )

    if criteria.filters.open_now and place.open_now is True:
        confirmed.append(
            _reason(
                MatchReasonKind.CONFIRMED,
                f"{provider_name} reports this place open now.",
            )
        )
    if (
        criteria.filters.minimum_rating is not None
        and place.rating is not None
    ):
        confirmed.append(
            _reason(
                MatchReasonKind.CONFIRMED,
                (
                    f"{provider_name} rating {place.rating:.1f} meets your "
                    f"{criteria.filters.minimum_rating.value:.1f} minimum."
                ),
            )
        )
    if criteria.filters.dine_in and place.dine_in is True:
        confirmed.append(
            _reason(
                MatchReasonKind.CONFIRMED,
                f"{provider_name} reports dine-in is available.",
            )
        )
    if criteria.filters.takeout and place.takeout is True:
        confirmed.append(
            _reason(
                MatchReasonKind.CONFIRMED,
                f"{provider_name} reports takeout is available.",
            )
        )
    if availability_window is not None:
        confirmed.append(
            _reason(
                MatchReasonKind.CONFIRMED,
                f"{provider_name} hours overlap your requested time.",
            )
        )

    if criteria.filters.cuisines:
        cuisines = _join_or(
            tuple(cuisine.value.title() for cuisine in criteria.filters.cuisines)
        )
        relevance.append(
            _reason(
                MatchReasonKind.RELEVANCE,
                (
                    f"{cuisines} influenced {provider_name} text relevance; "
                    "the cuisine is not independently verified."
                ),
            )
        )

    if criteria.filters.common_foods:
        foods = tuple(
            food.value.title() for food in criteria.filters.common_foods
        )
        if len(foods) == 1:
            food_text = (
                f"{foods[0]} availability is not verified—"
                "check the menu or call."
            )
        else:
            food_text = (
                f"{_join_or(foods)} influenced {provider_name} text relevance; "
                "menu availability is not verified—check the menu or call."
            )
        relevance.append(_reason(MatchReasonKind.RELEVANCE, food_text))

    active_foods = tuple(
        food.value for food in criteria.filters.common_foods
    )
    seen_requirements: set[tuple[DescriptiveRequirementKind, str]] = set()
    for requirement in descriptive_requirements:
        normalized_text = requirement.text.casefold()
        identity = (requirement.kind, normalized_text)
        if identity in seen_requirements:
            continue
        seen_requirements.add(identity)
        if (
            requirement.kind is DescriptiveRequirementKind.DISH
            and _mentions_active_food(
                text=normalized_text,
                active_foods=active_foods,
            )
        ):
            continue
        relevance.append(
            _descriptive_reason(
                requirement,
                provider_name=provider_name,
            )
        )

    return tuple((*confirmed, *relevance))


def _descriptive_reason(
    requirement: DescriptiveRequirement,
    *,
    provider_name: str,
) -> MatchReason:
    quoted_text = f"“{requirement.text}”"
    if requirement.kind is DescriptiveRequirementKind.DISH:
        suffix = (
            "availability is not verified—check the menu or call."
        )
    elif requirement.kind is DescriptiveRequirementKind.DIETARY:
        suffix = "confirm dietary requirements with the business."
    else:
        suffix = "it is not independently verified."
    return _reason(
        MatchReasonKind.RELEVANCE,
        f"{quoted_text} influenced {provider_name} text relevance; {suffix}",
    )


def _mentions_active_food(
    *,
    text: str,
    active_foods: tuple[str, ...],
) -> bool:
    return any(
        re.search(rf"\b{re.escape(food)}s?\b", text) is not None
        for food in active_foods
    )


def _format_radius(radius_meters: float) -> str:
    if radius_meters < 1_000:
        return f"{radius_meters:g} m"
    kilometres = radius_meters / 1_000
    return f"{kilometres:g} km"


def _join_or(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return f"{', '.join(values[:-1])}, or {values[-1]}"


def _provider_name(provider: str) -> str:
    if provider.casefold() == "google":
        return "Google"
    normalized = provider.replace("_", " ").strip().title()
    return normalized or "Provider"


def _reason(kind: MatchReasonKind, text: str) -> MatchReason:
    return MatchReason(kind=kind, text=text)
