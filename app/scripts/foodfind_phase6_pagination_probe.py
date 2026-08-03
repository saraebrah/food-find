"""One opt-in, historical Pro-only pagination probe for FoodFind."""

import argparse
import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from app.adapters.google_places import (
    GOOGLE_TEXT_SEARCH_URL,
    GooglePlacesGateway,
)
from app.settings import Settings


PAGINATION_QUERY = "chocolate cake"
PAGINATION_LATITUDE = 43.6519
PAGINATION_LONGITUDE = -79.3642
PAGINATION_RADIUS_METERS = 2_000
MAX_PAGES = 3
PAGINATION_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "nextPageToken",
    )
)


class PaginationProbeConfirmationRequired(ValueError):
    """Raised before any request when live-call consent is absent."""


def require_live_confirmation(*, confirmed: bool) -> None:
    if not confirmed:
        raise PaginationProbeConfirmationRequired(
            "Live Google pagination requests not confirmed. Re-run with "
            "--confirm-live-google-pagination-requests."
        )


def _request_body(*, page_token: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "textQuery": PAGINATION_QUERY,
        "pageSize": 20,
        "languageCode": "en",
        "regionCode": "CA",
        **GooglePlacesGateway._location_parameter(
            latitude=PAGINATION_LATITUDE,
            longitude=PAGINATION_LONGITUDE,
            radius_meters=PAGINATION_RADIUS_METERS,
        ),
    }
    if page_token is not None:
        body["pageToken"] = page_token
    return body


async def request_page(
    *,
    api_key: str,
    http_client: httpx.AsyncClient,
    page_token: str | None = None,
) -> dict[str, Any]:
    response = await http_client.post(
        GOOGLE_TEXT_SEARCH_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": PAGINATION_FIELD_MASK,
        },
        json=_request_body(page_token=page_token),
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Google Places returned an unexpected response")
    return payload


async def request_all_pages(
    *,
    api_key: str,
    http_client: httpx.AsyncClient,
) -> list[dict[str, Any]]:
    """Request no more than Google's three Text Search result pages."""

    pages: list[dict[str, Any]] = []
    page_token: str | None = None
    seen_tokens: set[str] = set()

    for _ in range(MAX_PAGES):
        page = await request_page(
            api_key=api_key,
            http_client=http_client,
            page_token=page_token,
        )
        pages.append(page)
        next_token = page.get("nextPageToken")
        if not isinstance(next_token, str) or not next_token.strip():
            break
        if next_token in seen_tokens:
            break
        seen_tokens.add(next_token)
        page_token = next_token

    return pages


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _display_name(place: Mapping[str, Any]) -> str:
    display_name = _mapping(place.get("displayName"))
    text = display_name.get("text")
    return text if isinstance(text, str) and text else "Unnamed place"


def render_pages(pages: list[dict[str, Any]]) -> str:
    lines = [
        "FoodFind historical Pro pagination probe",
        f"Query: {PAGINATION_QUERY}",
        "Location: 318 King St E, Toronto",
        f"Radius: {PAGINATION_RADIUS_METERS // 1_000} km",
        f"Pages returned: {len(pages)}",
    ]
    for page_index, page in enumerate(pages):
        places = _list(page.get("places"))
        lines.extend(("", f"Page {page_index + 1} ({len(places)} places)"))
        for place_index, place_value in enumerate(places):
            place = _mapping(place_value)
            result_number = page_index * 20 + place_index + 1
            address = place.get("formattedAddress") or "Address unavailable"
            lines.append(f"{result_number}. {_display_name(place)}")
            lines.append(f"   Address: {address}")
    lines.extend(
        (
            "",
            "Raw Google responses were not saved.",
            "This probe changed no production search behavior.",
        )
    )
    return "\n".join(lines)


async def run_live_probe() -> None:
    settings = Settings()
    async with httpx.AsyncClient(timeout=20) as http_client:
        pages = await request_all_pages(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )
    print(render_pages(pages))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the fixed FoodFind chocolate-cake pagination probe."
    )
    parser.add_argument(
        "--confirm-live-google-pagination-requests",
        action="store_true",
        help="Confirm up to three billable Google Text Search Pro requests.",
    )
    arguments = parser.parse_args()
    require_live_confirmation(
        confirmed=arguments.confirm_live_google_pagination_requests
    )
    asyncio.run(run_live_probe())


if __name__ == "__main__":
    main()
