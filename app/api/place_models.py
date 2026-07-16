from pydantic import BaseModel, ConfigDict, Field


class PlaceDetailsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: str = Field(min_length=1, max_length=50)
    provider_place_id: str = Field(min_length=1, max_length=500)
