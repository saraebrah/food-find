from pydantic import BaseModel, ConfigDict, Field

from app.domain.location import SelectedLocation
from app.domain.place import Coordinates
from app.domain.search import SearchCriteria


class SelectedLocationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    label: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    provider: str | None = Field(default=None, max_length=50)
    provider_place_id: str | None = Field(default=None, max_length=500)

    def to_domain(self) -> SelectedLocation:
        return SelectedLocation(
            label=self.label,
            coordinates=Coordinates(
                latitude=self.latitude,
                longitude=self.longitude,
            ),
            provider=self.provider,
            provider_place_id=self.provider_place_id,
        )


class SearchPlacesRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    location: SelectedLocationRequest
    radius_meters: float = Field(ge=100, le=50_000)

    def to_domain(self) -> SearchCriteria:
        return SearchCriteria(
            location=self.location.to_domain(),
            radius_meters=self.radius_meters,
        )
