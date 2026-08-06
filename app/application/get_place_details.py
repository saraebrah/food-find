import asyncio
from dataclasses import replace

from app.domain.place import PlaceDetails
from app.ports.menu_link_resolver import MenuLinkResolver, MenuLinkResolverError
from app.ports.place_provider import PlaceProvider


class UnsupportedPlaceProviderError(ValueError):
    """A place reference does not belong to the configured provider."""


class GetPlaceDetails:
    def __init__(
        self,
        *,
        place_provider: PlaceProvider,
        menu_link_resolver: MenuLinkResolver,
        menu_discovery_timeout_seconds: float = 4,
    ) -> None:
        self._place_provider = place_provider
        self._menu_link_resolver = menu_link_resolver
        self._menu_discovery_timeout_seconds = menu_discovery_timeout_seconds

    async def execute(
        self,
        *,
        provider: str,
        provider_place_id: str,
    ) -> PlaceDetails:
        if provider != self._place_provider.provider_name:
            raise UnsupportedPlaceProviderError(
                f"Unsupported place provider: {provider}"
            )

        details = await self._place_provider.get_details(
            provider_place_id=provider_place_id
        )
        if details.website_uri is None:
            return details

        try:
            menu_uri = await asyncio.wait_for(
                self._menu_link_resolver.resolve_menu_uri(
                    website_uri=details.website_uri
                ),
                timeout=self._menu_discovery_timeout_seconds,
            )
        except (MenuLinkResolverError, asyncio.TimeoutError):
            menu_uri = None

        return replace(details, menu_uri=menu_uri)
