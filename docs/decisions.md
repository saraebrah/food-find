# Decisions

This file records important product, design, and technical decisions made during the project, including the reason behind each decision.

## Place data storage strategy

- **Date:** 2026-06-29
- **Status:** Current approach; revisit if the project's needs change

### Decision

For now, FoodFind will not create a permanent database by copying business content from a place-data provider.

The initial implementation will:

- Retrieve current business information from the selected provider when a user searches or opens a place.
- Access providers through a FoodFind-owned place-provider interface so that Google, Yelp, Foursquare, or another provider can be replaced without changing the core search logic.
- Normalize provider responses in memory into FoodFind's internal place model.
- Use short-lived caching only when the provider's current terms explicitly permit it.
- Store provider name and provider place ID when permitted, rather than permanently storing the provider's full business record.
- Store FoodFind-owned data, such as user favourites and application state, separately from provider-owned content.
- Keep source attribution on ratings and other provider-derived fields.
- Prevent provider responses from being retained unintentionally in logs, traces, analytics, CDN caches, or error-reporting systems.

Provider-specific cache lifetimes and storage permissions must be configuration and policy, not assumptions embedded in domain logic.

### Initial request flow

```text
Browser
   ↓
FoodFind backend
   ↓
Compliant short-lived cache
   ↓ cache miss
Place-provider adapter
   ↓
Selected place-data API
```

### Future option

FoodFind may later maintain a permanent base place database using an open dataset such as Overture Maps. Other providers could then supply current ratings, hours, service options, or photos when needed.

Provider content should only be copied into the base record when that provider permits it. Keep the source of each external field so its rules remain clear.

### Rationale

- Current business information is better retrieved from its authoritative provider than synchronized into another database.
- Avoiding permanent copies keeps the first implementation simpler and reduces stale data.
- A short-lived cache can control latency, API cost, and rate-limit exposure without assuming permanent storage rights.
- A provider interface keeps domain and search behavior independent from a specific vendor.
- Open data remains available later if owning and operating a place database becomes strategically useful.

### Tradeoffs

- Search and place-detail availability depend on the selected provider.
- Live retrieval increases latency, API usage costs, and rate-limit exposure.
- Stored favourites may require a provider call before their current details can be displayed.
- Combining providers later will require entity matching, deduplication, attribution, and field-level provenance.

### Current policy examples

