# Features

This file breaks the product into individual features, including expected behavior, edge cases, acceptance criteria, and implementation notes.

## Nearby place search

### Current behavior

- `POST /api/places/search` accepts one normalized selected location containing a label, latitude, and longitude.
- Users choose a radius of 500 m, 1 km, 2 km, or 5 km; 1 km is the default.
- The fixed provider types are restaurant and café.
- The endpoint returns normalized FoodFind place objects.
- Loading or reloading the home page does not run a search.
- The Google client and server-side API key are created only when the search endpoint is called.
- The home page provides an explicit **Search** button.
- While a search is active, the button is disabled to prevent duplicate requests.
- Successful results appear in a list with the available name, category, address, and provider attribution.
- Missing category or address values are omitted instead of inferred.

The initial browser UI uses a small deferred JavaScript file. It attaches the API request only to the button's click event and does not run a search during page initialization.

### Acceptance criteria

- One endpoint request produces exactly one provider search.
- Repeated `GET /` requests produce zero provider searches.
- Automated tests replace the provider with a fake and never call Google.
- The selected coordinates and radius are passed into the generalized application use case; included types remain defined once there.
- Provider values are inserted with DOM text properties rather than interpreted as HTML.
- The result count and search status are announced through visible text and an ARIA live region.

Phase 2 keeps these states explicit and recoverable without adding a frontend state-management framework.

## Search feedback and recovery

### Current behavior

- Starting a valid search clears results from the previous search before making the request.
- Changing the location or radius clears previous results without starting another search.
- The status region reports when location suggestions, location resolution, or nearby search are in progress.
- An empty nearby-search response leaves the result list hidden and displays a no-results message.
- Browser-detected invalid coordinates or radius values display guidance without calling the nearby-place provider.
- API validation failures display input guidance, while provider or network failures display a temporary-unavailability message.
- Provider-specific transport and response errors become provider-neutral errors at the adapter boundary.
- The API returns a safe `502` response for provider failures without exposing Google response details.
- Controls are restored after successful, invalid, empty, or failed search requests.

No state-management framework is used. The current interface has one result-clearing helper and direct status updates appropriate to the size of the page.

### Acceptance criteria

- Old result elements and counts are removed when a new search begins or search inputs change.
- No-results, invalid-input, and provider-failure states have different visible messages.
- A provider failure returns HTTP `502` with `Cache-Control: no-store` and no provider error details.
- Automated provider-failure tests use fakes or mocked HTTP responses and never call Google.
- A failed operation does not leave the location, radius, or search controls permanently disabled.

## Decimal-coordinate location entry

### Current behavior

- The location field initially contains Toronto City Hall coordinates as an editable default.
- Users can enter or paste decimal coordinates in `latitude, longitude` order.
- The browser accepts latitude from `-90` through `90` and longitude from `-180` through `180`.
- The browser normalizes valid values before sending them.
- The API performs the authoritative range and finite-number validation.
- Invalid input displays guidance and does not make a place-provider search.
- The location field is disabled during an active search so the returned result snapshot cannot become disconnected from a changed input.
- Changing the location after a completed search hides the old results.

### Acceptance criteria

- A valid selected location is represented by a label and coordinates.
- An explicit search uses the submitted coordinates rather than fixed Toronto constants.
- Out-of-range coordinates return HTTP `422` and do not call `search_nearby(...)`.
- Loading, reloading, or editing the location does not search automatically.
- The submitted radius is validated and included in the normalized search criteria.

Map selection remains in Phase 3, and device current location remains in Phase 5.

## Search radius

### Current behavior

- The radius control offers 500 m, 1 km, 2 km, and 5 km.
- The initial selection is 1 km.
- Changing the radius hides results from the previous search but does not call either Google adapter.
- The browser snapshots the selected radius only after the user selects **Search**.
- The location and radius controls are both disabled while the place search is active.
- The API validates radius values from 100 m through 50 km.
- `SearchCriteria` carries the selected location and radius together as one immutable application snapshot.
- The generalized search use case passes the selected radius to `PlaceProvider.search_nearby(...)`.

### Acceptance criteria

- Selecting 2 km produces one nearby search with `radius_meters=2000`.
- Editing the radius alone produces no provider call.
- Radius values below 100 m or above 50 km return HTTP `422` and do not search.
- Page load and reload do not search.
- The result lifecycle cannot read a different radius after a search begins.

## Place and address autocomplete

### Current behavior

- A location value that is not valid decimal coordinates enters autocomplete mode.
- Autocomplete waits until the input contains at least three characters.
- The browser waits 350 milliseconds after the latest edit before requesting suggestions.
- A new edit cancels the previous in-flight suggestion request and ignores stale responses.
- The browser uses one UUIDv4 session token across the typing and selection requests.
- Google Autocomplete (New) returns place predictions through FoodFind's server-side adapter.
- Suggestions are biased toward a 50 km circle around Toronto City Hall but are not geographically restricted to that circle.
- Google returns up to five predictions; FoodFind ignores query predictions and displays place predictions only.
- Suggestions appear in a visually separate list with visible `Google Maps` attribution.
- Selecting a suggestion calls Place Details (New) once to obtain its place ID and coordinates.
- The selected suggestion label becomes the visible location label.
- Completing a selection ends the session and causes the browser to generate a new session token for future edits.
- Search is disabled while text does not represent valid coordinates or a resolved suggestion.
- Selecting a suggestion does not automatically search for food places; the user must still select **Search**.

### Acceptance criteria

- Page loads and reloads do not construct a location provider or call Google.
- Direct decimal-coordinate entry makes no autocomplete or resolution request.
- Short queries make no provider request.
- Automated tests use fake location providers and mocked HTTPX responses.
- The API key is absent from browser code, URLs, request bodies, and responses.
- Suggestion and resolved-location responses use `Cache-Control: no-store`.
- Only UUIDv4 session tokens are accepted.
- Changing the input invalidates a previously resolved suggestion.
- A resolved suggestion produces the same `SelectedLocation` shape used by direct coordinates.
