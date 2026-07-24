import json
from typing import Protocol

from google.genai import types
from pydantic import ValidationError

from app.application.search_intent_output import SearchIntentOutput
from app.domain.search import SearchCriteria
from app.domain.search_interpretation import (
    SearchCapabilities,
    SearchInterpretationContext,
)
from app.domain.search_intent import SearchIntent
from app.ports.search_interpreter import SearchInterpreterError


GEMINI_SYSTEM_INSTRUCTION = """
You interpret natural-language food-place searches for FoodFind.
Return one complete SearchIntentOutput and follow its allowed enum values exactly.

Rules:
- Preserve current values when the user does not change them.
- Multiple values within one filter group mean OR. Different groups combine with AND.
- Good rated means a minimum rating of 4.0.
- Highly rated means a minimum rating of 4.5.
- Best or top rated means rating sort without inventing a minimum rating.
- Keep useful dish, dietary, atmosphere, or other descriptive requirements even
  when they do not have a dedicated filter.
- Text relevance is not proof that a place satisfies a descriptive requirement.
- Use only values and behavior listed in the FoodFind capabilities.
- "Near me" means the selected location in the supplied context. Record that
  interpretation as an assumption.
- Do not invent a different location, coordinates, provider fields, menu facts, or
  unsupported filter values.
- Resolve availability language using current_datetime and timezone:
  - Tonight means 6:00 p.m. to midnight.
  - Dinner means 5:00 p.m. to 10:00 p.m.
  - For an exact time such as "at 7 p.m.", set starts_at and ends_at to the same
    instant; do not invent a duration.
  - If an implied window is underway, use current_datetime as starts_at.
  - If an implied time or window has fully passed, use its next occurrence and
    record that assumption. Do not move an explicit past date; mark it unsupported.
  - Use ISO 8601 datetimes with the correct UTC offset for the supplied timezone.
  - Availability must end within availability_horizon_days, counting today as
    day one. If it does not, leave availability_window null and mark it unsupported.
- Use open_now only for a request about the present moment. Do not approximate a
  future or broader availability window as open_now.
- While explicit_location_resolution is false, mark requests to change to another
  location as unsupported. Do not replace the selected location.
- Record each ambiguity you resolve in assumptions.
- Put any criterion that cannot be represented safely in unsupported_criteria.
""".strip()


class GeminiModels(Protocol):
    async def generate_content(self, **kwargs: object) -> object: ...


class GeminiSearchInterpreter:
    def __init__(self, *, models: GeminiModels, model: str) -> None:
        self._models = models
        self._model = model

    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        try:
            response = await self._models.generate_content(
                model=self._model,
                contents=self._build_contents(
                    query=query,
                    search_criteria=search_criteria,
                    context=context,
                ),
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=SearchIntentOutput,
                ),
            )
        except Exception as error:
            raise SearchInterpreterError(
                "Gemini could not interpret the search"
            ) from error

        try:
            parsed = getattr(response, "parsed", None)
            if parsed is None:
                raise ValueError("Gemini returned no parsed search intent")
            output = SearchIntentOutput.model_validate(parsed)
            return output.to_domain(base_criteria=search_criteria)
        except (ValidationError, ValueError, TypeError) as error:
            raise SearchInterpreterError(
                "Gemini could not interpret the search"
            ) from error

    @staticmethod
    def _build_contents(
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> str:
        filters = search_criteria.filters
        current_state = {
            "selected_location": {
                "label": search_criteria.location.label,
                "latitude": search_criteria.location.coordinates.latitude,
                "longitude": search_criteria.location.coordinates.longitude,
            },
            "radius_meters": search_criteria.radius_meters,
            "filters": {
                "place_types": [value.value for value in filters.place_types],
                "cuisines": [value.value for value in filters.cuisines],
                "common_foods": [
                    value.value for value in filters.common_foods
                ],
                "open_now": filters.open_now,
                "minimum_rating": (
                    filters.minimum_rating.value
                    if filters.minimum_rating is not None
                    else None
                ),
                "dine_in": filters.dine_in,
                "takeout": filters.takeout,
            },
            "sort": search_criteria.sort.value,
        }
        interpretation_context = {
            "current_date": context.current_date.isoformat(),
            "current_datetime": context.local_datetime.isoformat(),
            "timezone": context.timezone_name,
            "capabilities": GeminiSearchInterpreter._serialize_capabilities(
                context.capabilities
            ),
        }
        return "\n".join(
            (
                f"User request: {query}",
                "Current editable search state:",
                json.dumps(current_state, separators=(",", ":"), sort_keys=True),
                "Interpretation context:",
                json.dumps(
                    interpretation_context,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        )

    @staticmethod
    def _serialize_capabilities(
        capabilities: SearchCapabilities,
    ) -> dict[str, object]:
        return {
            "place_types": [
                value.value for value in capabilities.place_types
            ],
            "cuisines": [value.value for value in capabilities.cuisines],
            "common_foods": [
                value.value for value in capabilities.common_foods
            ],
            "minimum_ratings": [
                value.value for value in capabilities.minimum_ratings
            ],
            "sort_options": [
                value.value for value in capabilities.sort_options
            ],
            "descriptive_requirement_kinds": [
                value.value
                for value in capabilities.descriptive_requirement_kinds
            ],
            "minimum_radius_meters": capabilities.minimum_radius_meters,
            "maximum_radius_meters": capabilities.maximum_radius_meters,
            "open_now": capabilities.open_now,
            "dine_in": capabilities.dine_in,
            "takeout": capabilities.takeout,
            "selected_location_reference": (
                capabilities.selected_location_reference
            ),
            "explicit_location_resolution": (
                capabilities.explicit_location_resolution
            ),
            "time_aware_availability": (
                capabilities.time_aware_availability
            ),
            "availability_horizon_days": (
                capabilities.availability_horizon_days
            ),
            "device_location": capabilities.device_location,
        }
