# Phase 1 Overview

This document explains what FoodFind built in Phase 1, how the pieces connect, why each Python file exists, and how this foundation supports later phases.

## What Phase 1 accomplished

Phase 1 built the smallest complete FoodFind data flow:

1. A user opens the FoodFind page.
2. The page does not search automatically.
3. The user selects **Search Toronto**.
4. The browser sends one `POST` request to the FoodFind backend.
5. The backend runs a search with a fixed Toronto location and radius.
6. The Google Places adapter makes one server-side Google request.
7. Google's response is validated and converted into FoodFind-owned `Place` objects.
8. The browser receives those normalized places and displays them in a list.

This is often called a vertical slice: one thin but complete path through the browser, backend, external provider, internal models, and tests.

The current fixed search uses:

- Toronto City Hall: latitude `43.6532`, longitude `-79.3832`
- radius: `1,000` metres
- place types: `restaurant` and `cafe`
- maximum Google results per request: `20`

## What the user can do now

After starting the application and opening the home page, the user can select **Search Toronto**. FoodFind displays each returned place's available:

- name
- category
- address
- provider attribution

The button is disabled while the request is active, preventing overlapping searches. Reloading the page returns to the initial state and does not automatically contact Google.

This interface is deliberately small. User-selected locations, radius controls, richer result details, maps, filters, and smart search belong to later phases.

## The complete request path

```text
Browser: Search Toronto click
        |
        | POST /api/places/search
        v
app/main.py: search_places()
        |
        | receives a PlaceProvider dependency
        v
app/application/search_fixed_toronto.py
SearchFixedTorontoPlaces.execute()
        |
        | calls the provider port with fixed criteria
        v
app/ports/place_provider.py: PlaceProvider
        |
        | implemented by
        v
app/adapters/google_places.py: GooglePlacesGateway
        |
        | server-side HTTPS request
        v
Google Places API
        |
        | Google JSON response
        v
Google Pydantic response models
        |
        | _to_place()
        v
app/domain/place.py: list[Place]
        |
        | FastAPI JSON response
        v
app/static/search.js: rendered result list
```

The important boundary is in the middle: the application asks for the capability represented by `PlaceProvider`; it does not ask specifically for Google. Google is currently the adapter that supplies that capability.

## Architecture by responsibility

```text
app/domain/       FoodFind-owned data definitions
app/ports/        capabilities the application requires
app/application/  FoodFind actions and workflow rules
app/adapters/     external-service implementations
app/main.py       FastAPI routes and dependency wiring
app/settings.py   server-side configuration
app/scripts/      manual operational checks
tests/            automated behavior checks
```

This follows a small hexagonal, or ports-and-adapters, structure. The core concepts are owned by FoodFind. Framework and provider details remain at the edges.

## Production Python files

### `app/domain/place.py`

Purpose:

- Defines the provider-independent data FoodFind uses after a provider response has been normalized.

Definitions:

- `Coordinates`: stores `latitude` and `longitude`.
- `Place`: stores provider attribution, provider place ID, name, optional category information, optional address, and coordinates.

Both are frozen dataclasses. Their normal fields cannot be reassigned after creation. That gives the rest of the request one stable snapshot instead of shared mutable provider data.

Used by:

- `PlaceProvider` as its return type.
- `GooglePlacesGateway._to_place()` when normalizing Google records.
- `SearchFixedTorontoPlaces` as its result type.
- `app.main.search_places()` as its response type.
- Test fakes and expected test results.
- FastAPI, which serializes the dataclasses into JSON for the browser.

Prerequisites:

- Only Python's standard `dataclasses` module.

Why it exists:

Without this file, application and browser-facing code would depend on fields such as Google's `displayName`. Adding Yelp or another provider would then require changing core code. The internal `Place` model prevents that coupling.

#### How `Place` makes provider results consistent

