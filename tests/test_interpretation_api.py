from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.domain.search import (
    CommonFood,
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchCriteria,
    SearchFilters,
    SearchSort,
)
from app.domain.search_interpretation import SearchInterpretationContext
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
    DescriptiveRequirementKind,
    ResolvedAssumption,
    SearchIntent,
    UnsupportedCriterion,
)
from app.main import (
    app,
    get_current_datetime,
    get_search_interpreter,
)
from app.ports.search_interpreter import SearchInterpreterError


CURRENT_DATETIME = datetime(2026, 7, 23, 15, 30, tzinfo=timezone.utc)


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
        return SearchIntent(
            search_criteria=SearchCriteria(
                location=search_criteria.location,
                radius_meters=2_000,
                filters=SearchFilters(
                    place_types=(PlaceType.RESTAURANT,),
                    cuisines=(Cuisine.PERSIAN,),
                    common_foods=(CommonFood.KEBAB,),
                    minimum_rating=MinimumRating.FOUR,
                    dine_in=True,
                ),
                sort=SearchSort.RATING,
            ),
            descriptive_requirements=(
                DescriptiveRequirement(
                    text="serves kebab",
                    kind=DescriptiveRequirementKind.DISH,
                ),
            ),
            availability_window=AvailabilityWindow(
                starts_at=datetime.fromisoformat(
                    "2026-07-23T18:00:00-04:00"
                ),
                ends_at=datetime.fromisoformat(
                    "2026-07-24T00:00:00-04:00"
                ),
            ),
            assumptions=(
                ResolvedAssumption(
                    source_text="good rated",
                    interpretation="Minimum rating of 4.0",
                ),
            ),
            unsupported_criteria=(
                UnsupportedCriterion(
                    text="not crowded",
                    reason="Current crowd levels are unavailable",
                ),
            ),
        )


class FailingInterpreter:
    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent:
        raise SearchInterpreterError("private Gemini failure")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def request_payload() -> dict[str, object]:
    return {
        "query": "good rated Persian restaurant serving kebab near me tonight",
        "timezone": "America/Toronto",
        "search_criteria": {
            "location": {
                "label": "318 King St E, Toronto",
                "latitude": 43.6519,
                "longitude": -79.3642,
            },
            "radius_meters": 1_000,
            "filters": {
                "place_types": ["restaurant", "cafe"],
                "cuisines": [],
                "common_foods": [],
                "open_now": False,
                "minimum_rating": None,
                "dine_in": False,
                "takeout": False,
            },
            "sort": "provider_default",
        },
    }


def test_explicit_interpretation_returns_editable_intent_once(
    client: TestClient,
) -> None:
    interpreter = RecordingInterpreter()
    app.dependency_overrides[get_search_interpreter] = lambda: interpreter
    app.dependency_overrides[get_current_datetime] = lambda: CURRENT_DATETIME

    response = client.post("/api/search/interpret", json=request_payload())

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(interpreter.calls) == 1
    query, criteria, context = interpreter.calls[0]
    assert query.endswith("near me tonight")
    assert criteria.location.label == "318 King St E, Toronto"
    assert context.local_datetime.isoformat() == "2026-07-23T11:30:00-04:00"
    assert context.timezone_name == "America/Toronto"
    assert response.json() == {
        "search_criteria": {
            "location": {
                "label": "318 King St E, Toronto",
                "latitude": 43.6519,
                "longitude": -79.3642,
                "provider": None,
                "provider_place_id": None,
            },
            "radius_meters": 2_000.0,
            "filters": {
                "place_types": ["restaurant"],
                "cuisines": ["persian"],
                "common_foods": ["kebab"],
                "open_now": False,
                "minimum_rating": 4.0,
                "dine_in": True,
                "takeout": False,
            },
            "sort": "rating",
        },
        "descriptive_requirements": [
            {"text": "serves kebab", "kind": "dish"}
        ],
        "availability_window": {
            "starts_at": "2026-07-23T18:00:00-04:00",
            "ends_at": "2026-07-24T00:00:00-04:00",
        },
        "assumptions": [
            {
                "source_text": "good rated",
                "interpretation": "Minimum rating of 4.0",
            },
            {
                "source_text": "near me",
                "interpretation": (
                    "Using the selected location: 318 King St E, Toronto"
                ),
            },
        ],
        "unsupported_criteria": [
            {
                "text": "not crowded",
                "reason": "Current crowd levels are unavailable",
            }
        ],
        "timezone": "America/Toronto",
    }


def test_interpretation_rejects_invalid_timezone(client: TestClient) -> None:
    interpreter = RecordingInterpreter()
    app.dependency_overrides[get_search_interpreter] = lambda: interpreter
    payload = request_payload()
    payload["timezone"] = "Toronto/Unknown"

    response = client.post("/api/search/interpret", json=payload)

    assert response.status_code == 422


def test_interpretation_rejects_search_only_review_fields(
    client: TestClient,
) -> None:
    interpreter = RecordingInterpreter()
    app.dependency_overrides[get_search_interpreter] = lambda: interpreter
    payload = request_payload()
    search_criteria = payload["search_criteria"]
    assert isinstance(search_criteria, dict)
    search_criteria["descriptive_requirements"] = [
        {"text": "quiet atmosphere", "kind": "atmosphere"}
    ]

    response = client.post("/api/search/interpret", json=payload)

    assert response.status_code == 422
    assert interpreter.calls == []


def test_interpretation_returns_safe_provider_error(client: TestClient) -> None:
    app.dependency_overrides[get_search_interpreter] = FailingInterpreter
    app.dependency_overrides[get_current_datetime] = lambda: CURRENT_DATETIME

    response = client.post("/api/search/interpret", json=request_payload())

    assert response.status_code == 502
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "detail": "Smart search is temporarily unavailable"
    }
    assert "private Gemini failure" not in response.text
