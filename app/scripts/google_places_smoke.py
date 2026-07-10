import asyncio

import httpx

from app.adapters.google_places import GooglePlacesGateway
from app.settings import Settings


TORONTO_CITY_HALL_LATITUDE = 43.6532
TORONTO_CITY_HALL_LONGITUDE = -79.3832
SMOKE_TEST_RADIUS_METERS = 1_000
SMOKE_TEST_TYPES = ("restaurant", "cafe")


async def run() -> None:
    settings = Settings()

    async with httpx.AsyncClient(timeout=10) as http_client:
        gateway = GooglePlacesGateway(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )
        response = await gateway.search_nearby(
            latitude=TORONTO_CITY_HALL_LATITUDE,
            longitude=TORONTO_CITY_HALL_LONGITUDE,
            radius_meters=SMOKE_TEST_RADIUS_METERS,
            included_types=SMOKE_TEST_TYPES,
        )

    print(f"Google Places smoke test succeeded: {len(response.places)} places returned.")
    for place in response.places[:3]:
        print(f"- {place.display_name.text}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
