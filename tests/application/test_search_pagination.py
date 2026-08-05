import pytest

from app.application.search_places import SearchPlaces
from app.domain.location import SelectedLocation
from app.domain.place import Coordinates, Place, PlaceDetails
from app.domain.search import SearchCriteria, SearchFilters, SearchSort
from app.domain.search_intent import AvailabilityWindow, DescriptiveRequirement
from app.ports.place_provider import (
    PlaceProviderError,
    PlaceSearchPage,
)


SEARCH_ORIGIN = Coordinates(latitude=43.6532, longitude=-79.3832)


def make_place(
    number: int,
    *,
    rating: float | None = None,
    latitude_offset: float = 0,
) -> Place:
    return Place(
        provider="google",
        provider_place_id=f"place-{number}",
        name=f"Place {number}",
        category="Restaurant",
        category_code="restaurant",
        address=None,
        coordinates=Coordinates(
            latitude=SEARCH_ORIGIN.latitude + latitude_offset,
            longitude=SEARCH_ORIGIN.longitude,
        ),
        business_status="operational",
        rating=rating,
    )


class PagedPlaceProvider:
    provider_name = "google"

    def __init__(
        self,
        pages: dict[str | None, PlaceSearchPage | PlaceProviderError],
    ) -> None:
        self._pages = pages
        self.continuation_tokens: list[str | None] = []

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
        continuation_token: str | None = None,
    ) -> PlaceSearchPage:
        self.continuation_tokens.append(continuation_token)
        page = self._pages[continuation_token]
        if isinstance(page, PlaceProviderError):
            raise page
        return page

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        raise NotImplementedError


def criteria(*, sort: SearchSort = SearchSort.PROVIDER_DEFAULT) -> SearchCriteria:
    return SearchCriteria(
        location=SelectedLocation(
            label="Toronto City Hall",
            coordinates=SEARCH_ORIGIN,
        ),
        radius_meters=5_000,
        sort=sort,
    )


@pytest.mark.anyio
async def test_search_collects_then_sorts_and_limits_combined_pages() -> None:
    first_page = tuple(
        make_place(number, rating=3 + number / 10)
        for number in range(1, 9)
    )
    second_page = (
        make_place(8, rating=3.8),
        *(
            make_place(number, rating=3 + number / 20)
            for number in range(9, 24)
        ),
    )
    provider = PagedPlaceProvider(
        {
            None: PlaceSearchPage(
                places=first_page,
                continuation_token="page-2",
            ),
            "page-2": PlaceSearchPage(
                places=second_page,
                continuation_token="page-3",
            ),
        }
    )

    places = await SearchPlaces(place_provider=provider).execute(
        criteria=criteria(sort=SearchSort.RATING)
    )

    assert provider.continuation_tokens == [None, "page-2"]
    assert len(places) == 20
    assert len({place.provider_place_id for place in places}) == 20
    assert [place.rating for place in places] == sorted(
        (place.rating for place in places),
        reverse=True,
    )


@pytest.mark.anyio
async def test_search_does_not_continue_after_twenty_valid_results() -> None:
    provider = PagedPlaceProvider(
        {
            None: PlaceSearchPage(
                places=tuple(make_place(number) for number in range(1, 21)),
                continuation_token="unused-page-2",
            ),
        }
    )

    places = await SearchPlaces(place_provider=provider).execute(
        criteria=criteria()
    )

    assert len(places) == 20
    assert provider.continuation_tokens == [None]


@pytest.mark.anyio
async def test_search_stops_after_three_provider_requests() -> None:
    provider = PagedPlaceProvider(
        {
            None: PlaceSearchPage(
                places=(make_place(1),),
                continuation_token="page-2",
            ),
            "page-2": PlaceSearchPage(
                places=(make_place(2),),
                continuation_token="page-3",
            ),
            "page-3": PlaceSearchPage(
                places=(make_place(3),),
                continuation_token="page-4",
            ),
        }
    )

    places = await SearchPlaces(place_provider=provider).execute(
        criteria=criteria()
    )

    assert provider.continuation_tokens == [None, "page-2", "page-3"]
    assert [place.provider_place_id for place in places] == [
        "place-1",
        "place-2",
        "place-3",
    ]


@pytest.mark.anyio
async def test_search_returns_collected_results_when_continuation_fails() -> None:
    provider = PagedPlaceProvider(
        {
            None: PlaceSearchPage(
                places=(make_place(1), make_place(2)),
                continuation_token="page-2",
            ),
            "page-2": PlaceProviderError("continuation failed"),
        }
    )

    places = await SearchPlaces(place_provider=provider).execute(
        criteria=criteria()
    )

    assert provider.continuation_tokens == [None, "page-2"]
    assert [place.provider_place_id for place in places] == [
        "place-1",
        "place-2",
    ]


@pytest.mark.anyio
async def test_distance_sort_uses_combined_foodfind_distances() -> None:
    provider = PagedPlaceProvider(
        {
            None: PlaceSearchPage(
                places=(make_place(1, latitude_offset=0.01),),
                continuation_token="page-2",
            ),
            "page-2": PlaceSearchPage(
                places=tuple(
                    make_place(number, latitude_offset=number / 100_000)
                    for number in range(2, 22)
                ),
                continuation_token=None,
            ),
        }
    )

    places = await SearchPlaces(place_provider=provider).execute(
        criteria=criteria(sort=SearchSort.DISTANCE)
    )

    assert len(places) == 20
    assert [place.distance_meters for place in places] == sorted(
        place.distance_meters for place in places
    )
    assert places[0].provider_place_id == "place-2"