`Place` defines the consistent **data format of each returned search result** across FoodFind. It does not define the parameters or behavior of the `search_nearby(...)` function; `PlaceProvider` handles that separate responsibility.

Every gateway's `search_nearby(...)` implementation should return FoodFind `Place` objects, regardless of the provider's original response format:

```text
Google record ──Google gateway──> Place
Yelp record   ───Yelp gateway───> Place
Other record  ──Other gateway───> Place
```

The conversion normally happens inside the provider adapter or gateway. In the current Google gateway, `search_nearby(...)` validates Google's response and calls `_to_place(...)` for every Google record. A future Yelp gateway would perform its own Yelp-to-`Place` conversion before returning its results.

This means the rest of FoodFind can always work with fields such as:

- `place.name`
- `place.category`
- `place.address`
- `place.coordinates`

It does not need one code path for `google_place.displayName` and another for whatever field name Yelp uses.

The precise distinction is:

- `Place` standardizes the shape of one result.
- `Sequence[Place]` standardizes the collection returned by a search.
- `PlaceProvider.search_nearby(...)` standardizes the search method's required behavior and signature.

### `app/ports/place_provider.py`

Purpose:

- Defines the nearby-place-search capability FoodFind needs.

Definition:

- `PlaceProvider`: a Python `Protocol` with the asynchronous `search_nearby(...)` method.

`search_nearby(...)` requires:

- latitude
- longitude
- radius in metres
- included place types

It returns a sequence of FoodFind `Place` objects.

Used by:

- `SearchFixedTorontoPlaces`, which receives a `PlaceProvider` rather than a Google class.
- `GooglePlacesGateway`, which implements the protocol.
- `get_place_provider()` and `search_places()` for FastAPI dependency typing.
- Fake providers in automated tests.

Prerequisites:

- `app.domain.place.Place`
- Python's `Protocol` and `Sequence` typing tools

Why it exists:

The port lets high-level application code depend on a capability instead of a vendor. Later, another adapter can implement the same method without rewriting the search use case.

#### How `PlaceProvider` acts as a contract

It is reasonable to think of `PlaceProvider` as a template, but **contract**, **interface**, or **protocol** is more precise. It describes the method a place provider must offer:

```python
async def search_nearby(
    *,
    latitude: float,
    longitude: float,
    radius_meters: float,
    included_types: Sequence[str],
) -> Sequence[Place]
```

It does not contain the real search implementation. Google and Yelp need different request code, so each gateway supplies its own implementation while following this shared contract.

In the current declaration:

```python
class GooglePlacesGateway(PlaceProvider):
```

`GooglePlacesGateway` explicitly inherits from the `PlaceProvider` protocol. Calling it a parent is not entirely wrong in normal Python inheritance terms, but it is important that this parent supplies a required shape rather than shared search behavior. The actual Google behavior still lives in `GooglePlacesGateway.search_nearby(...)`.

Python protocols also support structural typing. That means another class can satisfy `PlaceProvider` by defining a compatible `search_nearby(...)` method even if it does not explicitly write `(PlaceProvider)` after its class name. Explicit inheritance is used for `GooglePlacesGateway` because it makes the intended relationship clear.

In the FastAPI route:

```python
async def search_places(
    place_provider: Annotated[PlaceProvider, Depends(get_place_provider)],
):
```

the two parts of `Annotated[...]` have different jobs:

- `PlaceProvider` is the declared type of the `place_provider` parameter. It tells readers, editors, and type checkers which behavior the route is allowed to rely on.
- `Depends(get_place_provider)` is FastAPI metadata. It tells FastAPI to call `get_place_provider()` and inject the returned object as the argument.

During a real search, the injected object is a `GooglePlacesGateway`. During tests, FastAPI's dependency override injects a fake recording provider. The route can use either because it depends only on the `PlaceProvider` contract.

A protocol is primarily a design and type-checking contract; it does not automatically perform complete runtime validation of every method signature. Tests and static type checking provide additional verification that implementations behave as expected.

