from collections.abc import Sequence
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.domain.place import Coordinates, Place, PlaceDetails
from app.ports.place_provider import PlaceProvider, PlaceProviderError


GOOGLE_NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.primaryType",
        "places.primaryTypeDisplayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
    )
)
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


class GooglePlaceRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    display_name: GoogleLocalizedText = Field(alias="displayName")
    primary_type: str | None = Field(default=None, alias="primaryType")
    primary_type_display_name: GoogleLocalizedText | None = Field(
        default=None, alias="primaryTypeDisplayName"
    )
    formatted_address: str | None = Field(default=None, alias="formattedAddress")
    location: GoogleLocation
    business_status: str | None = Field(default=None, alias="businessStatus")


class GoogleNearbySearchResponse(BaseModel):
    places: list[GooglePlaceRecord] = Field(default_factory=list)


class GoogleOpeningHours(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    open_now: bool | None = Field(default=None, alias="openNow")
    weekday_descriptions: list[str] = Field(
        default_factory=list,
        alias="weekdayDescriptions",
    )


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


class GooglePlacesGateway(PlaceProvider):
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ValueError("Google Places API key must not be empty")

        self._api_key = api_key
        self._http_client = http_client

    @property
    def provider_name(self) -> str:
        return "google"

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> list[Place]:
        if not included_types:
            raise ValueError("At least one place type is required")
        if not 0 < radius_meters <= 50_000:
            raise ValueError("Radius must be greater than zero and at most 50,000 metres")

        try:
            response = await self._http_client.post(
                GOOGLE_NEARBY_SEARCH_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": GOOGLE_FIELD_MASK,
                },
                json={
                    "includedTypes": list(included_types),
                    "maxResultCount": 20,
                    "locationRestriction": {
                        "circle": {
                            "center": {
                                "latitude": latitude,
                                "longitude": longitude,
                            },
                            "radius": float(radius_meters),
                        }
                    },
                },
            )
            response.raise_for_status()
            google_response = GoogleNearbySearchResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as error:
            raise PlaceProviderError("Google Places search failed") from error

        return [self._to_place(place) for place in google_response.places]

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
        )