- Google generally restricts prefetching, caching, and storing Places content, while allowing Place IDs to be stored indefinitely: [Google Places policies](https://developers.google.com/maps/documentation/places/web-service/policies).
- Yelp currently permits Places content to be cached for up to 24 hours and Yelp Business IDs to be stored indefinitely: [Yelp Places FAQ](https://docs.developer.yelp.com/docs/places-faq).
- Overture distributes downloadable place data under source-specific open licences and attribution requirements: [Overture attribution and licensing](https://docs.overturemaps.org/attribution/).

These examples can change. Check the selected provider's current storage and display rules when implementing its adapter.

## Initial place-data provider

- **Date:** 2026-07-04
- **Status:** Current approach

### Decision

FoodFind will use Google Places as its first place-data provider.

The integration must follow these safeguards:

- Automated tests use mocked Google responses and never call the live API.
- Page loads use one explicit search operation and must not create request loops.
- The Google API key remains in a server-only environment variable and is never included in browser code or responses.
- The Google API key must be restricted to **Places API** and **Places API (New)** in Google Cloud.
- A low daily request quota is preferred before broader live development calls begin.
- If quota controls are unavailable during the Google Cloud free trial, live calls must stay manual and sparse, with billing alert monitoring.

The current Google Cloud setup uses API restrictions for **Places API** and **Places API (New)** because the key is used server-side in Python and there may not be a fixed server IP during local development. The current budget alert is `$2/month`. This is acceptable for local development, but it is weaker than a hard daily quota because a budget alert warns about spend rather than stopping requests.

### Rationale

Google Places supplies the basic place fields needed for the first version, and expected development usage should remain within its monthly free allowance. The existing provider interface decision keeps the application replaceable if that changes.

## Internal place model and provider port

- **Date:** 2026-07-11
- **Status:** Current approach

### Decision

Provider adapters return FoodFind-owned `Place` objects through the `PlaceProvider` port. The internal model currently contains:

- provider name and provider place ID
- business name
- provider-supplied category label and category code
- address
- coordinates
- normalized business status
- straight-line distance from the selected search location, when attached by the search use case

Google response models remain inside the Google adapter and are converted to the internal model before results leave that boundary. Optional provider fields remain `None` when unavailable instead of being inferred.

Category labels and codes are still provider-supplied at this stage. A shared FoodFind category taxonomy will be introduced only when manual place-type filtering requires one.

### Rationale

- Application code can search for places without depending on Google's response schema.
- Another provider can implement the same port and return the same internal model.
- Immutable domain objects make one normalized provider response a stable snapshot for later application and display steps.
- Delaying a shared category taxonomy avoids inventing filtering behavior before that feature is built.

## Nearby summary fields and on-demand details

- **Date:** 2026-07-15
- **Status:** Current approach

### Decision

Nearby-search result summaries contain name, category, address, straight-line distance, and provider attribution. Google supplies the place fields in the existing nearby-search request, while `SearchPlaces` calculates distance locally from the selected-location snapshot and result coordinates.

The first result page uses only the useful fields required for its summaries and keeps the nearby-search field mask within **Nearby Search Pro**. Pro availability alone is not a reason to request or display a field.

Rating, rating count, current opening hours, phone, and website are requested through **Place Details Enterprise** only when a user explicitly opens a result. Opening one result does not trigger detail requests for the other results.

The detail adapter requests only `id`, `rating`, `userRatingCount`, `currentOpeningHours`, `regularOpeningHours`, `nationalPhoneNumber`, `internationalPhoneNumber`, and `websiteUri`. It prefers the current seven-day hours, uses regular hours only as a fallback, and maps the response into FoodFind's provider-independent `PlaceDetails` model.

The browser caches successful details only while the current result list is rendered. Closing and reopening a result reuses that response. A location/radius change or new search clears the browser cache and aborts any in-flight detail request. Detail API responses use `Cache-Control: no-store`; FoodFind does not add permanent provider-data storage.

Service options such as dine-in, takeout, and delivery require **Enterprise + Atmosphere** fields. They are deferred until the relevant Phase 3 filters are implemented and are not part of the Phase 2 detail request.

`businessStatus` is normalized at the adapter boundary. `SearchPlaces` excludes businesses explicitly reported temporarily or permanently closed. A missing status does not prove closure, so the place remains in results with an operational-status warning. `OPERATIONAL` means the business has not been reported closed; it must not be presented as “open now.” Current open status requires opening-hours data.

When details are retrieved for a place whose operational status is unconfirmed, FoodFind shows a **Call to confirm** action. Other places use **Call**. The full number is hidden by default but can be revealed as plain, copyable text with **Show number** and concealed again with **Hide number**. Revealing it is entirely a browser display change over the already-fetched details and creates no provider request.

The call action uses a `tel:` link so supported phones and configured desktop calling applications can handle it. The link can populate a device's dialer, but a web page cannot bypass the operating system's final confirmation and place a telephone call automatically.

Result actions are browser links rather than additional provider operations:

- Phone links use a sanitized `tel:` value. The provider-supplied display number is available through an explicit show/hide control rather than occupying space by default.
- Website values become links only when they use the `http:` or `https:` scheme. They open in a separate tab with `noopener noreferrer`.
- Directions use `https://www.google.com/maps/dir/?api=1` with the result coordinates as the destination. Google results also include their Google place ID to identify the establishment precisely; a future non-Google result can still use its coordinates without mislabelling another provider's ID as a Google ID.
- The directions URL omits origin and travel mode so Google Maps can use or request the user's starting point and offer relevant travel choices.

Google Maps URLs do not require an API key and do not create another Places API request. FoodFind therefore does not request Google's `googleMapsLinks` field solely to implement directions.

### Rationale

- Result summaries become useful without creating another provider call.
- Keeping the first page within Pro preserves its larger free monthly allowance and lower paid rate.
- Fetching Enterprise details on demand aligns provider cost with demonstrated user interest.
- Calculated straight-line distance is provider-independent and can support later distance sorting.
- Filtering normalized closure values in the application layer gives every future provider the same result policy.
- Retaining unknown-status places avoids treating missing provider data as evidence that a business is closed.
- On-demand details limit latency, response size, and use of Google's higher billing tier.
- A later provider can map its closure values into the same FoodFind status values.
- Link actions reuse already-available summary or detail values and do not increase provider cost.

### Current provider references

- Google lists name, address, coordinates, and `businessStatus` in the Nearby Search Pro field group: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search).
- Google lists rating and opening-hours fields in the Nearby Search Enterprise field group: [Place data fields](https://developers.google.com/maps/documentation/places/web-service/data-fields).
- Google lists dine-in, takeout, delivery, and similar service options in the Enterprise + Atmosphere field group: [Place data fields](https://developers.google.com/maps/documentation/places/web-service/data-fields).
- Google documents cross-platform directions URLs and confirms that Maps URLs do not require an API key: [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started).

## Fixed Toronto search lifecycle

- **Date:** 2026-07-11
- **Status:** Superseded by the normalized selected-location search on 2026-07-12

### Decision

The first application search uses Toronto City Hall (`43.6532`, `-79.3832`), a 1,000-metre radius, and the provider types `restaurant` and `cafe`.

The search is exposed as `POST /api/places/search`. Normal page loads do not invoke the endpoint or construct the Google provider. Each endpoint request creates a server-side provider dependency, executes the application use case once, and returns normalized places.

The page will call this endpoint only after a deliberate user action in the next Phase 1 task. Because the search is not tied to page loading, refreshing the page cannot start a request loop or repeat a previous POST.

### Rationale

- Fixed criteria prove the application flow before location and radius controls are introduced.
- A `POST` endpoint represents an explicit operation and is not fetched as a page resource.
- Dependency injection lets automated tests substitute a fake provider without loading the API key or contacting Google.
- Keeping the coordinates and radius in one application use case prevents different entry points from using different fixed search state.

## Normalized selected location and generalized search

- **Date:** 2026-07-12
- **Status:** Current approach

### Decision

Every location input method will produce a FoodFind-owned `SelectedLocation` containing:

- a visible label
- coordinates
- optional provider name and provider place ID

`SearchPlaces` receives this object inside `SearchCriteria` and passes its coordinates to the existing `PlaceProvider`. The place types remain `restaurant` and `cafe` until their later roadmap step.

For Step 1A, the browser accepts decimal coordinates and sends the normalized label, latitude, and longitude to `POST /api/places/search`. The API validates finite values and coordinate ranges with a Pydantic boundary model before constructing the domain object.

The previous `SearchFixedTorontoPlaces` class remains as a compatibility wrapper around `SearchPlaces`; the active web route no longer depends on fixed Toronto constants.

### Rationale

- Address suggestions, coordinates, map clicks, and current location can all converge on one domain format.
- The search use case does not need to know how the location was obtained.
- Backend validation remains authoritative even though the browser also provides immediate input guidance.
- Snapshotting and disabling the field during a request prevents lifecycle inconsistencies between the searched coordinates and visible input.

## Phase 1 browser interface

- **Date:** 2026-07-11
- **Status:** Temporary Phase 1 approach

### Decision

The first result list uses the existing server-rendered page plus a small deferred JavaScript file. The script calls the fixed search endpoint only from the **Search Toronto** click handler and renders the returned normalized places with DOM APIs.

SvelteKit and the TypeScript frontend build system are deferred until the interface needs reusable controls and richer client state. This is not a change to the preferred frontend stack; it keeps the Phase 1 data-flow proof focused and avoids introducing a second application structure solely for one button and list.

### Safeguards

- Script initialization makes no API request.
- The search button is disabled while a request is active.
- Provider strings are assigned with `textContent`, not inserted as HTML.
- A page reload returns to the initial state and does not repeat the previous search.
- Automated backend and page tests continue to use fake or mocked providers.

## Google location autocomplete lifecycle

- **Date:** 2026-07-12
- **Status:** Current approach

### Decision

FoodFind uses server-side **Autocomplete (New)** for place and address suggestions and **Place Details (New)** to resolve a selected prediction into coordinates. Both operations stay behind the FoodFind-owned `LocationProvider` port.

The browser generates a UUIDv4 session token. It reuses that token for debounced autocomplete requests and the single Place Details request that completes the selection, then generates a new token. The API rejects other UUID versions.

Autocomplete begins after three characters and a 350-millisecond debounce. Editing the query aborts the previous browser request. Google requests use a Toronto location bias, Canadian region formatting, and English language preference; the bias influences ordering but does not restrict results to Toronto or Canada.

Place Details requests only `id` and `location`. The selected label comes from the autocomplete prediction, avoiding an unnecessary `displayName` field while retaining the user-visible prediction they selected.

### Provider and privacy safeguards

- API keys remain in server-only headers.
- Browser-to-FoodFind requests use POST bodies rather than putting typed addresses in URLs.
- Autocomplete, resolution, and nearby-search responses use `Cache-Control: no-store`.
- Automated tests replace the location provider or HTTP transport and never call Google.
- Suggestions display visible `Google Maps` text attribution in the same container.
- Google-derived result cards identify their source as `Google Maps`.
- Publicly accessible terms and privacy information incorporating Google's required terms must be added before the project is made available beyond local/private development.

### Rationale

- All input methods still converge on the same `SelectedLocation` domain object.
- Debouncing, cancellation, and explicit selection limit calls and prevent stale suggestions from becoming current state.
- Session tokens group one typing-and-selection interaction for correct Google billing behavior.
- A separate location-provider port keeps autocomplete concerns out of nearby food-place search logic.

## Normalized search criteria and radius

- **Date:** 2026-07-12
- **Status:** Current approach

### Decision

`SearchCriteria` is the application-owned immutable snapshot for one place search. It currently contains:

- the normalized `SelectedLocation`
- radius in metres

The browser offers 500 m, 1 km, 2 km, and 5 km presets. The API accepts and validates values from 100 m through 50,000 m, while the application use case passes the chosen value through the existing provider port without modification.

Changing the radius clears the visible result state but does not search. When the user explicitly starts a search, the browser snapshots the current location and radius and disables both controls until the request completes.

### Rationale

- Later manual filters and smart-search interpretation can extend one normalized search object instead of adding unrelated function arguments.
- The API boundary remains authoritative even though the current UI exposes only valid presets.
- Snapshotting the controls prevents a request from displaying results under a location or radius that changed while it was running.
- Keeping the provider port in metres avoids UI-label and unit-conversion concerns inside provider adapters.

## Provider failure boundary

- **Date:** 2026-07-13
- **Status:** Current approach

### Decision

Google adapters translate transport errors, unsuccessful provider responses, and invalid provider response data into provider-neutral `PlaceProviderError` or `LocationProviderError` exceptions. FastAPI routes convert those exceptions into safe HTTP `502` responses with `Cache-Control: no-store`.

The browser distinguishes invalid input from temporary provider or network failure, clears stale results, and restores disabled controls after each request. This uses direct status updates and one result-clearing helper rather than a separate frontend state-management system.

### Rationale

- Core routes and future provider adapters do not need Google-specific error handling.
- Provider response details are not exposed to the browser.
- The current UI stays simple while giving each operation a predictable recovery path.

## Filters and smart search before the map

- **Date:** 2026-07-15
- **Status:** Current approach

### Decision

After completing basic place discovery, FoodFind will build in this order:

1. Manual filters and sorting
2. Smart search that translates requests into the manual filter state
3. The map experience and device current location together
4. First-version cleanup

Filters will be implemented one at a time. Before adding each one, confirm whether Google supports it, which billing tier its fields require, how missing values behave, and whether it can be applied by Google or only to the returned result set.

Current location remains combined with the map phase. Delaying the map therefore also delays device-location permission, while autocomplete, addresses, and coordinate entry continue to provide working manual location selection.

### Rationale

- Filters determine whether FoodFind can return meaningfully relevant choices and establish the search state that later features need.
- Smart search can reuse the proven filter state instead of creating a parallel search implementation.
- The existing list already provides distance, address, details, calls, websites, and Google Maps directions, so it remains usable without an embedded map.
- Building the map after the search model is stable reduces simultaneous work on provider behavior, client state, and marker/list synchronization.
- Combining map selection and current location completes the spatial experience in one phase while keeping every location source normalized through the same domain model.

### Tradeoffs

- Users will not initially have embedded spatial context or map-based location selection.
- Device current location arrives later because it is grouped with the map.
- Filter implementation may change provider fields and billing tiers before the map work begins.
- Filters and smart search will make the browser state richer, so the project must decide whether to introduce SvelteKit before extending the temporary JavaScript interface substantially.
