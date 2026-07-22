from math import asin, cos, degrees, pi, radians, sin
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.domain.place import Coordinates, Place, PlaceDetails
from app.domain.search import (
    EARTH_RADIUS_METERS,
    CommonFood,
    Cuisine,
    PlaceType,
    SearchFilters,
    SearchSort,
)
from app.ports.place_provider import PlaceProvider, PlaceProviderError


GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.primaryType",
        "places.types",
        "places.primaryTypeDisplayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
    )
)
GOOGLE_CURRENT_OPENING_HOURS_FIELD = "places.currentOpeningHours"
GOOGLE_RATING_FIELD = "places.rating"
GOOGLE_DINE_IN_FIELD = "places.dineIn"
GOOGLE_TAKEOUT_FIELD = "places.takeout"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
GOOGLE_DETAILS_FIELD_MASK = ",".join(
    (
        "id",
        "rating",
        "userRatingCount",
        "currentOpeningHours",
        "regularOpeningHours",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "websiteUri",
    )
)


class GoogleLocalizedText(BaseModel):
    text: str


class GoogleLocation(BaseModel):
    latitude: float
    longitude: float


class GoogleOpeningHours(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    open_now: bool | None = Field(default=None, alias="openNow")
    weekday_descriptions: list[str] = Field(
        default_factory=list,
        alias="weekdayDescriptions",
    )


class GooglePlaceRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    display_name: GoogleLocalizedText = Field(alias="displayName")
    primary_type: str | None = Field(default=None, alias="primaryType")
    types: list[str] = Field(default_factory=list)
    primary_type_display_name: GoogleLocalizedText | None = Field(
        default=None, alias="primaryTypeDisplayName"
    )
    formatted_address: str | None = Field(default=None, alias="formattedAddress")
    location: GoogleLocation
    business_status: str | None = Field(default=None, alias="businessStatus")
    current_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="currentOpeningHours",
    )
    rating: float | None = None
    dine_in: bool | None = Field(default=None, alias="dineIn")
    takeout: bool | None = None


class GoogleTextSearchResponse(BaseModel):
    places: list[GooglePlaceRecord] = Field(default_factory=list)


class GooglePlaceDetailsRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    rating: float | None = None
    user_rating_count: int | None = Field(default=None, alias="userRatingCount")
    current_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="currentOpeningHours",
    )
    regular_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="regularOpeningHours",
    )
    national_phone_number: str | None = Field(
        default=None,
        alias="nationalPhoneNumber",
    )
    international_phone_number: str | None = Field(
        default=None,
        alias="internationalPhoneNumber",
    )
    website_uri: str | None = Field(default=None, alias="websiteUri")


GOOGLE_BUSINESS_STATUSES = {
    "OPERATIONAL": "operational",
    "CLOSED_TEMPORARILY": "temporarily_closed",
    "CLOSED_PERMANENTLY": "permanently_closed",
}
GOOGLE_PLACE_TYPES = {
    PlaceType.RESTAURANT: "restaurant",
    PlaceType.CAFE: "cafe",
    PlaceType.BAR: "bar",
    PlaceType.BAKERY: "bakery",
}
GOOGLE_PLACE_TYPE_QUERY_TEXT = {
    PlaceType.RESTAURANT: "restaurants",
    PlaceType.CAFE: "cafes",
    PlaceType.BAR: "bars",
    PlaceType.BAKERY: "bakeries",
}
GOOGLE_CUISINE_QUERY_TEXT = {
    Cuisine.CHINESE: "Chinese",
    Cuisine.ITALIAN: "Italian",
    Cuisine.PERSIAN: "Persian",
    Cuisine.THAI: "Thai",
    Cuisine.INDIAN: "Indian",
}
GOOGLE_COMMON_FOOD_QUERY_TEXT = {
    CommonFood.PIZZA: "pizza",
    CommonFood.BURGER: "burgers",
    CommonFood.STEAK: "steak",
    CommonFood.RAMEN: "ramen",
    CommonFood.KEBAB: "kebab",
}


