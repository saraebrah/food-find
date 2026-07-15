import json

import httpx
import pytest

from app.adapters.google_locations import GoogleLocationGateway
from app.domain.location import LocationSuggestion, SelectedLocation
from app.domain.place import Coordinates
from app.ports.location_provider import LocationProviderError


SESSION_TOKEN = "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.anyio
async def test_suggest_makes_one_server_side_autocomplete_request() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        assert request.method == "POST"
        assert str(request.url) == "https://places.googleapis.com/v1/places:autocomplete"
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == (
            "suggestions.placePrediction.placeId,"
            "suggestions.placePrediction.text.text"
        )
        assert "test-api-key" not in request.content.decode()
        assert json.loads(request.content) == {
            "input": "Union Station",
            "languageCode": "en",
            "regionCode": "ca",
            "sessionToken": SESSION_TOKEN,
            "locationBias": {
                "circle": {
                    "center": {"latitude": 43.6532, "longitude": -79.3832},
                    "radius": 50_000.0,
                }
            },
        }

        return httpx.Response(
            200,
            json={
                "suggestions": [
                    {
                        "placePrediction": {
                            "placeId": "google-location-1",
                            "text": {
                                "text": "Union Station, Front Street West, Toronto, ON, Canada"
                            },
                        }
                    },
                    {"queryPrediction": {"text": {"text": "Union Station food"}}},
                ]
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GoogleLocationGateway(
            api_key="test-api-key",
            http_client=http_client,
        )

        suggestions = await gateway.suggest(
            query="Union Station",
            session_token=SESSION_TOKEN,
        )

    assert request_count == 1
    assert suggestions == [
        LocationSuggestion(
            provider="google",
            provider_place_id="google-location-1",
            label="Union Station, Front Street West, Toronto, ON, Canada",
        )
    ]


@pytest.mark.anyio
async def test_resolve_uses_place_details_and_returns_selected_location() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/places/google-location-1"
        assert request.url.params["sessionToken"] == SESSION_TOKEN
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == "id,location"
        assert "test-api-key" not in str(request.url)

        return httpx.Response(
            200,
            json={
                "id": "google-location-1",
                "location": {"latitude": 43.6453, "longitude": -79.3806},
            },
        )

    suggestion = LocationSuggestion(
        provider="google",
        provider_place_id="google-location-1",
        label="Union Station, Front Street West, Toronto, ON, Canada",
    )
    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GoogleLocationGateway(
            api_key="test-api-key",
            http_client=http_client,
        )

        location = await gateway.resolve(
            suggestion=suggestion,
            session_token=SESSION_TOKEN,
        )

    assert location == SelectedLocation(
        label="Union Station, Front Street West, Toronto, ON, Canada",
        coordinates=Coordinates(latitude=43.6453, longitude=-79.3806),
        provider="google",
        provider_place_id="google-location-1",
    )


@pytest.mark.anyio
async def test_suggest_translates_google_error_response() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request, json={"error": {"message": "quota"}})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GoogleLocationGateway(
            api_key="test-api-key",
            http_client=http_client,
        )

        with pytest.raises(LocationProviderError):
            await gateway.suggest(query="Union Station", session_token=SESSION_TOKEN)
