from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.domain.location import LocationSuggestion, SelectedLocation
from app.domain.place import Coordinates
from app.main import app, get_location_provider
from app.ports.location_provider import LocationProviderError


SESSION_TOKEN = "550e8400-e29b-41d4-a716-446655440000"


class RecordingLocationProvider:
    def __init__(self) -> None:
        self.suggest_calls: list[dict[str, str]] = []
        self.resolve_calls: list[dict[str, object]] = []

    async def suggest(
        self,
        *,
        query: str,
        session_token: str,
    ) -> Sequence[LocationSuggestion]:
        self.suggest_calls.append({"query": query, "session_token": session_token})
        return [
            LocationSuggestion(
                provider="google",
                provider_place_id="google-location-1",
                label="Union Station, Front Street West, Toronto, ON, Canada",
            )
        ]

    async def resolve(
        self,
        *,
        suggestion: LocationSuggestion,
        session_token: str,
    ) -> SelectedLocation:
        self.resolve_calls.append(
            {"suggestion": suggestion, "session_token": session_token}
        )
        return SelectedLocation(
            label=suggestion.label,
            coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
            provider=suggestion.provider,
            provider_place_id=suggestion.provider_place_id,
        )


class FailingLocationProvider:
    async def suggest(
        self,
        *,
        query: str,
        session_token: str,
    ) -> Sequence[LocationSuggestion]:
        raise LocationProviderError("private provider details")

    async def resolve(
        self,
        *,
        suggestion: LocationSuggestion,
        session_token: str,
    ) -> SelectedLocation:
        raise LocationProviderError("private provider details")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_autocomplete_returns_normalized_suggestions(client: TestClient) -> None:
    provider = RecordingLocationProvider()
    app.dependency_overrides[get_location_provider] = lambda: provider

    response = client.post(
        "/api/locations/autocomplete",
        json={"query": "Union Station", "session_token": SESSION_TOKEN},
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert provider.suggest_calls == [
        {"query": "Union Station", "session_token": SESSION_TOKEN}
    ]
    assert response.json() == [
        {
            "provider": "google",
            "provider_place_id": "google-location-1",
            "label": "Union Station, Front Street West, Toronto, ON, Canada",
        }
    ]


def test_page_loads_do_not_construct_location_provider(client: TestClient) -> None:
    dependency_call_count = 0

    def override_location_provider() -> RecordingLocationProvider:
        nonlocal dependency_call_count
        dependency_call_count += 1
        return RecordingLocationProvider()

    app.dependency_overrides[get_location_provider] = override_location_provider

    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 200
    assert dependency_call_count == 0


def test_autocomplete_rejects_short_queries_without_calling_provider(
    client: TestClient,
) -> None:
    provider = RecordingLocationProvider()
    app.dependency_overrides[get_location_provider] = lambda: provider

    response = client.post(
        "/api/locations/autocomplete",
        json={"query": "Un", "session_token": SESSION_TOKEN},
    )

    assert response.status_code == 422
    assert provider.suggest_calls == []


def test_resolve_returns_normalized_selected_location(client: TestClient) -> None:
    provider = RecordingLocationProvider()
    app.dependency_overrides[get_location_provider] = lambda: provider

    response = client.post(
        "/api/locations/resolve",
        json={
            "provider_place_id": "google-location-1",
            "label": "Union Station, Front Street West, Toronto, ON, Canada",
            "session_token": SESSION_TOKEN,
        },
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert provider.resolve_calls == [
        {
            "suggestion": LocationSuggestion(
                provider="google",
                provider_place_id="google-location-1",
                label="Union Station, Front Street West, Toronto, ON, Canada",
            ),
            "session_token": SESSION_TOKEN,
        }
    ]
    assert response.json() == {
        "label": "Union Station, Front Street West, Toronto, ON, Canada",
        "latitude": 43.6453,
        "longitude": -79.3806,
        "provider": "google",
        "provider_place_id": "google-location-1",
    }


@pytest.mark.parametrize(
    ("path", "request_json"),
    (
        (
            "/api/locations/autocomplete",
            {"query": "Union Station", "session_token": SESSION_TOKEN},
        ),
        (
            "/api/locations/resolve",
            {
                "provider_place_id": "google-location-1",
                "label": "Union Station, Toronto",
                "session_token": SESSION_TOKEN,
            },
        ),
    ),
)
def test_location_endpoints_return_safe_provider_error(
    client: TestClient,
    path: str,
    request_json: dict[str, str],
) -> None:
    app.dependency_overrides[get_location_provider] = lambda: FailingLocationProvider()

    response = client.post(path, json=request_json)

    assert response.status_code == 502
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"detail": "Location service is temporarily unavailable"}
    assert "private provider details" not in response.text


def test_autocomplete_rejects_non_v4_session_token(client: TestClient) -> None:
    provider = RecordingLocationProvider()
    app.dependency_overrides[get_location_provider] = lambda: provider

    response = client.post(
        "/api/locations/autocomplete",
        json={
            "query": "Union Station",
            "session_token": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        },
    )

    assert response.status_code == 422
    assert provider.suggest_calls == []
