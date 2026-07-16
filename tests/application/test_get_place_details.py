import pytest

from app.application.get_place_details import (
    GetPlaceDetails,
    UnsupportedPlaceProviderError,
)
from app.domain.place import PlaceDetails


class RecordingDetailsProvider:
    provider_name = "google"

    def __init__(self) -> None:
        self.requested_place_ids: list[str] = []

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        self.requested_place_ids.append(provider_place_id)
        return PlaceDetails(
            provider="google",
            provider_place_id=provider_place_id,
            rating=4.5,
            user_rating_count=10,
            open_now=False,
            opening_hours=("Monday: 9:00 AM – 5:00 PM",),
            phone_number="(416) 555-0100",
            website_uri="https://example.com/",
        )


@pytest.mark.anyio
async def test_get_place_details_uses_the_matching_provider() -> None:
    provider = RecordingDetailsProvider()
    use_case = GetPlaceDetails(place_provider=provider)

    details = await use_case.execute(
        provider="google",
        provider_place_id="google-place-1",
    )

    assert provider.requested_place_ids == ["google-place-1"]
    assert details.provider_place_id == "google-place-1"


@pytest.mark.anyio
async def test_get_place_details_rejects_a_different_provider_without_a_call() -> None:
    provider = RecordingDetailsProvider()
    use_case = GetPlaceDetails(place_provider=provider)

    with pytest.raises(UnsupportedPlaceProviderError):
        await use_case.execute(
            provider="another-provider",
            provider_place_id="other-place-1",
        )

    assert provider.requested_place_ids == []