### `app/adapters/google_places.py`

Purpose:

- Contains everything specific to Google Places nearby search.
- Converts between FoodFind's provider call and Google's API format.
- Prevents Google response shapes from leaking into the application.

Constants:

- `GOOGLE_NEARBY_SEARCH_URL`: Google's nearby-search endpoint.
- `GOOGLE_FIELD_MASK`: the exact Google fields Phase 1 requests.

Google-only response models:

- `GoogleLocalizedText`
- `GoogleLocation`
- `GooglePlaceRecord`
- `GoogleNearbySearchResponse`

These Pydantic models validate Google's JSON. Aliases such as `displayName` allow Google camelCase input to become normal Python attributes such as `display_name` inside the adapter.

`GooglePlacesGateway.__init__(...)`:

- Requires a non-empty API key.
- Requires an already-created `httpx.AsyncClient`.
- Stores both for the gateway request.

Called by:

- `get_place_provider()` in `app/main.py` for normal application searches.
- `run()` in the manual smoke script.
- Adapter tests with a mocked HTTP client.

Prerequisites:

- a server-side Google API key
- an `httpx.AsyncClient`
- `PlaceProvider`
- FoodFind `Place` and `Coordinates`
- Pydantic

`GooglePlacesGateway.search_nearby(...)`:

1. Rejects an empty place-type collection.
2. Rejects radii outside `0 < radius <= 50,000` metres.
3. Builds the Google headers and JSON request body.
4. Sends one asynchronous `POST` request.
5. Raises an HTTP error for a failed Google response.
6. Validates successful JSON with `GoogleNearbySearchResponse`.
7. Converts every Google record into a FoodFind `Place`.
8. Returns `list[Place]`.

`GooglePlacesGateway._to_place(...)`:

- Is a private static conversion helper.
- Maps Google ID to `provider_place_id`.
- Maps Google's display name, category, address, and coordinates to FoodFind fields.
- Sets the provider to `google`.
- Preserves missing optional fields as `None` instead of guessing them.

Used by:

- `search_nearby(...)` once for every validated Google result.

Why this file exists:

Google authentication, field masks, request bodies, aliases, and response formats are not FoodFind business rules. Keeping them in an adapter makes the rest of FoodFind provider-independent and easier to test.

### `app/application/search_fixed_toronto.py`

Purpose:

- Defines the Phase 1 fixed-Toronto search action.
- Keeps the fixed search state in one known place.

Constants:

- `TORONTO_CITY_HALL`
- `TORONTO_SEARCH_RADIUS_METERS`
- `TORONTO_SEARCH_TYPES`

`SearchFixedTorontoPlaces.__init__(...)`:

- Requires a `PlaceProvider`.
- Does not create or import the Google adapter.

`SearchFixedTorontoPlaces.execute()`:

- Calls the injected provider exactly once.
- Passes the fixed coordinates, radius, and place types.
- Returns the provider's normalized `Place` sequence.

Called by:

- `search_places()` in `app/main.py`.
- The application-level automated test.

Prerequisites:

- `PlaceProvider`
- `Place` and `Coordinates`
- an injected provider implementation at runtime

Why it exists:

The API route should handle HTTP, while the use case should define what a FoodFind action means. When Phase 2 adds user-selected criteria, the application layer can evolve without placing search rules inside FastAPI routes or Google code.

### `app/settings.py`

Purpose:

- Defines the application's server-side configuration boundary.

`Settings`:

- Reads configuration from environment variables and `.env`.
- Requires `GOOGLE_MAPS_API_KEY`.
- represents the key as Pydantic `SecretStr` to reduce accidental display in logs and debugging output.
- ignores unrelated environment variables.

Created by:

- `get_place_provider()` only when the search endpoint needs the real Google provider.
- `run()` in the manual smoke script.

Prerequisites:

