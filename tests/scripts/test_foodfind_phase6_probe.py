import json

import httpx
import pytest

from app.scripts.foodfind_phase6_probe import (
    PROBE_FIELD_MASK,
    REMAINING_PROBE_QUERIES,
    ProbeConfirmationRequired,
    render_probe_summary,
    render_probe_response,
    request_probe,
    request_remaining_probes,
    require_live_confirmation,
)


def test_live_probe_requires_explicit_confirmation() -> None:
    with pytest.raises(
        ProbeConfirmationRequired,
        match="--confirm-live-google-request",
    ):
        require_live_confirmation(confirmed=False)

    require_live_confirmation(confirmed=True)


@pytest.mark.anyio
async def test_probe_makes_one_evidence_search_and_keeps_key_server_side() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        body = json.loads(request.content)
        assert request.method == "POST"
        assert str(request.url) == (
            "https://places.googleapis.com/v1/places:searchText"
        )
        assert request.headers["X-Goog-Api-Key"] == "test-api-key"
        assert request.headers["X-Goog-FieldMask"] == PROBE_FIELD_MASK
        assert "test-api-key" not in str(request.url)
        assert "test-api-key" not in request.content.decode()
        assert body["textQuery"] == "creme brulee"
        assert body["pageSize"] == 20
        assert body["languageCode"] == "en"
        assert body["regionCode"] == "CA"
        assert set(body) == {
            "textQuery",
            "pageSize",
            "languageCode",
            "regionCode",
            "locationRestriction",
        }

        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": "place-1",
                        "displayName": {"text": "Muse Bistro + Bar"},
                        "formattedAddress": "203 Jarvis St, Toronto, ON",
                        "googleMapsUri": "https://maps.google.com/place-1",
                        "primaryType": "restaurant",
                        "types": ["restaurant", "food"],
                        "reviews": [
                            {
                                "text": {"text": "The creme brulee was excellent."},
                                "authorAttribution": {
                                    "displayName": "Example Reviewer",
                                    "uri": "https://maps.google.com/reviewer",
                                    "photoUri": "https://example.com/avatar.jpg",
                                },
                                "googleMapsUri": "https://maps.google.com/review-1",
                            }
                        ],
                    }
                ],
                "contextualContents": [
                    {
                        "reviews": [
                            {
                                "text": {"text": "Try the creme brulee."},
                                "authorAttribution": {
                                    "displayName": "Context Reviewer",
                                    "uri": "https://maps.google.com/context-reviewer",
                                },
                                "googleMapsUri": "https://maps.google.com/review-2",
                            }
                        ],
                        "justifications": [
                            {
                                "reviewJustification": {
                                    "highlightedText": {
                                        "text": "creme brulee",
                                    },
                                    "review": {
                                        "text": {
                                            "text": "The creme brulee was worth ordering."
                                        },
                                        "authorAttribution": {
                                            "displayName": "Evidence Reviewer",
                                            "uri": "https://maps.google.com/evidence-reviewer",
                                        },
                                        "googleMapsUri": (
                                            "https://maps.google.com/review-evidence"
                                        ),
                                    },
                                }
                            }
                        ],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        response = await request_probe(
            api_key="test-api-key",
            http_client=http_client,
        )

    assert request_count == 1
    assert response["places"][0]["id"] == "place-1"


@pytest.mark.anyio
async def test_remaining_examples_make_exactly_four_fixed_requests() -> None:
    received_queries: list[str] = []
    longitude_widths: list[float] = []

    async def handle_request(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        received_queries.append(body["textQuery"])
        rectangle = body["locationRestriction"]["rectangle"]
        longitude_widths.append(
            rectangle["high"]["longitude"] - rectangle["low"]["longitude"]
        )
        assert body["pageSize"] == 20
        assert "pageToken" not in body
        return httpx.Response(
            200,
            request=request,
            json={
                "places": [
                    {
                        "id": f"place-{len(received_queries)}",
                        "displayName": {"text": "Example"},
                    }
                ],
                "contextualContents": [{}],
            },
        )

    transport = httpx.MockTransport(handle_request)
    async with httpx.AsyncClient(transport=transport) as http_client:
        responses = await request_remaining_probes(
            api_key="test-api-key",
            http_client=http_client,
        )

    assert tuple(received_queries) == REMAINING_PROBE_QUERIES
    assert [query for query, _ in responses] == list(REMAINING_PROBE_QUERIES)
    assert len(responses) == 4
    assert longitude_widths[:3] == pytest.approx(
        [longitude_widths[0]] * 3
    )
    assert longitude_widths[3] > longitude_widths[0] * 2


def test_probe_report_keeps_context_aligned_with_its_place() -> None:
    report = render_probe_response(
        {
            "places": [
                {
                    "id": "place-1",
                    "displayName": {"text": "Muse Bistro + Bar"},
                    "formattedAddress": "203 Jarvis St, Toronto, ON",
                    "googleMapsUri": "https://maps.google.com/place-1",
                    "reviews": [
                        {
                            "text": {"text": "The creme brulee was excellent."},
                            "authorAttribution": {
                                "displayName": "Example Reviewer",
                                "uri": "https://maps.google.com/reviewer",
                                "photoUri": "https://example.com/avatar.jpg",
                            },
                            "googleMapsUri": "https://maps.google.com/review-1",
                        }
                    ],
                }
            ],
            "contextualContents": [
                {
                    "reviews": [
                        {
                            "text": {"text": "Try the creme brulee."},
                            "authorAttribution": {
                                "displayName": "Context Reviewer",
                                "uri": "https://maps.google.com/context-reviewer",
                            },
                            "googleMapsUri": "https://maps.google.com/review-2",
                        }
                    ],
                    "justifications": [
                        {
                            "reviewJustification": {
                                "highlightedText": {"text": "creme brulee"},
                                "review": {
                                    "text": {
                                        "text": "The creme brulee was worth ordering."
                                    },
                                    "authorAttribution": {
                                        "displayName": "Evidence Reviewer",
                                        "uri": (
                                            "https://maps.google.com/evidence-reviewer"
                                        ),
                                    },
                                    "googleMapsUri": (
                                        "https://maps.google.com/review-evidence"
                                    ),
                                },
                            }
                        }
                    ],
                }
            ],
        }
    )

    assert "Places returned: 1" in report
    assert "Contextual entries returned: 1" in report
    assert "Muse Bistro + Bar" in report
    assert "Try the creme brulee." in report
    assert "Context Reviewer" in report
    assert "https://maps.google.com/review-2" in report
    assert "The creme brulee was excellent." in report
    assert "Example Reviewer" in report
    assert "Highlighted evidence: creme brulee" in report
    assert "Justification review: The creme brulee was worth ordering." in report
    assert "Evidence Reviewer" in report
    assert "https://maps.google.com/review-evidence" in report
    assert "Raw Google response was not saved." in report


def test_probe_summary_lists_names_and_query_related_highlights_only() -> None:
    summary = render_probe_summary(
        query="truffle pizza",
        payload={
            "places": [
                {
                    "displayName": {"text": "Pi Co."},
                    "formattedAddress": "60 Colborne St, Toronto, ON",
                    "reviews": [{"text": {"text": "A long standard review."}}],
                }
            ],
            "contextualContents": [
                {
                    "justifications": [
                        {
                            "reviewJustification": {
                                "highlightedText": {
                                    "text": "pizza flavoured with truffle"
                                }
                            }
                        }
                    ]
                }
            ],
        },
    )

    assert "Query: truffle pizza" in summary
    assert "Pi Co." in summary
    assert "pizza flavoured with truffle" in summary
    assert "A long standard review." not in summary
