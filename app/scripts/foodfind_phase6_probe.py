"""One opt-in Google evidence probe for FoodFind Phase 6 Step 1.

This is a development utility, not part of production search. It makes one
fixed Text Search request and does not persist the Google response.
"""

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


PROBE_QUERY = "creme brulee"
REMAINING_PROBE_QUERIES = (
    "chocolate cake",
    "truffle pizza",
    "sushi taco",
    "crispy sushi taco",
)
PROBE_LATITUDE = 43.6519
PROBE_LONGITUDE = -79.3642
PROBE_RADIUS_METERS = 2_000
CRISPY_SUSHI_TACO_RADIUS_METERS = 5_000
REMAINING_PROBE_CASES = (
    ("chocolate cake", PROBE_RADIUS_METERS),
    ("truffle pizza", PROBE_RADIUS_METERS),
    ("sushi taco", PROBE_RADIUS_METERS),
    ("crispy sushi taco", CRISPY_SUSHI_TACO_RADIUS_METERS),
)
PROBE_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.googleMapsUri",
        "places.primaryType",
        "places.types",
        "places.reviews",
        "contextualContents",
    )
)


class ProbeConfirmationRequired(ValueError):
    """Raised before any request when explicit live-call consent is absent."""


def require_live_confirmation(*, confirmed: bool) -> None:
    if not confirmed:
        raise ProbeConfirmationRequired(
            "Live Google request not confirmed. Re-run with "
            "--confirm-live-google-request."
        )


async def request_probe(
    *,
    api_key: str,
    http_client: httpx.AsyncClient,
    query: str = PROBE_QUERY,
    radius_meters: int = PROBE_RADIUS_METERS,
) -> dict[str, Any]:
    """Make exactly one fixed Google Text Search evidence request."""

    request_body: dict[str, object] = {
        "textQuery": query,
        "pageSize": 20,
        "languageCode": "en",
        "regionCode": "CA",
        **GooglePlacesGateway._location_parameter(
            latitude=PROBE_LATITUDE,
            longitude=PROBE_LONGITUDE,
            radius_meters=radius_meters,
        ),
    }
    response = await http_client.post(
        GOOGLE_TEXT_SEARCH_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": PROBE_FIELD_MASK,
        },
        json=request_body,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Google Places returned an unexpected response")
    return payload


async def request_remaining_probes(
    *,
    api_key: str,
    http_client: httpx.AsyncClient,
) -> list[tuple[str, dict[str, Any]]]:
    """Make one request for each remaining fixed evaluation query."""

    responses: list[tuple[str, dict[str, Any]]] = []
    for query, radius_meters in REMAINING_PROBE_CASES:
        payload = await request_probe(
            api_key=api_key,
            http_client=http_client,
            query=query,
            radius_meters=radius_meters,
        )
        responses.append((query, payload))
    return responses


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: object) -> str:
    if isinstance(value, str):
        return value
    mapping = _mapping(value)
    text = mapping.get("text")
    return text if isinstance(text, str) else ""


def _shorten(value: str, *, limit: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}…"


def _render_review(review_value: object, *, label: str) -> list[str]:
    review = _mapping(review_value)
    author = _mapping(review.get("authorAttribution"))
    author_name = author.get("displayName") or "Unknown author"
    author_uri = author.get("uri") or "Unavailable"
    author_photo_uri = author.get("photoUri") or "Unavailable"
    source_uri = review.get("googleMapsUri") or "Unavailable"
    review_text = _shorten(_text(review.get("text"))) or "No review text returned"
    return [
        f"  {label}: {review_text}",
        f"    Author: {author_name}",
        f"    Author profile: {author_uri}",
        f"    Author avatar: {author_photo_uri}",
        f"    Source review: {source_uri}",
    ]


def _review_justifications(
    context: Mapping[str, Any],
) -> list[tuple[str, Mapping[str, Any]]]:
    justifications: list[tuple[str, Mapping[str, Any]]] = []
    for justification_value in _list(context.get("justifications")):
        justification = _mapping(justification_value)
        review_justification = _mapping(justification.get("reviewJustification"))
        highlighted = _mapping(review_justification.get("highlightedText"))
        text = _shorten(_text(highlighted))
        review = _mapping(review_justification.get("review"))
        if text or review:
            justifications.append((text, review))
    return justifications


