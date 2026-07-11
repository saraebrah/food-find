import json

import httpx
import pytest

from app.adapters.google_places import GooglePlacesGateway
from app.domain.place import Coordinates, Place


@pytest.mark.anyio
async def test_search_nearby_makes_one_server_side_google_request() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        body = json.loads(request.content)
        assert request.method == "POST"
        assert str(request.url) == "https://places.googleapis.com/v1/places:searchNearby"
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == (
            "places.id,places.displayName,places.primaryType,"
            "places.primaryTypeDisplayName,places.formattedAddress,places.location"
        )
        assert "test-api-key" not in str(request.url)
        assert "test-api-key" not in request.content.decode()
        assert body == {
            "includedTypes": ["restaurant", "cafe"],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": 43.6453, "longitude": -79.3806},
                    "radius": 1000.0,
                }
            },
        }

        return httpx.Response(
            200,
            json={
                "places": [
                    {
                        "id": "google-place-1",
                        "displayName": {"text": "Example Restaurant"},
                        "primaryType": "restaurant",
                        "primaryTypeDisplayName": {"text": "Restaurant"},
                        "formattedAddress": "1 Front Street, Toronto, ON",
                        "location": {"latitude": 43.6454, "longitude": -79.3805},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        places = await gateway.search_nearby(
            latitude=43.6453,
            longitude=-79.3806,
            radius_meters=1000,
            included_types=("restaurant", "cafe"),
        )

    assert request_count == 1
    assert places == [
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


@pytest.mark.anyio
async def test_search_nearby_preserves_missing_optional_place_fields() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "google-place-2",
                        "displayName": {"text": "Unnamed Category Cafe"},
                        "location": {"latitude": 43.65, "longitude": -79.38},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        places = await gateway.search_nearby(
            latitude=43.6453,
            longitude=-79.3806,
            radius_meters=1000,
            included_types=("restaurant",),
        )

    assert places == [
        Place(
            provider="google",
            provider_place_id="google-place-2",
            name="Unnamed Category Cafe",
            category=None,
            category_code=None,
            address=None,
            coordinates=Coordinates(latitude=43.65, longitude=-79.38),
        )
    ]


@pytest.mark.anyio
async def test_search_nearby_raises_for_google_error_response() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request, json={"error": {"message": "quota"}})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        with pytest.raises(httpx.HTTPStatusError):
            await gateway.search_nearby(
                latitude=43.6453,
                longitude=-79.3806,
                radius_meters=1000,
                included_types=("restaurant",),
            )
