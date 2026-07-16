from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from app.domain.place import Coordinates, Place, PlaceDetails
from app.main import app, get_place_provider
from app.ports.place_provider import PlaceProviderError


class RecordingPlaceProvider:
    provider_name = "google"

    def __init__(self) -> None:
        self.call_count = 0
        self.detail_call_count = 0
        self.searches: list[dict[str, object]] = []
        self.detail_place_ids: list[str] = []

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
                business_status="operational",
            )
        ]

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        self.detail_call_count += 1
        self.detail_place_ids.append(provider_place_id)
        return PlaceDetails(
            provider="google",
            provider_place_id=provider_place_id,
            rating=4.6,
            user_rating_count=321,
            open_now=True,
            opening_hours=("Monday: 9:00 AM – 9:00 PM",),
            phone_number="(416) 555-0100",
            website_uri="https://example.com/",
        )


class FailingPlaceProvider:
    provider_name = "google"

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> Sequence[Place]:
        raise PlaceProviderError("private provider details")

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        raise PlaceProviderError("private provider details")


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
    assert "function clearResults()" in response.text
    assert "if (places.length === 0)" in response.text
    assert 'places.length === 0 ? "No places found."' in response.text
    assert "response.status === 422" in response.text
    assert "Search is temporarily unavailable. Please try again." in response.text
    assert "function formatDistance(" in response.text
    assert "Operational status unconfirmed" in response.text
    assert 'fetch("/api/places/details"' in response.text
    assert 'button.textContent = "View details"' in response.text
    assert "const detailsByPlace = new Map()" in response.text
    assert 'detailsByPlace.clear()' in response.text
    assert '"Call to confirm"' in response.text
    assert '"Call"' in response.text
    assert "function websiteHref(" in response.text
    assert 'url.protocol !== "http:" && url.protocol !== "https:"' in response.text
    assert "function directionsHref(" in response.text
    assert 'new URL("https://www.google.com/maps/dir/")' in response.text
    assert 'url.searchParams.set("api", "1")' in response.text
    assert 'url.searchParams.set("destination_place_id"' in response.text
    assert 'directionsLink.textContent = "Get directions"' in response.text
    assert 'websiteLink.target = "_blank"' in response.text
    assert 'websiteLink.rel = "noopener noreferrer"' in response.text
    assert 'websiteLink.textContent = "Visit website"' in response.text
    assert 'showNumberButton.textContent = "Show number"' in response.text
    assert 'showNumberButton.textContent = "Hide number"' in response.text
    assert 'phoneNumber.hidden = true' in response.text
    assert 'phoneNumber.hidden = !phoneNumber.hidden' in response.text
    assert 'showNumberButton.setAttribute("aria-expanded"' in response.text
    assert "function closedBusinessStatus(" not in response.text
    assert '"Category unavailable"' in response.text
    assert '"Address unavailable"' in response.text


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
    assert provider.detail_call_count == 0


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
            "business_status": "operational",
            "distance_meters": 14,
        }
    ]


def test_search_returns_safe_provider_error(client: TestClient) -> None:
    app.dependency_overrides[get_place_provider] = lambda: FailingPlaceProvider()

    response = client.post(
        "/api/places/search",
        json={
            "location": {
                "label": "Union Station coordinates",
                "latitude": 43.6453,
                "longitude": -79.3806,
            },
            "radius_meters": 1_000,
        },
    )

    assert response.status_code == 502
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"detail": "Place search is temporarily unavailable"}
    assert "private provider details" not in response.text


def test_explicit_detail_request_calls_provider_once_and_returns_details(
    client: TestClient,
) -> None:
    provider = RecordingPlaceProvider()
    app.dependency_overrides[get_place_provider] = lambda: provider

    response = client.post(
        "/api/places/details",
        json={"provider": "google", "provider_place_id": "google-place-1"},
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert provider.call_count == 0
    assert provider.detail_call_count == 1
    assert provider.detail_place_ids == ["google-place-1"]
    assert response.json() == {
        "provider": "google",
        "provider_place_id": "google-place-1",
        "rating": 4.6,
        "user_rating_count": 321,
        "open_now": True,
        "opening_hours": ["Monday: 9:00 AM – 9:00 PM"],
        "phone_number": "(416) 555-0100",
        "website_uri": "https://example.com/",
    }


def test_detail_request_rejects_an_unsupported_provider_without_a_call(
    client: TestClient,
) -> None:
    provider = RecordingPlaceProvider()
    app.dependency_overrides[get_place_provider] = lambda: provider

    response = client.post(
        "/api/places/details",
        json={"provider": "another-provider", "provider_place_id": "place-1"},
    )

    assert response.status_code == 422
    assert provider.detail_call_count == 0


def test_detail_request_returns_safe_provider_error(client: TestClient) -> None:
    app.dependency_overrides[get_place_provider] = lambda: FailingPlaceProvider()

    response = client.post(
        "/api/places/details",
        json={"provider": "google", "provider_place_id": "google-place-1"},
    )

    assert response.status_code == 502
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == {"detail": "Place details are temporarily unavailable"}
    assert "private provider details" not in response.text


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
