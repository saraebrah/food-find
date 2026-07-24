from pydantic import BaseModel, ConfigDict, Field

from app.domain.place import (
    BusinessStatus,
    Coordinates,
    MatchReasonKind,
    Place,
)


class MatchReasonResponse(BaseModel):
    kind: MatchReasonKind
    text: str


class PlaceResponse(BaseModel):
    provider: str
    provider_place_id: str
    name: str
    category: str | None
    category_code: str | None
    address: str | None
    coordinates: Coordinates
    business_status: BusinessStatus | None
    open_now: bool | None
    rating: float | None
    dine_in: bool | None
    takeout: bool | None
    distance_meters: int | None
    match_reasons: list[MatchReasonResponse]

    @classmethod
    def from_domain(cls, place: Place) -> "PlaceResponse":
        return cls(
            provider=place.provider,
            provider_place_id=place.provider_place_id,
            name=place.name,
            category=place.category,
            category_code=place.category_code,
            address=place.address,
            coordinates=place.coordinates,
            business_status=place.business_status,
            open_now=place.open_now,
            rating=place.rating,
            dine_in=place.dine_in,
            takeout=place.takeout,
            distance_meters=place.distance_meters,
            match_reasons=[
                MatchReasonResponse(kind=reason.kind, text=reason.text)
                for reason in place.match_reasons
            ],
        )


class PlaceDetailsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=50)
    provider_place_id: str = Field(min_length=1, max_length=500)