def render_probe_response(
    payload: Mapping[str, Any],
    *,
    query: str = PROBE_QUERY,
) -> str:
    """Render a reviewable report without writing Google content to disk."""

    places = _list(payload.get("places"))
    contexts = _list(payload.get("contextualContents"))
    lines = [
        "FoodFind Phase 6 Step 1 — Google evidence probe",
        f"Query: {query}",
        "Location: 318 King St E, Toronto",
        f"Radius: {PROBE_RADIUS_METERS // 1_000} km",
        f"Places returned: {len(places)}",
        f"Contextual entries returned: {len(contexts)}",
        "",
        "Review ordering: Google selects review content by relevance. "
        "Contextual content prefers evidence related to the text query.",
        "Provider attribution: Google Maps",
    ]

    for index, place_value in enumerate(places):
        place = _mapping(place_value)
        context = _mapping(contexts[index]) if index < len(contexts) else {}
        name = _text(place.get("displayName")) or "Unnamed place"
        address = place.get("formattedAddress") or "Address unavailable"
        maps_uri = place.get("googleMapsUri") or "Unavailable"
        standard_reviews = _list(place.get("reviews"))
        contextual_reviews = _list(context.get("reviews"))

        lines.extend(
            (
                "",
                f"{index + 1}. {name}",
                f"  Address: {address}",
                f"  Google Maps: {maps_uri}",
                f"  Standard reviews returned: {len(standard_reviews)}",
                f"  Contextual reviews returned: {len(contextual_reviews)}",
            )
        )
        for evidence, review in _review_justifications(context):
            if evidence:
                lines.append(f"  Highlighted evidence: {evidence}")
            if review:
                lines.extend(
                    _render_review(review, label="Justification review")
                )
        for review in contextual_reviews[:2]:
            lines.extend(_render_review(review, label="Contextual review"))
        for review in standard_reviews[:2]:
            lines.extend(_render_review(review, label="Standard review"))

    lines.extend(
        (
            "",
            "Raw Google response was not saved.",
            "This probe changes no production search behavior.",
        )
    )
    return "\n".join(lines)


def render_probe_summary(
    *,
    query: str,
    payload: Mapping[str, Any],
    radius_meters: int = PROBE_RADIUS_METERS,
) -> str:
    """Render only place names and query-related highlights for comparison."""

    places = _list(payload.get("places"))
    contexts = _list(payload.get("contextualContents"))
    lines = [
        f"Query: {query}",
        f"Radius: {radius_meters // 1_000} km",
        f"Places returned: {len(places)}",
        f"Contextual entries returned: {len(contexts)}",
    ]
    for index, place_value in enumerate(places):
        place = _mapping(place_value)
        context = _mapping(contexts[index]) if index < len(contexts) else {}
        name = _text(place.get("displayName")) or "Unnamed place"
        address = place.get("formattedAddress") or "Address unavailable"
        highlights = [
            evidence
            for evidence, _review in _review_justifications(context)
            if evidence
        ]
        evidence_text = " | ".join(highlights) if highlights else "None"
        lines.extend(
            (
                f"{index + 1}. {name}",
                f"   Address: {address}",
                f"   Query-related highlight: {evidence_text}",
            )
        )
    return "\n".join(lines)


async def run_live_probe() -> None:
    settings = Settings()
    async with httpx.AsyncClient(timeout=20) as http_client:
        payload = await request_probe(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )
    print(render_probe_response(payload))


async def run_live_remaining_probes() -> None:
    settings = Settings()
    async with httpx.AsyncClient(timeout=20) as http_client:
        responses = await request_remaining_probes(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )
    for index, ((query, radius_meters), (_, payload)) in enumerate(
        zip(REMAINING_PROBE_CASES, responses, strict=True)
    ):
        if index:
            print()
        print(
            render_probe_summary(
                query=query,
                payload=payload,
                radius_meters=radius_meters,
            )
        )
    print()
    print("Raw Google responses were not saved.")
    print("These probes changed no production search behavior.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the single FoodFind Phase 6 Google evidence probe."
    )
    confirmation = parser.add_mutually_exclusive_group()
    confirmation.add_argument(
        "--confirm-live-google-request",
        action="store_true",
        help="Confirm one billable Google Text Search request.",
    )
    confirmation.add_argument(
        "--confirm-remaining-example-requests",
        action="store_true",
        help="Confirm four billable searches for the remaining examples.",
    )
    arguments = parser.parse_args()
    confirmed = (
        arguments.confirm_live_google_request
        or arguments.confirm_remaining_example_requests
    )
    require_live_confirmation(confirmed=confirmed)
    if arguments.confirm_remaining_example_requests:
        asyncio.run(run_live_remaining_probes())
    else:
        asyncio.run(run_live_probe())


if __name__ == "__main__":
    main()
