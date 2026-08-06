import httpx
import pytest

from app.adapters.website_menu_links import WebsiteMenuLinkResolver
from app.ports.menu_link_resolver import MenuLinkResolverError


async def public_host(_: str) -> tuple[str, ...]:
    return ("93.184.216.34",)


@pytest.mark.anyio
async def test_finds_and_resolves_an_explicit_menu_link_from_the_homepage() -> None:
    requested_urls: list[str] = []

    async def handle_request(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                request=request,
                text="User-agent: *\nAllow: /\n",
            )
        return httpx.Response(
            200,
            request=request,
            headers={"Content-Type": "text/html; charset=utf-8"},
            text='''
                <html><body>
                  <a href="/about">About us</a>
                  <a href="/food/menu.pdf#today">View our menu</a>
                </body></html>
            ''',
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=public_host,
        )

        menu_uri = await resolver.resolve_menu_uri(
            website_uri="https://restaurant.example/"
        )

    assert menu_uri == "https://restaurant.example/food/menu.pdf"
    assert requested_urls == [
        "https://restaurant.example/robots.txt",
        "https://restaurant.example/",
    ]


@pytest.mark.anyio
async def test_respects_a_robots_rule_that_disallows_the_homepage() -> None:
    requested_paths: list[str] = []

    async def handle_request(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(
            200,
            request=request,
            text="User-agent: FoodFindMenuLinkResolver\nDisallow: /\n",
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=public_host,
        )

        menu_uri = await resolver.resolve_menu_uri(
            website_uri="https://restaurant.example/"
        )

    assert menu_uri is None
    assert requested_paths == ["/robots.txt"]


@pytest.mark.anyio
async def test_does_not_guess_a_menu_path_when_no_explicit_link_exists() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            request=request,
            headers={"Content-Type": "text/html"},
            text='<a href="/about">About</a><a href="/contact">Contact</a>',
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=public_host,
        )

        menu_uri = await resolver.resolve_menu_uri(
            website_uri="https://restaurant.example/"
        )

    assert menu_uri is None


@pytest.mark.anyio
async def test_skips_inspection_when_robots_cannot_be_read_safely() -> None:
    requested_paths: list[str] = []

    async def handle_request(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(500, request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=public_host,
        )

        menu_uri = await resolver.resolve_menu_uri(
            website_uri="https://restaurant.example/"
        )

    assert menu_uri is None
    assert requested_paths == ["/robots.txt"]


@pytest.mark.anyio
async def test_does_not_request_a_website_that_resolves_to_a_private_address() -> None:
    request_count = 0

    async def handle_request(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, request=request)

    async def private_host(_: str) -> tuple[str, ...]:
        return ("127.0.0.1",)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=private_host,
        )

        menu_uri = await resolver.resolve_menu_uri(
            website_uri="http://localhost/"
        )

    assert menu_uri is None
    assert request_count == 0


@pytest.mark.anyio
async def test_translates_a_website_request_failure() -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private network detail", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle_request)
    ) as http_client:
        resolver = WebsiteMenuLinkResolver(
            http_client=http_client,
            resolve_hostname=public_host,
        )

        with pytest.raises(MenuLinkResolverError):
            await resolver.resolve_menu_uri(
                website_uri="https://restaurant.example/"
            )
