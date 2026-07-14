from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.domain.location import LocationSuggestion, SelectedLocation
from app.domain.place import Coordinates
from app.ports.location_provider import LocationProvider


GOOGLE_AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
GOOGLE_AUTOCOMPLETE_FIELD_MASK = ",".join(
    (
        "suggestions.placePrediction.placeId",
        "suggestions.placePrediction.text.text",
    )
)
GOOGLE_PLACE_DETAILS_FIELD_MASK = "id,location"
TORONTO_BIAS_CENTER = Coordinates(latitude=43.6532, longitude=-79.3832)
TORONTO_BIAS_RADIUS_METERS = 50_000


class GooglePredictionText(BaseModel):
    text: str


class GooglePlacePrediction(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_id: str = Field(alias="placeId")
    text: GooglePredictionText


class GoogleAutocompleteSuggestion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    place_prediction: GooglePlacePrediction | None = Field(
        default=None,
        alias="placePrediction",
    )


class GoogleAutocompleteResponse(BaseModel):
    suggestions: list[GoogleAutocompleteSuggestion] = Field(default_factory=list)


class GoogleLocation(BaseModel):
    latitude: float
    longitude: float


class GooglePlaceDetailsResponse(BaseModel):
    id: str
    location: GoogleLocation


class GoogleLocationGateway(LocationProvider):
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ValueError("Google Places API key must not be empty")

        self._api_key = api_key
        self._http_client = http_client

    async def suggest(
        self,
        *,
        query: str,
        session_token: str,
    ) -> list[LocationSuggestion]:
        normalized_query = query.strip()
        if len(normalized_query) < 3:
            raise ValueError("Autocomplete query must contain at least three characters")
        if not session_token.strip():
            raise ValueError("Autocomplete session token must not be empty")

        response = await self._http_client.post(
            GOOGLE_AUTOCOMPLETE_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self._api_key,
                "X-Goog-FieldMask": GOOGLE_AUTOCOMPLETE_FIELD_MASK,
            },
            json={
                "input": normalized_query,
                "languageCode": "en",
                "regionCode": "ca",
                "sessionToken": session_token,
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": TORONTO_BIAS_CENTER.latitude,
                            "longitude": TORONTO_BIAS_CENTER.longitude,
                        },
                        "radius": float(TORONTO_BIAS_RADIUS_METERS),
                    }
                },
            },
        )
        response.raise_for_status()

        google_response = GoogleAutocompleteResponse.model_validate(response.json())
        return [
            LocationSuggestion(
                provider="google",
                provider_place_id=suggestion.place_prediction.place_id,
                label=suggestion.place_prediction.text.text,
            )
            for suggestion in google_response.suggestions
            if suggestion.place_prediction is not None
        ]

    async def resolve(
        self,
        *,
        suggestion: LocationSuggestion,
        session_token: str,
    ) -> SelectedLocation:
        if suggestion.provider != "google":
            raise ValueError("Google location gateway can only resolve Google suggestions")
        if not session_token.strip():
            raise ValueError("Autocomplete session token must not be empty")

        place_id = quote(suggestion.provider_place_id, safe="")
        response = await self._http_client.get(
            f"https://places.googleapis.com/v1/places/{place_id}",
            params={"sessionToken": session_token},
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self._api_key,
                "X-Goog-FieldMask": GOOGLE_PLACE_DETAILS_FIELD_MASK,
            },
        )
        response.raise_for_status()

        details = GooglePlaceDetailsResponse.model_validate(response.json())
        if details.id != suggestion.provider_place_id:
            raise ValueError("Google returned details for an unexpected place ID")

        return SelectedLocation(
            label=suggestion.label,
            coordinates=Coordinates(
                latitude=details.location.latitude,
                longitude=details.location.longitude,
            ),
            provider="google",
            provider_place_id=details.id,
        )
