from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.adapters.gemini_search_interpreter import (
    GEMINI_SYSTEM_INSTRUCTION,
    GeminiSearchInterpreter,
)
from app.application.search_intent_output import SearchIntentOutput
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates
from app.domain.search import MinimumRating, SearchCriteria, SearchSort
from app.domain.search_interpretation import SearchInterpretationContext
from app.ports.search_interpreter import SearchInterpreterError


class RecordingModels:
    def __init__(
        self,
        *,
        parsed: SearchIntentOutput | dict[str, object] | None,
        error: Exception | None = None,
    ) -> None:
        self.parsed = parsed
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(parsed=self.parsed)


def make_criteria() -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="Private selected location",
            coordinates=Coordinates(latitude=43.6519, longitude=-79.3642),
        ),
        radius_meters=1_000,
    )


def valid_output() -> SearchIntentOutput:
    return SearchIntentOutput.model_validate(
        {
            "radius_meters": 1_000,
            "filters": {
                "place_types": ["restaurant"],
                "cuisines": ["persian"],
                "common_foods": [],
                "open_now": False,
                "minimum_rating": 4.5,
                "dine_in": False,
                "takeout": False,
            },
            "sort": "rating",
            "descriptive_requirements": [],
            "availability_window": None,
            "assumptions": [
                {
                    "source_text": "highly rated",
                    "interpretation": "Minimum rating of 4.5",
                }
            ],
            "unsupported_criteria": [],
        }
    )


def make_context() -> SearchInterpretationContext:
    return SearchInterpretationContext(
        current_datetime=datetime(
            2026,
            7,
            23,
            11,
            30,
            tzinfo=ZoneInfo("America/Toronto"),
        ),
        timezone_name="America/Toronto",
    )


@pytest.mark.anyio
async def test_gemini_uses_structured_output_with_step_four_context() -> None:
    models = RecordingModels(parsed=valid_output())
    interpreter = GeminiSearchInterpreter(
        models=models,
        model="gemini-3.6-flash",
    )

    intent = await interpreter.interpret(
        query="highly rated Persian restaurant near me",
        search_criteria=make_criteria(),
        context=make_context(),
    )

    assert intent.search_criteria.filters.minimum_rating is MinimumRating.FOUR_AND_HALF
    assert intent.search_criteria.sort is SearchSort.RATING
    assert len(models.calls) == 1
    call = models.calls[0]
    assert call["model"] == "gemini-3.6-flash"
    contents = str(call["contents"])
    assert "highly rated Persian restaurant near me" in contents
    assert "Private selected location" in contents
    assert "43.6519" in contents
    assert "-79.3642" in contents
    assert '"current_date":"2026-07-23"' in contents
    assert '"current_datetime":"2026-07-23T11:30:00-04:00"' in contents
    assert '"timezone":"America/Toronto"' in contents
    assert '"place_types":["restaurant","cafe","bar","bakery"]' in contents
    assert '"time_aware_availability":true' in contents
    assert '"availability_horizon_days":7' in contents
    assert '"device_location":false' in contents
    config = call["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is SearchIntentOutput
    assert config.system_instruction == GEMINI_SYSTEM_INSTRUCTION
    assert "Good rated means a minimum rating of 4.0" in GEMINI_SYSTEM_INSTRUCTION
    assert "near me" in GEMINI_SYSTEM_INSTRUCTION.lower()
    assert "Tonight means 6:00 p.m. to midnight" in GEMINI_SYSTEM_INSTRUCTION
    assert (
        "set starts_at and ends_at to the same"
        in GEMINI_SYSTEM_INSTRUCTION
    )


@pytest.mark.anyio
async def test_gemini_accepts_a_timezone_aware_availability_window() -> None:
    payload = valid_output().model_dump(mode="json")
    payload["availability_window"] = {
        "starts_at": "2026-07-23T18:00:00-04:00",
        "ends_at": "2026-07-24T00:00:00-04:00",
    }
    payload["assumptions"] = [
        {
            "source_text": "tonight",
            "interpretation": "6:00 p.m. to midnight in America/Toronto",
        }
    ]
    output = SearchIntentOutput.model_validate(payload)
    models = RecordingModels(parsed=output.model_dump(mode="json"))
    interpreter = GeminiSearchInterpreter(
        models=models,
        model="gemini-3.6-flash",
    )

    intent = await interpreter.interpret(
        query="Persian restaurant open tonight",
        search_criteria=make_criteria(),
        context=make_context(),
    )

    assert intent.availability_window is not None
    assert intent.availability_window.starts_at.isoformat() == (
        "2026-07-23T18:00:00-04:00"
    )


@pytest.mark.anyio
async def test_gemini_revalidates_dictionary_output() -> None:
    models = RecordingModels(parsed=valid_output().model_dump(mode="json"))
    interpreter = GeminiSearchInterpreter(
        models=models,
        model="gemini-3.6-flash",
    )

    intent = await interpreter.interpret(
        query="Persian restaurant",
        search_criteria=make_criteria(),
        context=make_context(),
    )

    assert intent.search_criteria.filters.minimum_rating is MinimumRating.FOUR_AND_HALF


@pytest.mark.anyio
@pytest.mark.parametrize(
    "models",
    (
        RecordingModels(parsed=None),
        RecordingModels(parsed={"invalid": "output"}),
        RecordingModels(parsed=None, error=RuntimeError("private SDK failure")),
    ),
)
async def test_gemini_converts_provider_failures_to_safe_domain_error(
    models: RecordingModels,
) -> None:
    interpreter = GeminiSearchInterpreter(
        models=models,
        model="gemini-3.6-flash",
    )

    with pytest.raises(
        SearchInterpreterError,
        match="Gemini could not interpret the search",
    ) as error:
        await interpreter.interpret(
            query="Persian restaurant",
            search_criteria=make_criteria(),
            context=make_context(),
        )

    assert "private SDK failure" not in str(error.value)
