from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.domain.place import Coordinates, Place
from app.main import app, get_place_provider


class RecordingPlaceProvider:
    def __init__(self) -> None:
        self.call_count = 0
        self.searches: list[dict[str, object]] = []

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> Sequence[Place]:
        self.call_count += 1
        self.searches.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "radius_meters": radius_meters,
                "included_types": tuple(included_types),
            }
        )
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
    assert 'id="location-input"' in response.text
    assert '<label for="location-input">Location</label>' in response.text
    assert 'inputmode="search"' in response.text
    assert 'aria-autocomplete="list"' in response.text
    assert 'id="location-suggestions"' in response.text
    assert 'translate="no">Google Maps' in response.text
    assert 'id="radius-select"' in response.text
    assert '<option value="500">500 m</option>' in response.text
    assert '<option value="1000" selected>1 km</option>' in response.text
    assert '<option value="2000">2 km</option>' in response.text
    assert '<option value="5000">5 km</option>' in response.text
    assert 'id="search-status"' in response.text
    assert 'id="place-results"' in response.text
    assert '/static/search.js' in response.text


def test_search_script_is_served_as_a_static_asset(client: TestClient) -> None:
    response = client.get("/static/search.js")

    assert response.status_code == 200
    assert 'addEventListener("click"' in response.text
    assert 'method: "POST"' in response.text
    assert '"Content-Type": "application/json"' in response.text
    assert 'setTimeout(requestSuggestions, 350)' in response.text
    assert 'crypto.randomUUID()' in response.text
    assert 'looksLikeCoordinatePair(query)' in response.text
    assert 'radiusSelect.addEventListener("change"' in response.text


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

    response = client.post(
        "/api/places/search",
        json={
            "location": {
                "label": "Union Station coordinates",
                "latitude": 43.6453,
                "longitude": -79.3806,
            },
            "radius_meters": 2_000,
        },
    )

    assert response.status_code == 200
    assert dependency_call_count == 1
    assert provider.call_count == 1
    assert provider.searches == [
        {
            "latitude": 43.6453,
            "longitude": -79.3806,
            "radius_meters": 2_000,
            "included_types": ("restaurant", "cafe"),
        }
    ]
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


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    (
        (90.0001, -79.3806),
        (-90.0001, -79.3806),
        (43.6453, 180.0001),
        (43.6453, -180.0001),
    ),
)
def test_search_rejects_out_of_range_coordinates_without_searching(
    client: TestClient,
    latitude: float,
    longitude: float,
) -> None:
    provider = RecordingPlaceProvider()
    app.dependency_overrides[get_place_provider] = lambda: provider

    response = client.post(
        "/api/places/search",
        json={
            "location": {
                "label": "Invalid coordinates",
                "latitude": latitude,
                "longitude": longitude,
            },
            "radius_meters": 1_000,
        },
    )

    assert response.status_code == 422
    assert provider.call_count == 0


@pytest.mark.parametrize("radius_meters", (99, 50_001))
def test_search_rejects_out_of_range_radius_without_searching(
    client: TestClient,
    radius_meters: int,
) -> None:
    provider = RecordingPlaceProvider()
    app.dependency_overrides[get_place_provider] = lambda: provider

    response = client.post(
        "/api/places/search",
        json={
            "location": {
                "label": "Union Station coordinates",
                "latitude": 43.6453,
                "longitude": -79.3806,
            },
            "radius_meters": radius_meters,
        },
    )

    assert response.status_code == 422
    assert provider.call_count == 0
