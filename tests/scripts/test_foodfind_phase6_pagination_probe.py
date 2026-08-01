import json

import httpx
import pytest

from app.scripts.foodfind_phase6_pagination_probe import (
    PAGINATION_FIELD_MASK,
    PaginationProbeConfirmationRequired,
    render_pages,
    request_all_pages,
    require_live_confirmation,
)


def test_pagination_probe_requires_explicit_confirmation() -> None:
    with pytest.raises(
        PaginationProbeConfirmationRequired,
        match="--confirm-live-google-pagination-requests",
    ):
        require_live_confirmation(confirmed=False)

    require_live_confirmation(confirmed=True)


@pytest.mark.anyio
async def test_probe_requests_at_most_three_pro_pages_with_page_tokens() -> None:
    request_bodies: list[dict[str, object]] = []

    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        request_bodies.append(body)
        page_number = len(request_bodies)

        assert request.method == "POST"
        assert str(request.url) == (
            "https://places.googleapis.com/v1/places:searchText"
        )
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == PAGINATION_FIELD_MASK
        assert "reviews" not in PAGINATION_FIELD_MASK
        assert "contextualContents" not in PAGINATION_FIELD_MASK
        assert "test-api-key" not in str(request.url)
        assert "test-api-key" not in request.content.decode()

        payload: dict[str, object] = {
            "places": [
                {
                    "id": f"place-{page_number}",
                    "displayName": {"text": f"Page {page_number} Place"},
                    "formattedAddress": f"{page_number} King St, Toronto",
                }
            ]
        }
        if page_number < 3:
            payload["nextPageToken"] = f"page-{page_number + 1}-token"
        return httpx.Response(200, request=request, json=payload)

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        pages = await request_all_pages(
            api_key="test-api-key",
            http_client=http_client,
        )

    assert len(pages) == 3
    assert [body.get("pageToken") for body in request_bodies] == [
        None,
        "page-2-token",
        "page-3-token",
    ]
    for body in request_bodies:
        assert body["textQuery"] == "chocolate cake"
        assert body["pageSize"] == 20
        assert body["languageCode"] == "en"
        assert body["regionCode"] == "CA"
        assert "locationRestriction" in body


@pytest.mark.anyio
async def test_probe_stops_when_google_returns_no_next_page_token() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, request=request, json={"places": []})

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        pages = await request_all_pages(
            api_key="test-api-key",
            http_client=http_client,
        )

    assert request_count == 1
    assert len(pages) == 1


def test_report_preserves_page_boundaries_without_saving_raw_data() -> None:
    report = render_pages(
        [
            {
                "places": [
                    {
                        "displayName": {"text": "First Place"},
                        "formattedAddress": "1 King St, Toronto",
                    }
                ],
                "nextPageToken": "not-rendered",
            },
            {
                "places": [
                    {
                        "displayName": {"text": "CRAFT Beer Market Toronto"},
                        "formattedAddress": "1 Adelaide St E, Toronto",
                    }
                ]
            },
        ]
    )

    assert "Page 1" in report
    assert "1. First Place" in report
    assert "Page 2" in report
    assert "21. CRAFT Beer Market Toronto" in report
    assert "not-rendered" not in report
    assert "Raw Google responses were not saved." in report
