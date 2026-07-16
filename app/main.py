from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.adapters.google_places import GooglePlacesGateway
from app.adapters.google_locations import GoogleLocationGateway
from app.api.location_models import (
    AutocompleteLocationRequest,
    LocationSuggestionResponse,
    ResolveLocationRequest,
    SelectedLocationResponse,
)
from app.api.place_models import PlaceDetailsRequest
from app.api.search_models import SearchPlacesRequest
from app.application.get_place_details import (
    GetPlaceDetails,
    UnsupportedPlaceProviderError,
)
from app.application.search_places import SearchPlaces
from app.domain.place import Place, PlaceDetails
from app.ports.location_provider import LocationProvider, LocationProviderError
from app.ports.place_provider import PlaceProvider, PlaceProviderError
from app.settings import Settings


APP_DIR = Path(__file__).parent

app = FastAPI(title="FoodFind")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

templates = Jinja2Templates(directory=APP_DIR / "templates")


async def get_place_provider() -> AsyncIterator[PlaceProvider]:
    settings = Settings()
    async with httpx.AsyncClient(timeout=10) as http_client:
        yield GooglePlacesGateway(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )


async def get_location_provider() -> AsyncIterator[LocationProvider]:
    settings = Settings()
    async with httpx.AsyncClient(timeout=10) as http_client:
        yield GoogleLocationGateway(
            api_key=settings.google_maps_api_key.get_secret_value(),
            http_client=http_client,
        )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/places/search")
async def search_places(
    search_request: SearchPlacesRequest,
    response: Response,
    place_provider: Annotated[PlaceProvider, Depends(get_place_provider)],
) -> list[Place]:
    response.headers["Cache-Control"] = "no-store"
    search = SearchPlaces(place_provider=place_provider)
    criteria = search_request.to_domain()
    try:
        return list(await search.execute(criteria=criteria))
    except PlaceProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="Place search is temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error


@app.post("/api/places/details")
async def get_place_details(
    details_request: PlaceDetailsRequest,
    response: Response,
    place_provider: Annotated[PlaceProvider, Depends(get_place_provider)],
) -> PlaceDetails:
    response.headers["Cache-Control"] = "no-store"
    use_case = GetPlaceDetails(place_provider=place_provider)
    try:
        return await use_case.execute(
            provider=details_request.provider,
            provider_place_id=details_request.provider_place_id,
        )
    except UnsupportedPlaceProviderError as error:
        raise HTTPException(
            status_code=422,
            detail="Unsupported place provider",
            headers={"Cache-Control": "no-store"},
        ) from error
    except PlaceProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="Place details are temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error


@app.post("/api/locations/autocomplete")
async def autocomplete_locations(
    autocomplete_request: AutocompleteLocationRequest,
    response: Response,
    location_provider: Annotated[LocationProvider, Depends(get_location_provider)],
) -> list[LocationSuggestionResponse]:
    response.headers["Cache-Control"] = "no-store"
    try:
        suggestions = await location_provider.suggest(
            query=autocomplete_request.query,
            session_token=str(autocomplete_request.session_token),
        )
    except LocationProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="Location service is temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error
    return [
        LocationSuggestionResponse.from_domain(suggestion)
        for suggestion in suggestions
    ]


@app.post("/api/locations/resolve")
async def resolve_location(
    resolve_request: ResolveLocationRequest,
    response: Response,
    location_provider: Annotated[LocationProvider, Depends(get_location_provider)],
) -> SelectedLocationResponse:
    response.headers["Cache-Control"] = "no-store"
    try:
        location = await location_provider.resolve(
            suggestion=resolve_request.to_suggestion(),
            session_token=str(resolve_request.session_token),
        )
    except LocationProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="Location service is temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error
    return SelectedLocationResponse.from_domain(location)