class GooglePlacesGateway(PlaceProvider):
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ValueError("Google Places API key must not be empty")

        self._api_key = api_key
        self._http_client = http_client

    @property
    def provider_name(self) -> str:
        return "google"

    @staticmethod
    def _search_field_mask(*, filters: SearchFilters, sort: SearchSort) -> str:
        conditional_fields: list[str] = []
        if filters.open_now:
            conditional_fields.append(GOOGLE_CURRENT_OPENING_HOURS_FIELD)
        if filters.minimum_rating is not None or sort is SearchSort.RATING:
            conditional_fields.append(GOOGLE_RATING_FIELD)
        if filters.dine_in:
            conditional_fields.append(GOOGLE_DINE_IN_FIELD)
        if filters.takeout:
            conditional_fields.append(GOOGLE_TAKEOUT_FIELD)
        return ",".join((GOOGLE_FIELD_MASK, *conditional_fields))

    @staticmethod
    def _build_text_query(*, filters: SearchFilters) -> str:
        place_types = " or ".join(
            GOOGLE_PLACE_TYPE_QUERY_TEXT[place_type]
            for place_type in filters.place_types
        )
        parts = [place_types]
        if filters.cuisines:
            cuisines = " or ".join(
                GOOGLE_CUISINE_QUERY_TEXT[cuisine]
                for cuisine in filters.cuisines
            )
            parts.append(f"with {cuisines} cuisine")
        if filters.common_foods:
            foods = " or ".join(
                GOOGLE_COMMON_FOOD_QUERY_TEXT[food]
                for food in filters.common_foods
            )
            parts.append(f"serving {foods}")
        return " ".join(parts)

    @staticmethod
    def _location_parameter(
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
    ) -> dict[str, object]:
        angular_radius = radius_meters / EARTH_RADIUS_METERS
        latitude_radians = radians(latitude)
        longitude_radians = radians(longitude)
        minimum_latitude = max(-pi / 2, latitude_radians - angular_radius)
        maximum_latitude = min(pi / 2, latitude_radians + angular_radius)

        if minimum_latitude <= -pi / 2 or maximum_latitude >= pi / 2:
            return {
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": float(radius_meters),
                    }
                }
            }

        longitude_delta = asin(
            min(1.0, sin(angular_radius) / cos(latitude_radians))
        )
        minimum_longitude = longitude_radians - longitude_delta
        maximum_longitude = longitude_radians + longitude_delta
        if minimum_longitude < -pi or maximum_longitude > pi:
            return {
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": float(radius_meters),
                    }
                }
            }

        return {
            "locationRestriction": {
                "rectangle": {
                    "low": {
                        "latitude": degrees(minimum_latitude),
                        "longitude": degrees(minimum_longitude),
                    },
                    "high": {
                        "latitude": degrees(maximum_latitude),
                        "longitude": degrees(maximum_longitude),
                    },
                }
            }
        }

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
    ) -> list[Place]:
        if not filters.place_types:
            raise ValueError("At least one place type is required")
        if not 0 < radius_meters <= 50_000:
            raise ValueError("Radius must be greater than zero and at most 50,000 metres")

        request_body: dict[str, object] = {
            "textQuery": self._build_text_query(filters=filters),
            "pageSize": 20,
            **self._location_parameter(
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
            ),
        }
        if len(filters.place_types) == 1:
            request_body["includedType"] = GOOGLE_PLACE_TYPES[
                filters.place_types[0]
            ]
            request_body["strictTypeFiltering"] = True
        if filters.open_now:
            request_body["openNow"] = True
        if filters.minimum_rating is not None:
            request_body["minRating"] = filters.minimum_rating.value
        if sort is SearchSort.DISTANCE:
            request_body["rankPreference"] = "DISTANCE"

        selected_google_types = frozenset(
            GOOGLE_PLACE_TYPES[place_type] for place_type in filters.place_types
        )

        try:
            response = await self._http_client.post(
                GOOGLE_TEXT_SEARCH_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": self._search_field_mask(
                        filters=filters,
                        sort=sort,
                    ),
                },
                json=request_body,
            )
            response.raise_for_status()
            google_response = GoogleTextSearchResponse.model_validate(
                response.json()
            )
        except (httpx.HTTPError, ValueError) as error:
            raise PlaceProviderError("Google Places search failed") from error

        return [
            self._to_place(place)
            for place in google_response.places
            if not place.types or selected_google_types.intersection(place.types)
        ]

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        if not provider_place_id.strip():
            raise ValueError("Google place ID must not be empty")

        place_id = quote(provider_place_id, safe="")
        try:
            response = await self._http_client.get(
                GOOGLE_PLACE_DETAILS_URL.format(place_id=place_id),
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": GOOGLE_DETAILS_FIELD_MASK,
                },
            )
            response.raise_for_status()
            google_details = GooglePlaceDetailsRecord.model_validate(response.json())
            if google_details.id != provider_place_id:
                raise ValueError("Google Places returned a different place ID")
        except (httpx.HTTPError, ValueError) as error:
            raise PlaceProviderError("Google Place Details request failed") from error

        current_hours = google_details.current_opening_hours
        regular_hours = google_details.regular_opening_hours
        opening_hours = (
            current_hours.weekday_descriptions
            if current_hours and current_hours.weekday_descriptions
            else regular_hours.weekday_descriptions
            if regular_hours
            else []
        )
        open_now = (
            current_hours.open_now
            if current_hours and current_hours.open_now is not None
            else regular_hours.open_now
            if regular_hours
            else None
        )

        return PlaceDetails(
            provider=self.provider_name,
            provider_place_id=google_details.id,
            rating=google_details.rating,
            user_rating_count=google_details.user_rating_count,
            open_now=open_now,
            opening_hours=tuple(opening_hours),
            phone_number=(
                google_details.national_phone_number
                or google_details.international_phone_number
            ),
            website_uri=google_details.website_uri,
        )

    @staticmethod
    def _to_place(place: GooglePlaceRecord) -> Place:
        return Place(
            provider="google",
            provider_place_id=place.id,
            name=place.display_name.text,
            category=(
                place.primary_type_display_name.text
                if place.primary_type_display_name
                else None
            ),
            category_code=place.primary_type,
            address=place.formatted_address,
            coordinates=Coordinates(
                latitude=place.location.latitude,
                longitude=place.location.longitude,
            ),
            business_status=GOOGLE_BUSINESS_STATUSES.get(place.business_status),
            open_now=(
                place.current_opening_hours.open_now
                if place.current_opening_hours
                else None
            ),
            rating=place.rating,
            dine_in=place.dine_in,
            takeout=place.takeout,
        )
