import asyncio

import pytest

from app.application.get_place_details import (
    GetPlaceDetails,
    UnsupportedPlaceProviderError,
)
from app.domain.place import PlaceDetails
from app.ports.menu_link_resolver import MenuLinkResolverError


class RecordingDetailsProvider:
    provider_name = "google"

    def __init__(self, *, website_uri: str | None = "https://example.com/") -> None:
        self.website_uri = website_uri
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
            website_uri=self.website_uri,
        )


class RecordingMenuLinkResolver:
    def __init__(self, *, menu_uri: str | None = "https://example.com/menu") -> None:
        self.menu_uri = menu_uri
        self.website_uris: list[str] = []

    async def resolve_menu_uri(self, *, website_uri: str) -> str | None:
        self.website_uris.append(website_uri)
        return self.menu_uri


class FailingMenuLinkResolver:
    async def resolve_menu_uri(self, *, website_uri: str) -> str | None:
        raise MenuLinkResolverError("private website failure")


class SlowMenuLinkResolver:
    async def resolve_menu_uri(self, *, website_uri: str) -> str | None:
        await asyncio.Event().wait()
        return None


@pytest.mark.anyio
async def test_get_place_details_uses_the_matching_provider() -> None:
    provider = RecordingDetailsProvider()
    menu_link_resolver = RecordingMenuLinkResolver()
    use_case = GetPlaceDetails(
        place_provider=provider,
        menu_link_resolver=menu_link_resolver,
    )

    details = await use_case.execute(
        provider="google",
        provider_place_id="google-place-1",
    )

    assert provider.requested_place_ids == ["google-place-1"]
    assert menu_link_resolver.website_uris == ["https://example.com/"]
    assert details.provider_place_id == "google-place-1"
    assert details.menu_uri == "https://example.com/menu"


@pytest.mark.anyio
async def test_get_place_details_rejects_a_different_provider_without_a_call() -> None:
    provider = RecordingDetailsProvider()
    menu_link_resolver = RecordingMenuLinkResolver()
    use_case = GetPlaceDetails(
        place_provider=provider,
        menu_link_resolver=menu_link_resolver,
    )

    with pytest.raises(UnsupportedPlaceProviderError):
        await use_case.execute(
            provider="another-provider",
            provider_place_id="other-place-1",
        )

    assert provider.requested_place_ids == []
    assert menu_link_resolver.website_uris == []


@pytest.mark.anyio
async def test_get_place_details_keeps_details_when_menu_discovery_fails() -> None:
    provider = RecordingDetailsProvider()
    use_case = GetPlaceDetails(
        place_provider=provider,
        menu_link_resolver=FailingMenuLinkResolver(),
    )

    details = await use_case.execute(
        provider="google",
        provider_place_id="google-place-1",
    )

    assert details.website_uri == "https://example.com/"
    assert details.menu_uri is None


@pytest.mark.anyio
async def test_get_place_details_skips_discovery_without_a_website() -> None:
    provider = RecordingDetailsProvider(website_uri=None)
    menu_link_resolver = RecordingMenuLinkResolver()
    use_case = GetPlaceDetails(
        place_provider=provider,
        menu_link_resolver=menu_link_resolver,
    )

    details = await use_case.execute(
        provider="google",
        provider_place_id="google-place-1",
    )

    assert details.website_uri is None
    assert details.menu_uri is None
    assert menu_link_resolver.website_uris == []


@pytest.mark.anyio
async def test_get_place_details_keeps_details_when_menu_discovery_times_out() -> None:
    use_case = GetPlaceDetails(
        place_provider=RecordingDetailsProvider(),
        menu_link_resolver=SlowMenuLinkResolver(),
        menu_discovery_timeout_seconds=0.01,
    )

    details = await use_case.execute(
        provider="google",
        provider_place_id="google-place-1",
    )

    assert details.website_uri == "https://example.com/"
    assert details.menu_uri is None
