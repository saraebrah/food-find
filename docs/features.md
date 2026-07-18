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
- Successful results appear in a list with name, category, address, straight-line distance, and provider attribution.
- Businesses explicitly reported temporarily or permanently closed are excluded from results.
- Results with missing business status remain visible with an operational-status warning.
- Missing category or address values are identified as unavailable instead of inferred.

The active browser UI is a Svelte 5 and SvelteKit TypeScript application under `frontend/`. Its page-level search handler is the only place that starts a nearby search; rendering and initializing components do not search. The earlier server-rendered template and deferred JavaScript remain temporarily as a fallback during the transition.

### Acceptance criteria

- One endpoint request produces exactly one provider search.
- Repeated `GET /` requests produce zero provider searches.
- Automated tests replace the provider with a fake and never call Google.
- The selected coordinates and radius are passed into the generalized application use case; included types remain defined once there.
- Provider values are rendered through Svelte text interpolation rather than interpreted as HTML.
- The result count and search status are announced through visible text and an ARIA live region.

These states remain explicit and recoverable in local Svelte component state without adding an external state-management library.

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

No external state-management library is used. The Svelte page owns the search snapshot, results, and status; focused child components own suggestion and per-card detail lifecycles.

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

Map selection and device current location remain together in Phase 5.

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

## Result summaries

### Current behavior

- Each result displays its name, category, address, straight-line distance from the selected location, and provider attribution.
- FoodFind calculates distance locally from the search origin and provider-supplied result coordinates; it does not make a routing request.
- Google business status is normalized into provider-independent operational, temporarily closed, or permanently closed values.
- The search use case removes explicitly temporary and permanent closures before results reach the API or browser.
- Missing business status does not prove closure, so the result remains visible with the message: “Operational status unconfirmed. Call to confirm before visiting.”
- An operational business is not labelled “open now” because business status is not the same as current opening hours.
- Missing category, address, or distance values are identified as unavailable instead of guessed.
- The nearby-search field mask remains in Google's Pro tier. Rating and current opening hours are deferred to the on-demand detail request in Step 5 instead of raising every nearby search to the Enterprise tier.
- The first result page may request only useful fields that keep Nearby Search in the Pro tier. It does not request every Pro field merely because the field is available.
- Enterprise fields are fetched only after the user explicitly opens a result.
- Enterprise + Atmosphere service fields, including dine-in and takeout, are deferred until their Phase 3 filters are implemented.
- Each result has a **View details** control. Opening it requests only that place's rating, rating count, current opening hours and open status, phone, and website.
- A fetched detail response is cached in browser memory while the current result list remains rendered. Closing and reopening the same result does not make another request; changing the search clears the cache and aborts in-flight detail requests.
- Ratings identify their provider, current open status remains distinct from operational business status, and unavailable detail values are labelled instead of inferred.
- A detail failure stays within the opened card and offers a retry without removing the search results.
- For an unconfirmed business with an available phone number, the details include a **Call to confirm** `tel:` action and an optional **Show number** control.
- Available phone numbers are callable through `tel:` links. The action reads **Call to confirm** when operational status is unknown and **Call** otherwise.
- The full phone number is hidden by default to keep the actions concise. **Show number** reveals a plain, copyable value and changes to **Hide number**; toggling it does not make a provider request.
- Available `http:` or `https:` websites appear as a concise **Visit website** link and open in a new browser tab; the full provider URL is not displayed. Other URI schemes are not turned into links.
- Every result with a usable destination has a **Get directions** action. It opens a universal Google Maps directions URL using the result coordinates and, for Google results, the Google place ID for more precise matching.
- The directions link omits an origin so Google Maps can use the device's relevant starting location or ask the user for one. It does not force a travel mode.
- Creating or opening an action does not call a FoodFind API endpoint or add another Google Places request.

### Acceptance criteria

- Distance is calculated from the immutable selected-location snapshot used for the search.
- Provider adapters return normalized closure status rather than Google-specific status strings.
- Explicitly temporary and permanently closed places do not reach the result cards.
- Missing status produces an operational-status warning without treating the place as closed.
- An unconfirmed place with an available phone number has a **Call to confirm** action and an on-demand copyable number.
- On supported phones, the `tel:` link opens the dialer with the number populated; FoodFind does not claim that a browser can bypass the device's final call confirmation.
- Selecting **Show number** reveals the already-fetched value without another detail request and **Hide number** conceals it again.
- Provider attribution remains visible on every result.
- Adding summary information does not create another Google request.
- Loading the first result list never requests an Enterprise or Enterprise + Atmosphere field.
- Opening one result produces at most one on-demand Enterprise detail request for that selected place, not one request for every search result.
- Loading or reloading the page and rendering search summaries produce zero place-detail requests.
- The place-detail endpoint and response use `Cache-Control: no-store`, and the API key remains only in the server-to-Google header.
- Phone links contain only a sanitized dialable value, and unsupported website URI schemes are never assigned to link destinations.
- Website and Google Maps links that open a new tab use `noopener noreferrer`.
- A Google Maps directions URL includes `api=1`, an encoded destination, and the Google place ID when the result came from Google.
- Rendering website, phone, or directions actions does not increase the place-provider call count.
- Automated tests verify field mapping, distance calculation, API output, and missing-field text without calling Google.

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
