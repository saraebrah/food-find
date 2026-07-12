from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.domain.place import Coordinates, Place
from app.main import app, get_place_provider


class RecordingPlaceProvider:
    def __init__(self) -> None:
        self.call_count = 0

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> Sequence[Place]:
        self.call_count += 1
        return [
            Place(
                provider="google",
                provider_place_id="google-place-1",
                name="Example Restaurant",
                category="Restaurant",
                category_code="restaurant",
                address="1 Front Street, Toronto, ON",
                coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
            )
        ]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_home_page_renders_foodfind_shell(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "FoodFind" in response.text
    assert "Nearby food discovery starts here." in response.text
    assert 'id="search-button"' in response.text
    assert 'type="button"' in response.text
    assert 'id="search-status"' in response.text
    assert 'id="place-results"' in response.text
    assert '/static/search.js' in response.text


def test_search_script_is_served_as_a_static_asset(client: TestClient) -> None:
    response = client.get("/static/search.js")

    assert response.status_code == 200
    assert 'addEventListener("click"' in response.text
    assert 'method: "POST"' in response.text


def test_page_loads_do_not_search_provider(client: TestClient) -> None:
    provider = RecordingPlaceProvider()
    dependency_call_count = 0

    def override_place_provider() -> RecordingPlaceProvider:
        nonlocal dependency_call_count
        dependency_call_count += 1
        return provider

    app.dependency_overrides[get_place_provider] = override_place_provider

    first_response = client.get("/")
    reload_response = client.get("/")

    assert first_response.status_code == 200
    assert reload_response.status_code == 200
    assert dependency_call_count == 0
    assert provider.call_count == 0


def test_explicit_search_calls_provider_once_and_returns_places(
    client: TestClient,
) -> None:
    provider = RecordingPlaceProvider()
    dependency_call_count = 0

    def override_place_provider() -> RecordingPlaceProvider:
        nonlocal dependency_call_count
        dependency_call_count += 1
        return provider

    app.dependency_overrides[get_place_provider] = override_place_provider

    response = client.post("/api/places/search")

    assert response.status_code == 200
    assert dependency_call_count == 1
    assert provider.call_count == 1
    assert response.json() == [
        {
            "provider": "google",
            "provider_place_id": "google-place-1",
            "name": "Example Restaurant",
            "category": "Restaurant",
            "category_code": "restaurant",
            "address": "1 Front Street, Toronto, ON",
            "coordinates": {"latitude": 43.6454, "longitude": -79.3805},
        }
    ]
