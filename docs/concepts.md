# Implementation Concepts

This file explains code concepts used in FoodFind. It is meant as a lightweight reference while building the project, not as a product requirements document.

## Current integration shape

FoodFind currently talks to Google Places from the backend. The important design choice is that Google-specific behavior stays at the edge of the app.

The rest of the app should depend on a simpler idea: “find nearby food places.” Google is one provider that can satisfy that need, but it should not shape the whole application.

The main boundary is now represented by three parts:

- `app/domain/place.py` defines FoodFind's `Place` and `Coordinates` objects.
- `app/ports/place_provider.py` defines the search capability the application can use.
- `app/adapters/google_places.py` translates between that capability and Google Places.

## Configuration and `.env`

The Google API key lives in `.env`, outside the committed codebase.

That gives the project one local place for secrets while keeping them out of Git. The app reads the value through the settings layer instead of reading environment variables directly in many files.

In this project:

- `.env` stores local secret values.
- `app/settings.py` defines the settings object.
- Application code receives configuration through that settings object.

This keeps configuration access consistent and easier to change later.

## Secret values

The Google API key is represented as a secret value in the settings layer.

This does not make the key impossible to leak, but it reduces accidental exposure in logs, repr output, tracebacks, and debug printing. When code truly needs the raw key, it must explicitly extract the value and pass it to the Google adapter.

The key should not appear in:

- browser code
- rendered HTML
- committed files
- test fixtures
- logs
- error output

## HTTP client

An HTTP client is the object Python uses to send web requests.

FoodFind is a server when it responds to browser requests. It also becomes a client when it calls Google Places. In that second role, Google is the server and FoodFind is the client.

The HTTP client sends the request, receives the response, and gives the app access to the returned status code and JSON body.

## Async HTTP client

The Google Places call uses an async HTTP client because external network calls can take noticeable time.

Async code lets Python wait for I/O without blocking the whole process. In this project, the Google request is awaited:

```python
response = await http_client.post(...)
```

That means: start the request, wait until the response is available, then continue.

## `asyncio`

Async functions need an event loop to run.

The manual Google check is a normal terminal command, so it uses `asyncio.run(...)` to start Python’s async runner and execute the async function.

Without that, calling an async function from a regular script would create a coroutine object but would not actually run the Google request.

## `if __name__ == "__main__"`

This Python pattern means: only run the script’s main function when the file is executed directly.

It matters for `app/scripts/google_places_smoke.py` because importing the file should not accidentally make a real Google API request.

## Automated tests vs manual smoke checks

Automated tests and smoke checks serve different purposes.

Automated tests are safe, repeatable, and should run often. In FoodFind, they use mocked Google responses and must not call the real Google API.

Manual smoke checks verify that the real integration works against the real external service. They can require network access, a valid API key, and billing/quota protection.

For this project:

- `tests/adapters/test_google_places.py` is an automated test file.
- `app/scripts/google_places_smoke.py` is a manual verification script.

The smoke script stays outside `tests/` so `pytest` does not accidentally call Google.

## Mock transport

A mock transport replaces the real network layer in tests.

Normally, the HTTP client sends a request over the internet. With a mock transport, the test intercepts the request, inspects it, and returns a fake response.

This lets the tests verify important behavior without depending on:

- Google availability
- internet access
- billing
- API quota
- a real API key

The tests can still confirm that the app sends the correct URL, headers, field mask, and request body.

## Field mask

Google Places uses a field mask to decide which fields to return.

The field names must match Google’s API schema exactly. For example, Google uses `displayName`, not Python-style `display_name`.

Field masks are useful because they:

- keep responses smaller
- make returned data more predictable
- avoid requesting fields the app does not need yet
- can affect billing tier depending on the fields requested

For Phase 1, FoodFind asks for basic place fields only.

## Pydantic models

Pydantic models define the expected shape of data.

FoodFind uses them to validate Google’s JSON response and convert it into structured Python objects. This is safer than passing raw dictionaries throughout the app.

If Google returns a shape the code does not expect, validation can catch the issue near the API boundary instead of allowing bad data to spread deeper into the application.

## Pydantic aliases

Google’s API uses camelCase field names. Python code usually uses snake_case names.

Pydantic aliases let the app read Google’s field names while exposing normal Python names in code.

Example:

- Google response: `displayName`
- Python attribute: `display_name`

This keeps vendor naming conventions from leaking through the rest of the codebase.

## Response parsing

After Google returns JSON, FoodFind validates and parses the response into Pydantic models.

This creates a clear boundary:

- outside the adapter: raw provider JSON
- inside the adapter: validated Google-specific Python objects
- outside the adapter: FoodFind-owned `Place` objects

The conversion happens before the adapter returns, so application code never needs to read fields such as Google's `displayName`.

## Domain models and immutable snapshots

The internal `Place` and `Coordinates` objects are frozen dataclasses. A dataclass is a compact way to define a data-focused Python object. `frozen=True` prevents normal field reassignment after creation.

That gives later steps one stable snapshot of a normalized provider result. Search and display code can pass the object explicitly without re-reading mutable provider data at different lifecycle stages.

The internal model records the provider and provider place ID because the result still comes from an external source. Missing optional fields remain `None`; FoodFind does not guess values that Google did not return.

## Ports and protocols

A port describes a capability the application needs without selecting the technology that provides it. `PlaceProvider` says that a provider can search nearby and return FoodFind `Place` objects.

Python's `Protocol` supports this style through structural typing: an adapter satisfies the port by providing the required method and compatible signature. The application can later receive a Google adapter, a Yelp adapter, or a fake test provider through the same boundary.

## Adapter / gateway pattern

The Google Places integration is implemented as an adapter, also called a gateway.

The adapter knows Google-specific details:

- endpoint URL
- authentication headers
- request body format
- field mask
- response shape
- error behavior

The rest of the app should not need to know those details. It should ask for an application-level action, such as “search nearby places.”

Adapters are useful because they:

- reduce vendor lock-in
- keep external service details out of core app logic
- make tests easier
- make provider replacement easier
- give each file a clearer responsibility

## If FoodFind later moves to Yelp or another provider

The Google adapter should not be modified to pretend it is Yelp.

Instead, the app would add a new provider adapter, such as a Yelp adapter, with the same high-level behavior. Ideally, both adapters expose a similar method such as `search_nearby`.

FoodFind already defines its own internal `Place` model and `PlaceProvider` port. A Yelp adapter would translate Yelp's response into that same model rather than changing the Google adapter or exposing Yelp's raw response format to the application.

## Mental model

The app should depend on capabilities, not vendors.

FoodFind needs the capability to find nearby food places. Google is the first implementation of that capability.

The adapter translates:

1. FoodFind request → Google request
2. Google response → FoodFind-friendly result

If another provider is added later, a different adapter can perform the same translation.
