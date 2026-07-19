# Features

This file breaks the product into individual features, including expected behavior, edge cases, acceptance criteria, and implementation notes.

## Nearby place search

### Current behavior

- `POST /api/places/search` accepts one normalized selected location containing a label, latitude, and longitude.
- Users choose a radius of 500 m, 1 km, 2 km, or 5 km; 1 km is the default.
- Users can search for any combination of the supported place types: restaurant, café, bar, and bakery. Restaurant and café are selected by default.
- Users can optionally choose supported cuisines or supported common-food business categories, but not both groups in one search.
- Users can optionally keep only places that Google explicitly reports open at search time.
- Users can preserve Google's recommended order, order results by distance, or order Google's candidate set by rating.
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
- The selected coordinates, radius, normalized filters, and sort are passed into the generalized application use case.
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

## Filter and sorting state

### Current behavior

- Every Svelte search snapshot contains `filters` and `sort` alongside location and radius.
- The filter state contains ordered `place_types`, `cuisines`, and `common_foods` lists. Restaurant and café are the default place types; both specialty lists default to empty.
- The `open_now` filter defaults to false.
- The `minimum_rating` filter defaults to no minimum and offers 3.0+, 3.5+, 4.0+, and 4.5+.
- The `dine_in` and `takeout` service filters are independent and default to false.
- Users can choose Google's recommended order (`provider_default`), ascending distance (`distance`), or highest rating first (`rating`).
- FastAPI converts both values into FoodFind-owned `SearchFilters` and `SearchSort` domain values before the application use case runs.
- Omitting the fields retains the same defaults for older callers.
- The place-type control supports restaurant, café, bar, and bakery as independent checkboxes. At least one must be selected before searching.
- The cuisine control supports Chinese, Italian, Persian, Thai, and Indian. Multiple selections match any selected cuisine.
- The common-food control supports pizza, burgers, steak, ramen, and kebab. These identify Google's business category and do not claim that a specific item is currently on the menu.
- Cuisine and common-food selections cannot be combined. Selecting from one group disables the other until the active group is cleared because Google represents both through one positive primary-type restriction whose selected values use OR behavior.
- Changing any filter or the sort clears stale results and displays guidance but does not search automatically.
- The selected FoodFind types are mapped by the Google adapter to Nearby Search `includedTypes`. A place can match any selected type; no result-side filtering or additional detail request is needed.
- Selected cuisines or common foods are mapped to `includedPrimaryTypes`. When combined with place types, Google requires a result to satisfy both restriction categories.
- Distance sorting maps to Google's `DISTANCE` rank preference. Recommended ordering omits that parameter and retains Google's default popularity ranking.
- Place type, cuisine, common-food, and distance controls do not add response fields or change the Nearby Search Pro field mask.
- When Open now is active, the Google adapter adds only `places.currentOpeningHours` to that search's field mask. This makes that Nearby Search request Enterprise without changing the default request.
- Nearby Search has no Open now request parameter. FoodFind therefore keeps only candidates whose normalized `open_now` value is explicitly true; false and missing values do not satisfy the filter.
- When a minimum rating is selected or rating sorting is active, the Google adapter adds only `places.rating` to the conditional Enterprise field mask.
- A selected minimum keeps ratings greater than or equal to its threshold. A missing rating does not satisfy a minimum.
- Rating sorting is applied highest-first after Google returns its candidates. Missing ratings remain available when no minimum is active and appear last; equal ratings preserve Google's relative order.
- When Dine-in is selected, the Google adapter adds only `places.dineIn`; when Takeout is selected, it adds only `places.takeout`. Either field makes that one search Enterprise + Atmosphere. Inactive service filters add neither field.
- Nearby Search has no request parameter for either service. FoodFind therefore retains only places whose normalized value is explicitly true for every selected service; false and missing values do not satisfy the filter.
- Google returns at most 20 Nearby Search candidates before FoodFind applies Open now, minimum rating, Dine-in, Takeout, or rating sorting. Filtering may produce fewer results, and rating sorting ranks only that candidate set.
- A retained result displays an **Open now** tag using the value already returned by the search. Rendering the tag makes no extra request.
- A returned summary rating is labelled as a Google Maps rating and displayed without an extra detail request.
- A generic food-truck type is not currently available as a Google Nearby Search type. Food truck is not shown as a supported filter and is deferred rather than mapped to an inaccurate substitute.
- Pasta is not shown as a common-food filter because Google has no request-filterable pasta place type.
- Unknown filter properties, unsupported values, duplicate selections, an empty place-type list, conflicting specialty groups, and unsupported sort values are rejected with HTTP `422`; they are not silently ignored.

