from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field


GOOGLE_NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.primaryType",
        "places.primaryTypeDisplayName",
        "places.formattedAddress",
        "places.location",
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


class GoogleNearbySearchResponse(BaseModel):
    places: list[GooglePlaceRecord] = Field(default_factory=list)


class GooglePlacesGateway:
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ValueError("Google Places API key must not be empty")

        self._api_key = api_key
        self._http_client = http_client

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        included_types: Sequence[str],
    ) -> GoogleNearbySearchResponse:
        if not included_types:
            raise ValueError("At least one place type is required")
        if not 0 < radius_meters <= 50_000:
            raise ValueError("Radius must be greater than zero and at most 50,000 metres")

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

        return GoogleNearbySearchResponse.model_validate(response.json())
