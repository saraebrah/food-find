import json

import httpx
import pytest

from app.adapters.google_places import GooglePlacesGateway
from app.domain.place import Coordinates, Place, PlaceDetails
from app.domain.search import (
    CommonFood,
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchFilters,
    SearchSort,
)
from app.ports.place_provider import PlaceProviderError


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
            "places.primaryTypeDisplayName,places.formattedAddress,places.location,"
            "places.businessStatus,places.currentOpeningHours,places.rating"
        )
        assert "test-api-key" not in str(request.url)
        assert "test-api-key" not in request.content.decode()
        assert body == {
            "includedTypes": ["bar", "bakery"],
            "includedPrimaryTypes": ["italian_restaurant"],
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
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
                        "businessStatus": "CLOSED_TEMPORARILY",
                        "currentOpeningHours": {"openNow": True},
                        "rating": 4.6,
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
            filters=SearchFilters(
                place_types=(PlaceType.BAR, PlaceType.BAKERY),
                cuisines=(Cuisine.ITALIAN,),
                open_now=True,
                minimum_rating=MinimumRating.FOUR,
            ),
            sort=SearchSort.DISTANCE,
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
            business_status="temporarily_closed",
            open_now=True,
            rating=4.6,
            distance_meters=None,
        )
    ]


@pytest.mark.anyio
async def test_search_nearby_preserves_missing_optional_place_fields() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["X-Goog-FieldMask"] == (
            "places.id,places.displayName,places.primaryType,"
            "places.primaryTypeDisplayName,places.formattedAddress,places.location,"
            "places.businessStatus"
        )
        assert "includedPrimaryTypes" not in body
        assert "rankPreference" not in body
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
            filters=SearchFilters(place_types=(PlaceType.RESTAURANT,)),
            sort=SearchSort.PROVIDER_DEFAULT,
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
            business_status=None,
            distance_meters=None,
        )
    ]


@pytest.mark.anyio
async def test_search_nearby_maps_common_food_categories() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["includedPrimaryTypes"] == [
            "pizza_restaurant",
            "ramen_restaurant",
        ]
        return httpx.Response(200, request=request, json={"places": []})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        places = await gateway.search_nearby(
            latitude=43.6453,
            longitude=-79.3806,
            radius_meters=1000,
            filters=SearchFilters(
                place_types=(PlaceType.RESTAURANT,),
                common_foods=(CommonFood.PIZZA, CommonFood.RAMEN),
            ),
            sort=SearchSort.PROVIDER_DEFAULT,
        )

    assert places == []


@pytest.mark.anyio
async def test_rating_sort_requests_rating_without_opening_hours() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        field_mask = request.headers["X-Goog-FieldMask"]
        assert field_mask.endswith("places.businessStatus,places.rating")
        assert "currentOpeningHours" not in field_mask
        assert "rankPreference" not in json.loads(request.content)
        return httpx.Response(200, request=request, json={"places": []})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)
        places = await gateway.search_nearby(
            latitude=43.6453,
            longitude=-79.3806,
            radius_meters=1000,
            filters=SearchFilters(),
            sort=SearchSort.RATING,
        )

    assert places == []


@pytest.mark.anyio
async def test_search_nearby_conditionally_requests_and_maps_service_fields() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        field_mask = request.headers["X-Goog-FieldMask"]
        assert field_mask.endswith("places.businessStatus,places.dineIn,places.takeout")
        assert "currentOpeningHours" not in field_mask
        assert "places.rating" not in field_mask
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "google-place-1",
                        "displayName": {"text": "Example Restaurant"},
                        "location": {"latitude": 43.65, "longitude": -79.38},
                        "dineIn": True,
                        "takeout": False,
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
            filters=SearchFilters(dine_in=True, takeout=True),
            sort=SearchSort.PROVIDER_DEFAULT,
        )

    assert places[0].dine_in is True
    assert places[0].takeout is False


@pytest.mark.parametrize(
    ("filters", "included_field", "excluded_field"),
    (
        (SearchFilters(dine_in=True), "places.dineIn", "places.takeout"),
        (SearchFilters(takeout=True), "places.takeout", "places.dineIn"),
    ),
)
def test_search_field_mask_adds_only_the_selected_service_field(
    filters: SearchFilters,
    included_field: str,
    excluded_field: str,
) -> None:
    field_mask = GooglePlacesGateway._search_field_mask(
        filters=filters,
        sort=SearchSort.PROVIDER_DEFAULT,
    )

    assert included_field in field_mask.split(",")
    assert excluded_field not in field_mask.split(",")


@pytest.mark.anyio
async def test_search_nearby_translates_google_error_response() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request, json={"error": {"message": "quota"}})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        with pytest.raises(PlaceProviderError):
            await gateway.search_nearby(
                latitude=43.6453,
                longitude=-79.3806,
                radius_meters=1000,
                filters=SearchFilters(place_types=(PlaceType.RESTAURANT,)),
                sort=SearchSort.PROVIDER_DEFAULT,
            )


@pytest.mark.anyio
async def test_get_details_requests_only_the_selected_place_enterprise_fields() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        assert request.method == "GET"
        assert str(request.url) == (
            "https://places.googleapis.com/v1/places/google-place-1"
        )
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == (
            "id,rating,userRatingCount,currentOpeningHours,regularOpeningHours,"
            "nationalPhoneNumber,internationalPhoneNumber,websiteUri"
        )
        assert "test-api-key" not in str(request.url)

        return httpx.Response(
            200,
            request=request,
            json={
                "id": "google-place-1",
                "rating": 4.6,
                "userRatingCount": 321,
                "currentOpeningHours": {
                    "openNow": True,
                    "weekdayDescriptions": [
                        "Monday: 9:00 AM – 9:00 PM",
                        "Tuesday: 9:00 AM – 9:00 PM",
                    ],
                },
                "regularOpeningHours": {
                    "weekdayDescriptions": ["Regular hours should be fallback only"]
                },
                "nationalPhoneNumber": "(416) 555-0100",
                "internationalPhoneNumber": "+1 416-555-0100",
                "websiteUri": "https://example.com/",
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        details = await gateway.get_details(provider_place_id="google-place-1")

    assert request_count == 1
    assert details == PlaceDetails(
        provider="google",
        provider_place_id="google-place-1",
        rating=4.6,
        user_rating_count=321,
        open_now=True,
        opening_hours=(
            "Monday: 9:00 AM – 9:00 PM",
            "Tuesday: 9:00 AM – 9:00 PM",
        ),
        phone_number="(416) 555-0100",
        website_uri="https://example.com/",
    )


@pytest.mark.anyio
async def test_get_details_preserves_missing_optional_fields() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "id": "google-place-2",
                "regularOpeningHours": {
                    "weekdayDescriptions": ["Monday: Closed"]
                },
                "internationalPhoneNumber": "+1 416-555-0101",
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        details = await gateway.get_details(provider_place_id="google-place-2")

    assert details == PlaceDetails(
        provider="google",
        provider_place_id="google-place-2",
        rating=None,
        user_rating_count=None,
        open_now=None,
        opening_hours=("Monday: Closed",),
        phone_number="+1 416-555-0101",
        website_uri=None,
    )


@pytest.mark.anyio
async def test_get_details_translates_google_error_response() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request, json={"error": {"message": "quota"}})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(api_key="test-api-key", http_client=http_client)

        with pytest.raises(PlaceProviderError):
            await gateway.get_details(provider_place_id="google-place-1")