- `pydantic-settings`
- `pydantic`
- `.env` containing `GOOGLE_MAPS_API_KEY`, or the same environment variable supplied another way

Why it exists:

The API key remains outside code, browser assets, test data, and responses. Configuration access is also centralized instead of repeated throughout the application.

### `app/main.py`

Purpose:

- Creates the FastAPI application.
- Serves the HTML page and static files.
- Connects framework, settings, use case, port, and Google adapter at the application's composition root.

Top-level setup:

- `APP_DIR` locates templates and static assets relative to the Python file.
- `app = FastAPI(...)` creates the web application.
- `app.mount(...)` makes CSS and JavaScript available under `/static`.
- `templates` configures Jinja templates.

`get_place_provider()`:

- Is an asynchronous FastAPI dependency.
- Creates `Settings` only for a route that requires the provider.
- Creates an `httpx.AsyncClient` with a ten-second timeout.
- creates `GooglePlacesGateway` with the server-side key and HTTP client.
- yields it as the `PlaceProvider` capability.
- closes the HTTP client after the request completes.

Used by:

- FastAPI's `Depends(...)` on the search route.
- Automated tests, which override it with a fake provider.

Prerequisites:

- a valid `Settings` object for a real search
- HTTPX
- the Google adapter

`home(request)`:

- Handles `GET /`.
- Renders `app/templates/index.html`.
- Does not depend on or construct a provider.
- Does not search.

Called by:

- FastAPI when a browser loads or reloads the home page.

`search_places(place_provider)`:

- Handles `POST /api/places/search`.
- Receives a `PlaceProvider` through FastAPI dependency injection.
- creates `SearchFixedTorontoPlaces` with that provider.
- awaits `execute()` once.
- returns the normalized places as JSON.

Called by:

- `app/static/search.js` after the user selects **Search Toronto**.

Why this file does not perform Google mapping itself:

`app/main.py` is the web and wiring layer. Moving provider request construction or response normalization here would mix HTTP routing with Google behavior and make both harder to replace and test.


### `app/scripts/google_places_smoke.py`

Purpose:

- Performs one manually requested check against the real Google Places API.
- Confirms that the key, Google Cloud configuration, network, request, and current response shape work together.

`run()`:

1. Loads `Settings` and the real key.
2. Creates an HTTPX async client.
3. Creates `GooglePlacesGateway`.
4. Runs one fixed Toronto request.
5. Prints the result count and up to three place names.

`main()`:

- Starts Python's async event loop with `asyncio.run(run())`.

`if __name__ == "__main__"`:

- Ensures the live request runs only when the script is deliberately executed.
- Importing the module does not call Google.

Called by:

- A developer manually running `python -m app.scripts.google_places_smoke`.

Prerequisites:

- valid `.env` key
- Google Places APIs enabled and allowed for the key
- network access
- billing/quota safeguards

Why it is outside `tests/`:

Pytest must remain free, deterministic, and safe to run repeatedly. A real Google call can consume quota, create cost, fail because of networking, and change as Google's data changes. The live smoke check is therefore manual.

## Automated test Python files

### `tests/conftest.py`

Purpose:

- Provides shared pytest configuration.

`anyio_backend()`:

- Tells AnyIO-based async tests to use Python's `asyncio` backend.
- Prevents the same async tests from being attempted against an unavailable alternative backend.

Used by:

- Tests marked with `@pytest.mark.anyio`.

Prerequisites:

- pytest
- AnyIO support installed through the application dependencies

### `tests/adapters/test_google_places.py`

Purpose:

- Tests the Google adapter without using the internet or a real key.

`test_search_nearby_makes_one_server_side_google_request()` verifies:

- exactly one request is made
- HTTP method and URL
- key and field-mask headers
- the key is absent from the URL and body
- request coordinates, radius, and types
- Google JSON is normalized into the expected FoodFind `Place`

`test_search_nearby_preserves_missing_optional_place_fields()` verifies:

