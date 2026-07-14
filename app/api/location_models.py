from pydantic import BaseModel, ConfigDict, Field, UUID4

from app.domain.location import LocationSuggestion, SelectedLocation


class AutocompleteLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=3, max_length=200)
    session_token: UUID4


class ResolveLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider_place_id: str = Field(min_length=1, max_length=500)
    label: str = Field(min_length=1, max_length=500)
    session_token: UUID4

    def to_suggestion(self) -> LocationSuggestion:
        return LocationSuggestion(
            provider="google",
            provider_place_id=self.provider_place_id,
            label=self.label,
        )


class LocationSuggestionResponse(BaseModel):
    provider: str
    provider_place_id: str
    label: str

    @classmethod
    def from_domain(
        cls,
        suggestion: LocationSuggestion,
    ) -> "LocationSuggestionResponse":
        return cls(
            provider=suggestion.provider,
            provider_place_id=suggestion.provider_place_id,
            label=suggestion.label,
        )


class SelectedLocationResponse(BaseModel):
    label: str
    latitude: float
    longitude: float
    provider: str | None
    provider_place_id: str | None

    @classmethod
    def from_domain(cls, location: SelectedLocation) -> "SelectedLocationResponse":
        return cls(
            label=location.label,
            latitude=location.coordinates.latitude,
            longitude=location.coordinates.longitude,
            provider=location.provider,
            provider_place_id=location.provider_place_id,
        )
