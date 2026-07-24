import json
from datetime import datetime

import httpx
import pytest

from app.adapters.google_places import GooglePlacesGateway
from app.domain.place import Coordinates, OpeningPeriod, Place, PlaceDetails
from app.domain.search import (
    CommonFood,
    Cuisine,
    MinimumRating,
    PlaceType,
    SearchFilters,
    SearchSort,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
    DescriptiveRequirementKind,
)
from app.ports.place_provider import PlaceProviderError


@pytest.mark.anyio
async def test_text_search_makes_one_server_side_google_request() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        body = json.loads(request.content)
        assert request.method == "POST"
        assert str(request.url) == "https://places.googleapis.com/v1/places:searchText"
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == (
            "places.id,places.displayName,places.primaryType,places.types,"
            "places.primaryTypeDisplayName,places.formattedAddress,places.location,"
            "places.businessStatus,places.currentOpeningHours,places.rating"
        )
        assert "test-api-key" not in str(request.url)
        assert "test-api-key" not in request.content.decode()

        restriction = body.pop("locationRestriction")
        assert body == {
            "textQuery": "bars or bakeries with Italian cuisine",
            "pageSize": 20,
            "openNow": True,
            "minRating": 4.0,
            "rankPreference": "DISTANCE",
        }
        rectangle = restriction["rectangle"]
        assert rectangle["low"]["latitude"] == pytest.approx(43.6363, abs=0.0001)
        assert rectangle["high"]["latitude"] == pytest.approx(43.6543, abs=0.0001)
        assert rectangle["low"]["longitude"] == pytest.approx(-79.3930, abs=0.0001)
        assert rectangle["high"]["longitude"] == pytest.approx(-79.3682, abs=0.0001)

        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "google-place-1",
                        "displayName": {"text": "Example Bar"},
                        "primaryType": "bar",
                        "types": ["bar", "food", "establishment"],
                        "primaryTypeDisplayName": {"text": "Bar"},
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
            name="Example Bar",
            category="Bar",
            category_code="bar",
            address="1 Front Street, Toronto, ON",
            coordinates=Coordinates(latitude=43.6454, longitude=-79.3805),
            business_status="temporarily_closed",
            open_now=True,
            rating=4.6,
            distance_meters=None,
        )
    ]


@pytest.mark.anyio
async def test_text_search_combines_cuisine_and_common_food_in_query() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["textQuery"] == (
            "restaurants with Persian cuisine serving kebab or ramen"
        )
        assert body["includedType"] == "restaurant"
        assert body["strictTypeFiltering"] is True
        assert "includedPrimaryTypes" not in body
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
                cuisines=(Cuisine.PERSIAN,),
                common_foods=(CommonFood.KEBAB, CommonFood.RAMEN),
            ),
            sort=SearchSort.PROVIDER_DEFAULT,
        )

    assert places == []


@pytest.mark.anyio
async def test_text_search_adds_reviewed_text_and_maps_current_opening_periods() -> None:
    window = AvailabilityWindow(
        starts_at=datetime.fromisoformat("2026-07-23T18:00:00-04:00"),
        ends_at=datetime.fromisoformat("2026-07-24T00:00:00-04:00"),
    )

    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["textQuery"] == (
            "restaurants with Persian cuisine quiet atmosphere"
        )
        assert request.headers["X-Goog-FieldMask"] == (
            "places.id,places.displayName,places.primaryType,places.types,"
            "places.primaryTypeDisplayName,places.formattedAddress,places.location,"
            "places.businessStatus,places.currentOpeningHours,places.timeZone"
        )
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "google-place-1",
                        "displayName": {"text": "Quiet Restaurant"},
                        "primaryType": "restaurant",
                        "types": ["restaurant", "food"],
                        "location": {
                            "latitude": 43.6454,
                            "longitude": -79.3805,
                        },
                        "currentOpeningHours": {
                            "periods": [
                                {
                                    "open": {
                                        "date": {
                                            "year": 2026,
                                            "month": 7,
                                            "day": 23,
                                        },
                                        "hour": 17,
                                        "minute": 0,
                                    },
                                    "close": {
                                        "date": {
                                            "year": 2026,
                                            "month": 7,
                                            "day": 23,
                                        },
                                        "hour": 23,
                                        "minute": 0,
                                    },
                                }
                            ]
                        },
                        "timeZone": {"id": "America/Toronto"},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        gateway = GooglePlacesGateway(
            api_key="test-api-key",
            http_client=http_client,
        )
        places = await gateway.search_nearby(
            latitude=43.6453,
            longitude=-79.3806,
            radius_meters=1000,
            filters=SearchFilters(
                place_types=(PlaceType.RESTAURANT,),
                cuisines=(Cuisine.PERSIAN,),
            ),
            sort=SearchSort.PROVIDER_DEFAULT,
            descriptive_requirements=(
                DescriptiveRequirement(
                    text="quiet atmosphere",
                    kind=DescriptiveRequirementKind.ATMOSPHERE,
                ),
            ),
            availability_window=window,
        )

    assert places[0].opening_periods == (
        OpeningPeriod(
            starts_at=datetime.fromisoformat("2026-07-23T17:00:00-04:00"),
            ends_at=datetime.fromisoformat("2026-07-23T23:00:00-04:00"),
        ),
    )


@pytest.mark.anyio
async def test_text_search_preserves_missing_optional_place_fields() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["X-Goog-FieldMask"] == (
            "places.id,places.displayName,places.primaryType,places.types,"
            "places.primaryTypeDisplayName,places.formattedAddress,places.location,"
            "places.businessStatus"
        )
        assert body["textQuery"] == "restaurants"
        assert body["includedType"] == "restaurant"
        assert body["strictTypeFiltering"] is True
        assert "rankPreference" not in body
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "google-place-2",
                        "displayName": {"text": "Unnamed Category Restaurant"},
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
            name="Unnamed Category Restaurant",
            category=None,
            category_code=None,
            address=None,
            coordinates=Coordinates(latitude=43.65, longitude=-79.38),
            business_status=None,
            distance_meters=None,
        )
    ]


@pytest.mark.anyio
async def test_text_search_removes_known_nonselected_place_types() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "restaurant",
                        "displayName": {"text": "Restaurant"},
                        "types": ["restaurant", "food"],
                        "location": {"latitude": 43.65, "longitude": -79.38},
                    },
                    {
                        "id": "store",
                        "displayName": {"text": "Store"},
                        "types": ["store", "establishment"],
                        "location": {"latitude": 43.65, "longitude": -79.38},
                    },
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
                place_types=(PlaceType.RESTAURANT, PlaceType.CAFE),
            ),
            sort=SearchSort.PROVIDER_DEFAULT,
        )

    assert [place.provider_place_id for place in places] == ["restaurant"]


@pytest.mark.anyio
async def test_rating_sort_requests_rating_without_opening_hours() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        field_mask = request.headers["X-Goog-FieldMask"]
        assert field_mask.endswith("places.businessStatus,places.rating")
        assert "currentOpeningHours" not in field_mask
        body = json.loads(request.content)
        assert "rankPreference" not in body
        assert "minRating" not in body
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
async def test_text_search_conditionally_requests_and_maps_service_fields() -> None:
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
async def test_text_search_translates_google_error_response() -> None:
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