- missing Google category and address values become `None`
- FoodFind does not invent missing provider data

`test_search_nearby_raises_for_google_error_response()` verifies:

- a Google error such as HTTP `429` becomes an `httpx.HTTPStatusError`

The local `handle_request(...)` functions are fake HTTP handlers used by `httpx.MockTransport`. They inspect outgoing requests and return controlled fake Google responses.

Prerequisites:

- `GooglePlacesGateway`
- FoodFind domain models
- pytest
- HTTPX mock transport

No test in this file reads `.env` or contacts Google.

### `tests/application/test_search_fixed_toronto.py`

Purpose:

- Tests the application use case without FastAPI or Google.

`RecordingPlaceProvider`:

- Is a fake implementation of the `PlaceProvider` shape.
- records every search call instead of contacting an external service.

`test_fixed_toronto_search_calls_provider_once_with_fixed_criteria()` verifies:

- the use case calls the provider exactly once
- the correct Toronto coordinates are used
- the radius is `1,000` metres
- the types are `restaurant` and `cafe`

Prerequisites:

- the application use case
- the domain `Place` type
- pytest async support

Why this test is separate from the adapter test:

It answers a different question. The adapter test asks, "Does FoodFind speak to Google correctly?" The application test asks, "Does the Phase 1 FoodFind action use the right search criteria?"

### `tests/test_app.py`

Purpose:

- Tests FastAPI routing, dependency wiring, and the page shell.

`RecordingPlaceProvider`:

- Is a fake provider for route tests.
- counts calls and returns one known normalized `Place`.

`client()`:

- Creates FastAPI's test client.
- clears dependency overrides after each test so one test cannot affect another.

`test_home_page_renders_foodfind_shell()` verifies:

- `GET /` succeeds
- the page contains the FoodFind shell
- the explicit button, status region, results list, and browser script are present

`test_search_script_is_served_as_a_static_asset()` verifies:

- `/static/search.js` is available
- the script is click-driven and uses `POST`

`test_page_loads_do_not_search_provider()` verifies:

- initial load and reload succeed
- neither load constructs the provider dependency
- neither load calls `search_nearby(...)`

`test_explicit_search_calls_provider_once_and_returns_places()` verifies:

- one `POST /api/places/search` constructs one provider dependency
- the provider is called once
- the normalized JSON response has the expected shape

Prerequisites:

- the FastAPI app
- FoodFind domain models
- pytest
- FastAPI/Starlette `TestClient`

The real `get_place_provider()` dependency is overridden, so these tests do not load the API key or contact Google.

## Supporting non-Python files

The Python files provide the backend flow, but three browser files complete the Phase 1 user journey.

### `app/templates/index.html`

- Defines the page structure.
- Provides the explicit search button.
- Provides the live status region and empty results list.
- loads CSS and the deferred search script.

### `app/static/search.js`

- Registers a click handler without searching during page load.
- disables the button while a request is active.
- sends `POST /api/places/search`.
- renders the returned normalized places.
- uses `textContent` so provider strings are treated as text rather than HTML.
- shows basic loading, empty, success, and failure messages.

### `app/static/styles.css`

- Styles the initial shell, search panel, button, status, and place cards.
- includes a small-screen layout.
- provides visible hover, disabled, and keyboard-focus states.

The current browser layer is intentionally small and has no Svelte/TypeScript build system yet. The preferred frontend stack remains Svelte 5 and SvelteKit; introducing it is more useful when later phases add reusable location, radius, filter, map, and state-management components.

## Runtime prerequisites

For normal local operation, Phase 1 needs:

1. Python 3.10 or newer.
2. A virtual environment with `requirements.txt` installed.
3. A `.env` file containing `GOOGLE_MAPS_API_KEY`.
4. Places API and Places API (New) allowed for the key.
5. Google Cloud billing and the configured budget alert.
6. Network access for deliberate live searches.

The API key remains server-side. The HTML and JavaScript never receive it; the browser talks only to FoodFind's own endpoint.

