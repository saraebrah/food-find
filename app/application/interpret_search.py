import re
from dataclasses import replace
from datetime import timedelta
from zoneinfo import ZoneInfo

from app.domain.search import SearchCriteria
from app.domain.search_interpretation import SearchInterpretationContext
from app.domain.search_intent import (
    AvailabilityWindow,
    ResolvedAssumption,
    SearchIntent,
)
from app.ports.search_interpreter import SearchInterpreter, SearchInterpreterError


NEAR_ME_PATTERN = re.compile(r"\bnear\s+me\b", re.IGNORECASE)


class InterpretSearch:
    def __init__(self, *, interpreter: SearchInterpreter) -> None:
        self._interpreter = interpreter

    async def execute(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query must not be blank")
        intent = await self._interpreter.interpret(
            query=normalized_query,
            search_criteria=search_criteria,
            context=context,
        )
        self._validate_capabilities(intent=intent, context=context)
        intent = replace(
            intent,
            search_criteria=replace(
                intent.search_criteria,
                location=search_criteria.location,
            ),
        )
        intent = self._normalize_availability(intent=intent, context=context)
        if not NEAR_ME_PATTERN.search(normalized_query):
            return intent

        assumptions = tuple(
            assumption
            for assumption in intent.assumptions
            if not NEAR_ME_PATTERN.search(assumption.source_text)
        )
        return replace(
            intent,
            assumptions=(
                *assumptions,
                ResolvedAssumption(
                    source_text="near me",
                    interpretation=(
                        "Using the selected location: "
                        f"{search_criteria.location.label}"
                    ),
                ),
            ),
        )

    @staticmethod
    def _validate_capabilities(
        *,
        intent: SearchIntent,
        context: SearchInterpretationContext,
    ) -> None:
        capabilities = context.capabilities
        criteria = intent.search_criteria
        filters = criteria.filters
        unsupported = (
            not (
                capabilities.minimum_radius_meters
                <= criteria.radius_meters
                <= capabilities.maximum_radius_meters
            )
            or any(
                place_type not in capabilities.place_types
                for place_type in filters.place_types
            )
            or any(
                cuisine not in capabilities.cuisines
                for cuisine in filters.cuisines
            )
            or any(
                food not in capabilities.common_foods
                for food in filters.common_foods
            )
            or (
                filters.minimum_rating is not None
                and filters.minimum_rating
                not in capabilities.minimum_ratings
            )
            or criteria.sort not in capabilities.sort_options
            or (filters.open_now and not capabilities.open_now)
            or (filters.dine_in and not capabilities.dine_in)
            or (filters.takeout and not capabilities.takeout)
            or any(
                requirement.kind
                not in capabilities.descriptive_requirement_kinds
                for requirement in intent.descriptive_requirements
            )
            or (
                intent.availability_window is not None
                and not capabilities.time_aware_availability
            )
        )
        if unsupported:
            raise SearchInterpreterError(
                "Interpreter returned unsupported criteria"
            )

    @staticmethod
    def _normalize_availability(
        *,
        intent: SearchIntent,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        window = intent.availability_window
        if window is None:
            return intent
        timezone = ZoneInfo(context.timezone_name)
        starts_at = window.starts_at.astimezone(timezone)
        ends_at = window.ends_at.astimezone(timezone)
        if (
            window.starts_at.utcoffset() != starts_at.utcoffset()
            or window.ends_at.utcoffset() != ends_at.utcoffset()
        ):
            raise SearchInterpreterError(
                "Interpreter returned an invalid availability window timezone"
            )

        current_datetime = context.local_datetime
        if ends_at < current_datetime:
            raise SearchInterpreterError(
                "Interpreter returned an availability window in the past"
            )
        last_supported_date = context.current_date + timedelta(
            days=context.capabilities.availability_horizon_days - 1
        )
        if ends_at.date() > last_supported_date:
            raise SearchInterpreterError(
                "Interpreter returned availability beyond the supported horizon"
            )
        if starts_at < current_datetime:
            starts_at = current_datetime

        return replace(
            intent,
            availability_window=AvailabilityWindow(
                starts_at=starts_at,
                ends_at=ends_at,
            ),
        )
