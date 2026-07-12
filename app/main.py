from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.adapters.google_places import GooglePlacesGateway
from app.application.search_fixed_toronto import SearchFixedTorontoPlaces
from app.domain.place import Place
from app.ports.place_provider import PlaceProvider
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/places/search")
async def search_places(
    place_provider: Annotated[PlaceProvider, Depends(get_place_provider)],
) -> list[Place]:
    search = SearchFixedTorontoPlaces(place_provider=place_provider)
    return list(await search.execute())
