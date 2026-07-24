from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai

from app.adapters.gemini_search_interpreter import GeminiSearchInterpreter
from app.adapters.google_locations import GoogleLocationGateway
from app.adapters.google_places import GooglePlacesGateway
from app.api.interpretation_models import (
    InterpretSearchRequest,
    SearchIntentResponse,
)
from app.api.location_models import (
    AutocompleteLocationRequest,
    LocationSuggestionResponse,
    ResolveLocationRequest,
    SelectedLocationResponse,
)
from app.api.place_models import PlaceDetailsRequest, PlaceResponse
from app.api.search_models import SearchPlacesRequest
from app.application.get_place_details import (
    GetPlaceDetails,
    UnsupportedPlaceProviderError,
)
from app.application.interpret_search import InterpretSearch
from app.application.search_places import (
    SearchPlaces,
    UnsupportedAvailabilityWindowError,
)
from app.domain.place import PlaceDetails
from app.domain.search_interpretation import SearchInterpretationContext
from app.ports.location_provider import LocationProvider, LocationProviderError
from app.ports.place_provider import PlaceProvider, PlaceProviderError
from app.ports.search_interpreter import (
    SearchInterpreter,
    SearchInterpreterError,
)
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


async def get_search_interpreter() -> AsyncIterator[SearchInterpreter]:
    settings = Settings()
    if settings.gemini_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="Smart search is not configured",
            headers={"Cache-Control": "no-store"},
        )

    client = genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
    )
    try:
        yield GeminiSearchInterpreter(
            models=client.aio.models,
            model=settings.gemini_model,
        )
    finally:
        await client.aio.aclose()


def get_current_datetime() -> datetime:
    return datetime.now(timezone.utc)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/places/search")
async def search_places(
    search_request: SearchPlacesRequest,
    response: Response,
    place_provider: Annotated[PlaceProvider, Depends(get_place_provider)],
    current_datetime: Annotated[datetime, Depends(get_current_datetime)],
) -> list[PlaceResponse]:
    response.headers["Cache-Control"] = "no-store"
    search = SearchPlaces(place_provider=place_provider)
    criteria = search_request.to_domain()
    try:
        places = await search.execute(
            criteria=criteria,
            descriptive_requirements=(
                search_request.descriptive_requirements_to_domain()
            ),
            availability_window=(
                search_request.availability_window_to_domain()
            ),
            current_datetime=current_datetime,
        )
        return [PlaceResponse.from_domain(place) for place in places]
    except UnsupportedAvailabilityWindowError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Requested availability is outside Google's "
                "seven-day hours range"
            ),
            headers={"Cache-Control": "no-store"},
        ) from error
    except PlaceProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="Place search is temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error


@app.post("/api/search/interpret")
async def interpret_search(
    interpretation_request: InterpretSearchRequest,
    response: Response,
    search_interpreter: Annotated[
        SearchInterpreter,
        Depends(get_search_interpreter),
    ],
    current_datetime: Annotated[datetime, Depends(get_current_datetime)],
) -> SearchIntentResponse:
    response.headers["Cache-Control"] = "no-store"
    context = SearchInterpretationContext(
        current_datetime=current_datetime,
        timezone_name=interpretation_request.timezone,
    )
    use_case = InterpretSearch(interpreter=search_interpreter)
    try:
        intent = await use_case.execute(
            query=interpretation_request.query,
            search_criteria=interpretation_request.search_criteria.to_domain(),
            context=context,
        )
    except SearchInterpreterError as error:
        raise HTTPException(
            status_code=502,
            detail="Smart search is temporarily unavailable",
            headers={"Cache-Control": "no-store"},
        ) from error
    return SearchIntentResponse.from_domain(
        intent=intent,
        timezone=context.timezone_name,
    )


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