### Acceptance criteria

- One explicit search snapshots location, radius, filters, and sort exactly once.
- The browser, API boundary, and application share the same normalized meaning for the state.
- Rendering, editing criteria, or constructing default state makes no provider request.
- Unsupported criteria cannot appear to be active while having no effect.
- Adding a later filter extends the existing filter object rather than adding an unrelated top-level request parameter.
- The initial browser state selects restaurant and café and makes no request.
- Selecting or clearing a checkbox makes no provider request and removes results from the previous criteria.
- One explicit search sends the complete normalized criteria and produces one Nearby Search request.
- Multiple cuisines or multiple common-food choices use OR behavior within their own group.
- General place types and the active specialty group use AND behavior between groups.
- Cuisine and common-food choices can never appear active together in either a valid browser or API state.
- Choosing distance changes provider ranking without making an extra request or adding a routing request.
- The Google request field mask is unchanged when any Pro filter or sort changes.
- Changing Open now makes no request until the user explicitly searches.
- A default search omits `places.currentOpeningHours` and remains Pro.
- An Open now search adds only `places.currentOpeningHours`, makes one Enterprise Nearby Search request, and returns only places whose value is true.
- A place with false or missing current-opening-hours data does not satisfy Open now.
- Selecting a minimum rating or rating sorting adds only `places.rating` to the search field mask and makes no extra request.
- Supported minimum ratings are exactly 3.0, 3.5, 4.0, and 4.5; unsupported thresholds return HTTP `422`.
- A missing rating is excluded by a minimum filter but retained at the end of rating-sorted results when no minimum is active.
- Rating sorting is descending and stable for equal values.
- Combining multiple Enterprise filters adds each required field once to the same Nearby Search request.
- Changing Dine-in or Takeout makes no request until the user explicitly searches.
- A search with neither service selected omits `places.dineIn` and `places.takeout`; it does not become Enterprise + Atmosphere.
- Selecting Dine-in or Takeout adds only the corresponding field to the same Nearby Search request. Selecting both adds each field once and still produces one request.
- A place with a false or missing service value does not satisfy that active service filter.

## Result summaries

### Current behavior

- Each result displays its name, category, address, straight-line distance from the selected location, and provider attribution.
- FoodFind calculates distance locally from the search origin and provider-supplied result coordinates; it does not make a routing request.
- Google business status is normalized into provider-independent operational, temporarily closed, or permanently closed values.
- The search use case removes explicitly temporary and permanent closures before results reach the API or browser.
- Missing business status does not prove closure, so the result remains visible with the message: “Operational status unconfirmed. Call to confirm before visiting.”
- An operational business is not labelled “open now” because business status is not the same as current opening hours.
- Missing category, address, or distance values are identified as unavailable instead of guessed.
- The default nearby-search field mask remains in Google's Pro tier. An Open now search conditionally adds current opening hours and becomes Enterprise.
- Minimum rating and rating sorting conditionally add rating and make that search Enterprise.
- A default first result page requests only useful fields that keep Nearby Search in the Pro tier. An active Enterprise search filter may add only the field it requires.
- When no Enterprise search filter is active, Enterprise fields are fetched only after the user explicitly opens a result. Enterprise search filters request only their required fields conditionally.
- Dine-in and takeout are requested only when their corresponding Phase 3 filter is active. They are not displayed as extra result-summary data.
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
- Loading a default first result list requests no Enterprise or Enterprise + Atmosphere field. Active Enterprise filters conditionally request only current opening hours and/or rating; active service filters conditionally request only dine-in and/or takeout.
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
