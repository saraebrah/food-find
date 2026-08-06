import asyncio
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

import httpx

from app.ports.menu_link_resolver import MenuLinkResolverError


USER_AGENT = "FoodFindMenuLinkResolver/1.0"
MAX_REDIRECTS = 3
MAX_DOCUMENT_BYTES = 1_000_000
MENU_WORD_PATTERN = re.compile(r"\bmenus?\b", re.IGNORECASE)
ORDER_PATTERN = re.compile(r"\b(?:order|ordering)\s+(?:online|now)\b", re.IGNORECASE)
MENU_PATH_PATTERN = re.compile(r"(?:^|[-_/])menus?(?:[-_/.]|$)", re.IGNORECASE)
ORDER_PATH_PATTERN = re.compile(
    r"(?:^|[-_/])(?:order-online|online-order|ordering)(?:[-_/.]|$)",
    re.IGNORECASE,
)

HostnameResolver = Callable[[str], Awaitable[Sequence[str]]]


@dataclass(frozen=True, slots=True)
class _FetchedDocument:
    status_code: int
    url: str
    content_type: str | None
    body: bytes


@dataclass(frozen=True, slots=True)
class _LinkCandidate:
    href: str
    label: str


class _HomepageLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[_LinkCandidate] = []
        self._href: str | None = None
        self._label_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.casefold() != "a" or self._href is not None:
            return

        attributes = {name.casefold(): value or "" for name, value in attrs}
        href = attributes.get("href", "").strip()
        if not href:
            return

        self._href = href
        self._label_parts = [
            attributes.get("aria-label", ""),
            attributes.get("title", ""),
        ]

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._label_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._href is None:
            return

        label = " ".join(" ".join(self._label_parts).split())
        self.links.append(_LinkCandidate(href=self._href, label=label))
        self._href = None
        self._label_parts = []


async def _resolve_hostname(hostname: str) -> tuple[str, ...]:
    records = await asyncio.to_thread(
        socket.getaddrinfo,
        hostname,
        None,
        type=socket.SOCK_STREAM,
    )
    return tuple(dict.fromkeys(record[4][0] for record in records))


class WebsiteMenuLinkResolver:
    """Find an explicit menu link on a restaurant's authoritative homepage."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        resolve_hostname: HostnameResolver = _resolve_hostname,
    ) -> None:
        self._http_client = http_client
        self._resolve_hostname = resolve_hostname

    async def resolve_menu_uri(self, *, website_uri: str) -> str | None:
        if not await self._is_safe_public_url(website_uri):
            return None

        try:
            if not await self._robots_allows(website_uri):
                return None
            homepage = await self._fetch_document(website_uri)
        except httpx.HTTPError as error:
            raise MenuLinkResolverError("Restaurant website request failed") from error

        if homepage is None or homepage.status_code != 200:
            return None
        if homepage.content_type is not None and not homepage.content_type.startswith(
            ("text/html", "application/xhtml+xml")
        ):
            return None

        parser = _HomepageLinkParser()
        parser.feed(homepage.body.decode("utf-8", errors="ignore"))

        ranked_links = sorted(
            parser.links,
            key=self._candidate_score,
            reverse=True,
        )
        for candidate in ranked_links:
            if self._candidate_score(candidate) == 0:
                break
            menu_uri, _ = urldefrag(urljoin(homepage.url, candidate.href))
            if menu_uri == homepage.url and not MENU_PATH_PATTERN.search(
                urlsplit(homepage.url).path
            ):
                continue
            if await self._is_safe_public_url(menu_uri):
                return menu_uri
        return None

    async def _robots_allows(self, website_uri: str) -> bool:
        parsed = urlsplit(website_uri)
        robots_uri = urlunsplit(
            (parsed.scheme, parsed.netloc, "/robots.txt", "", "")
        )
        try:
            document = await self._fetch_document(robots_uri)
        except httpx.HTTPError as error:
            raise MenuLinkResolverError("Restaurant robots request failed") from error

        if document is None:
            return False
        if document.status_code == 404:
            return True
        if document.status_code in {401, 403}:
            return False
        if document.status_code != 200:
            return False

        rules = robotparser.RobotFileParser()
        rules.set_url(robots_uri)
        rules.parse(document.body.decode("utf-8", errors="ignore").splitlines())
        return rules.can_fetch(USER_AGENT, website_uri)

    async def _fetch_document(self, url: str) -> _FetchedDocument | None:
        current_url = url
        for redirect_count in range(MAX_REDIRECTS + 1):
            if not await self._is_safe_public_url(current_url):
                return None

            async with self._http_client.stream(
                "GET",
                current_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.1",
                    "User-Agent": USER_AGENT,
                },
                follow_redirects=False,
            ) as response:
                if response.is_redirect:
                    location = response.headers.get("Location")
                    if location is None or redirect_count == MAX_REDIRECTS:
                        return None
                    current_url = urljoin(str(response.url), location)
                    continue

                declared_length = response.headers.get("Content-Length")
                if declared_length is not None:
                    try:
                        if int(declared_length) > MAX_DOCUMENT_BYTES:
                            return None
                    except ValueError:
                        return None

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_DOCUMENT_BYTES:
                        return None

                content_type = response.headers.get("Content-Type")
                return _FetchedDocument(
                    status_code=response.status_code,
                    url=str(response.url),
                    content_type=(
                        content_type.split(";", 1)[0].strip().casefold()
                        if content_type
                        else None
                    ),
                    body=bytes(body),
                )
        return None

    async def _is_safe_public_url(self, url: str) -> bool:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False

        try:
            addresses = await self._resolve_hostname(parsed.hostname)
            return bool(addresses) and all(
                ipaddress.ip_address(address).is_global for address in addresses
            )
        except (OSError, ValueError):
            return False

    @staticmethod
    def _candidate_score(candidate: _LinkCandidate) -> int:
        label = candidate.label.casefold()
        href = candidate.href.casefold()
        if MENU_WORD_PATTERN.search(label):
            return 100
        if MENU_PATH_PATTERN.search(urlsplit(href).path):
            return 80
        if ORDER_PATTERN.search(label):
            return 70
        if ORDER_PATH_PATTERN.search(urlsplit(href).path):
            return 60
        return 0
