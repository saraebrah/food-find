from app.domain.place import PlaceDetails
from app.ports.place_provider import PlaceProvider


class UnsupportedPlaceProviderError(ValueError):
    """A place reference does not belong to the configured provider."""


class GetPlaceDetails:
    def __init__(self, *, place_provider: PlaceProvider) -> None:
        self._place_provider = place_provider

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

        return await self._place_provider.get_details(
            provider_place_id=provider_place_id
        )
