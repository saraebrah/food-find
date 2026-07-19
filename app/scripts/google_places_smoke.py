import asyncio

import httpx

from app.adapters.google_places import GooglePlacesGateway
from app.domain.search import SearchFilters, SearchSort
from app.settings import Settings


TORONTO_CITY_HALL_LATITUDE = 43.6532
TORONTO_CITY_HALL_LONGITUDE = -79.3832
SMOKE_TEST_RADIUS_METERS = 1_000


async def run() -> None:
    settings = Settings()

    async with httpx.AsyncClient(timeout=10) as http_client:
        gateway = GooglePlacesGateway(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )
        places = await gateway.search_nearby(
            latitude=TORONTO_CITY_HALL_LATITUDE,
            longitude=TORONTO_CITY_HALL_LONGITUDE,
            radius_meters=SMOKE_TEST_RADIUS_METERS,
            filters=SearchFilters(),
            sort=SearchSort.PROVIDER_DEFAULT,
        )

    print(f"Google Places smoke test succeeded: {len(places)} places returned.")
    for place in places[:3]:
        print(f"- {place.name}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