Automated tests need the Python dependencies but do not need `.env`, a real key, Google access, or internet access.

## How Phase 1 prepares the next phases

### Phase 2: selected location, radius, and richer discovery

Current foundation:

- the provider port already accepts latitude, longitude, and radius
- the application layer owns search criteria
- the browser already has an explicit search action
- the backend already returns normalized results

Likely extension:

- replace fixed constants with a FoodFind search-criteria object
- validate user-supplied location and radius at the API boundary
- pass the validated criteria into a generalized search use case
- request and normalize additional Google fields for details and actions
- add complete loading, no-result, and provider-error recovery

The Google adapter and domain model can be extended rather than bypassed.

### Phase 3: map experience

Current foundation:

- every normalized `Place` already has `Coordinates`
- list results have stable provider IDs
- browser results come from one normalized snapshot

Likely extension:

- give the same place snapshot to both list and map components
- use provider place IDs to connect markers and list items
- keep selected state in the frontend without changing Google response parsing

### Phase 4: filters and sorting

Current foundation:

- provider calls already accept included place types
- categories are retained from the provider
- search logic is separate from HTTP routing and Google request construction

Likely extension:

- introduce FoodFind-owned search criteria and category types
- map those criteria to Google-specific types inside the adapter
- normalize or derive sortable fields with clear source attribution
- test filter behavior against fake providers before adding provider mapping tests

### Phase 5: current location

Current foundation:

- the provider and use case already work from coordinates
- the browser search is explicit

Likely extension:

- request browser geolocation only after a user action
- pass the obtained coordinates through the same generalized search path
- preserve a manually selected location as fallback

Current-location support should not need a separate Google integration.

### Phase 6: smart search

Current foundation:

- one application boundary will represent normalized search criteria
- provider-specific translation remains in the adapter

Likely extension:

- convert typed or natural-language requests into the same criteria used by manual controls
- show those interpreted criteria in the UI
- call the same search use case after user review

Smart search should produce search state; it should not create a second path to Google.

### Adding or replacing a provider

Current foundation:

- application code depends on `PlaceProvider`
- application results use FoodFind `Place` objects

Likely extension:

1. Add another adapter implementing `search_nearby(...)`.
2. Validate that provider's response at its own boundary.
3. Convert its records into FoodFind `Place` objects.
4. Change dependency wiring in `app/main.py` or select an adapter through configuration.

The use case, route, and result list should not need to learn the new provider's raw response format.

## What Phase 1 intentionally did not build

- user-entered or selected locations
- user-selected radius
- current-location permission
- map and markers
- ratings, hours, phone, website, directions, and reservation actions
- manual filters and sorting
- smart or natural-language search
- database or permanent copies of Google business records
- automatic page-load searches
- automated live-Google tests
- a SvelteKit frontend structure

These are omissions by sequence, not architectural dead ends. Phase 1 established the boundaries needed to add them incrementally.

## Current verification status

The automated suite covers three layers:

- Google adapter behavior with mocked HTTP responses
- fixed-Toronto application behavior with a fake provider
- FastAPI routes and page safety with dependency overrides

At Phase 1 completion, all eight automated tests pass with warnings treated as errors. Python compilation and repository whitespace checks also pass.

The browser click-and-render flow has not yet been exercised through an automated browser session because no in-app browser session was available during the final Phase 1 verification. The endpoint, page structure, static script delivery, request lifecycle, and normalized response are covered by automated tests, but interactive browser verification remains a useful manual check.

## Short mental model

FoodFind owns:

- what a place looks like internally
- what a nearby search capability looks like
- what the current application search means
- when a search is allowed to run

Google owns:

- its endpoint
- authentication header
- field mask
- request and response schema
- current business data

The Google adapter translates between the two. FastAPI connects the browser to the application use case. Tests replace external edges with controlled fakes so the core flow can be verified safely.
