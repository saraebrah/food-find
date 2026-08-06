from typing import Protocol


class MenuLinkResolverError(RuntimeError):
    """A restaurant website could not be inspected for a menu link."""


class MenuLinkResolver(Protocol):
    async def resolve_menu_uri(self, *, website_uri: str) -> str | None: ...
