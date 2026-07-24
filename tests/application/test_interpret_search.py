from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.application.interpret_search import InterpretSearch
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates
from app.domain.search import SearchCriteria, SearchFilters
from app.domain.search_interpretation import (
    FOODFIND_SEARCH_CAPABILITIES,
    SearchInterpretationContext,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    ResolvedAssumption,
    SearchIntent,
)
from app.ports.search_interpreter import SearchInterpreterError


def make_criteria() -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="318 King St E, Toronto",
            coordinates=Coordinates(latitude=43.6519, longitude=-79.3642),
        ),
        radius_meters=1_000,
    )


class RecordingInterpreter:
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, SearchCriteria, SearchInterpretationContext]
        ] = []

    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        self.calls.append((query, search_criteria, context))
        return SearchIntent(search_criteria=search_criteria)


class FailingInterpreter:
    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        raise SearchInterpreterError("private Gemini details")


class InconsistentNearMeInterpreter:
    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        return SearchIntent(
            search_criteria=SearchCriteria(
                location=SelectedLocation(
                    label="A different location",
                    coordinates=Coordinates(latitude=0, longitude=0),
                ),
                radius_meters=search_criteria.radius_meters,
            ),
            assumptions=(
                ResolvedAssumption(
                    source_text="near me",
                    interpretation="Using a different location",
                ),
                ResolvedAssumption(
                    source_text="Persian",
                    interpretation="Cuisine: Persian",
                ),
            ),
        )


class AvailabilityInterpreter:
    def __init__(self, window: AvailabilityWindow) -> None:
        self._window = window

    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        return SearchIntent(
            search_criteria=search_criteria,
            availability_window=self._window,
        )


class DineInInterpreter:
    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        return SearchIntent(
            search_criteria=replace(
                search_criteria,
                filters=SearchFilters(dine_in=True),
            )
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
async def test_interpret_search_normalizes_and_delegates_once() -> None:
    interpreter = RecordingInterpreter()
    use_case = InterpretSearch(interpreter=interpreter)
    criteria = make_criteria()
    context = make_context()

    intent = await use_case.execute(
        query="  highly rated Persian restaurant  ",
        search_criteria=criteria,
        context=context,
    )

    assert intent == SearchIntent(search_criteria=criteria)
    assert interpreter.calls == [
        ("highly rated Persian restaurant", criteria, context),
    ]


@pytest.mark.anyio
async def test_interpret_search_resolves_near_me_to_submitted_location() -> None:
    use_case = InterpretSearch(interpreter=InconsistentNearMeInterpreter())
    criteria = make_criteria()

    intent = await use_case.execute(
        query="Persian restaurant near me",
        search_criteria=criteria,
        context=make_context(),
    )

    assert intent.assumptions == (
        ResolvedAssumption(
            source_text="Persian",
            interpretation="Cuisine: Persian",
        ),
        ResolvedAssumption(
            source_text="near me",
            interpretation=(
                "Using the selected location: 318 King St E, Toronto"
            ),
        ),
    )
    assert intent.search_criteria.location is criteria.location


@pytest.mark.anyio
async def test_interpret_search_clamps_an_underway_window_to_current_time() -> None:
    toronto = ZoneInfo("America/Toronto")
    context = SearchInterpretationContext(
        current_datetime=datetime(2026, 7, 23, 18, 30, tzinfo=toronto),
        timezone_name="America/Toronto",
    )
    use_case = InterpretSearch(
        interpreter=AvailabilityInterpreter(
            AvailabilityWindow(
                starts_at=datetime(2026, 7, 23, 17, tzinfo=toronto),
                ends_at=datetime(2026, 7, 23, 22, tzinfo=toronto),
            )
        )
    )

    intent = await use_case.execute(
        query="restaurant open for dinner",
        search_criteria=make_criteria(),
        context=context,
    )

    assert intent.availability_window == AvailabilityWindow(
        starts_at=context.local_datetime,
        ends_at=datetime(2026, 7, 23, 22, tzinfo=toronto),
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "window",
    (
        AvailabilityWindow(
            starts_at=datetime(
                2026,
                7,
                23,
                18,
                tzinfo=timezone(timedelta(hours=-5)),
            ),
            ends_at=datetime(
                2026,
                7,
                23,
                22,
                tzinfo=timezone(timedelta(hours=-5)),
            ),
        ),
        AvailabilityWindow(
            starts_at=datetime(
                2026,
                7,
                23,
                9,
                tzinfo=ZoneInfo("America/Toronto"),
            ),
            ends_at=datetime(
                2026,
                7,
                23,
                10,
                tzinfo=ZoneInfo("America/Toronto"),
            ),
        ),
    ),
)
async def test_interpret_search_rejects_invalid_availability_for_context(
    window: AvailabilityWindow,
) -> None:
    use_case = InterpretSearch(interpreter=AvailabilityInterpreter(window))

    with pytest.raises(SearchInterpreterError, match="availability window"):
        await use_case.execute(
            query="restaurant open at a requested time",
            search_criteria=make_criteria(),
            context=make_context(),
        )


@pytest.mark.anyio
async def test_interpret_search_rejects_availability_beyond_provider_horizon() -> None:
    toronto = ZoneInfo("America/Toronto")
    use_case = InterpretSearch(
        interpreter=AvailabilityInterpreter(
            AvailabilityWindow(
                starts_at=datetime(2026, 7, 29, 18, tzinfo=toronto),
                ends_at=datetime(2026, 7, 30, 0, tzinfo=toronto),
            )
        )
    )

    with pytest.raises(SearchInterpreterError, match="supported horizon"):
        await use_case.execute(
            query="restaurant open next Thursday",
            search_criteria=make_criteria(),
            context=make_context(),
        )


@pytest.mark.anyio
async def test_interpret_search_rejects_a_disabled_provider_capability() -> None:
    context = replace(
        make_context(),
        capabilities=replace(
            FOODFIND_SEARCH_CAPABILITIES,
            dine_in=False,
        ),
    )

    with pytest.raises(SearchInterpreterError, match="unsupported criteria"):
        await InterpretSearch(interpreter=DineInInterpreter()).execute(
            query="restaurant with dine-in",
            search_criteria=make_criteria(),
            context=context,
        )


@pytest.mark.anyio
async def test_interpret_search_rejects_blank_input_without_calling_adapter() -> None:
    interpreter = RecordingInterpreter()
    use_case = InterpretSearch(interpreter=interpreter)

    with pytest.raises(ValueError, match="must not be blank"):
        await use_case.execute(
            query="   ",
            search_criteria=make_criteria(),
            context=make_context(),
        )

    assert interpreter.calls == []


@pytest.mark.anyio
async def test_interpret_search_preserves_provider_neutral_errors() -> None:
    use_case = InterpretSearch(interpreter=FailingInterpreter())

    with pytest.raises(SearchInterpreterError, match="private Gemini details"):
        await use_case.execute(
            query="Persian restaurant",
            search_criteria=make_criteria(),
            context=make_context(),
        )
