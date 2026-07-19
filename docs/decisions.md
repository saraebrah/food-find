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

The default first result page uses only the useful fields required for its summaries and keeps the nearby-search field mask within **Nearby Search Pro**. Pro availability alone is not a reason to request or display a field. An active Enterprise search filter may conditionally add only the field it requires.

Rating, rating count, current opening hours, phone, and website are requested through **Place Details Enterprise** when a user explicitly opens a result. Opening one result does not trigger detail requests for the other results. Separately, an active Open now filter conditionally requests current opening hours in its single Nearby Search request.

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

`SearchPlaces` receives this object inside `SearchCriteria` and passes its coordinates to the existing `PlaceProvider`. Phase 3 Step 2 replaces the earlier fixed restaurant-and-café constraint with the normalized editable place-type filter documented below.

For Step 1A, the browser accepts decimal coordinates and sends the normalized label, latitude, and longitude to `POST /api/places/search`. The API validates finite values and coordinate ranges with a Pydantic boundary model before constructing the domain object.

The previous `SearchFixedTorontoPlaces` class remains as a compatibility wrapper around `SearchPlaces`; the active web route no longer depends on fixed Toronto constants.

### Rationale

- Address suggestions, coordinates, map clicks, and current location can all converge on one domain format.
- The search use case does not need to know how the location was obtained.
- Backend validation remains authoritative even though the browser also provides immediate input guidance.
- Snapshotting and disabling the field during a request prevents lifecycle inconsistencies between the searched coordinates and visible input.

## Phase 1 browser interface

- **Date:** 2026-07-11
- **Status:** Superseded by the SvelteKit frontend transition on 2026-07-18

### Decision

The first result list uses the existing server-rendered page plus a small deferred JavaScript file. The script calls the fixed search endpoint only from the **Search Toronto** click handler and renders the returned normalized places with DOM APIs.

SvelteKit and the TypeScript frontend build system are deferred until the interface needs reusable controls and richer client state. This is not a change to the preferred frontend stack; it keeps the Phase 1 data-flow proof focused and avoids introducing a second application structure solely for one button and list.

### Safeguards

- Script initialization makes no API request.
- The search button is disabled while a request is active.
- Provider strings are assigned with `textContent`, not inserted as HTML.
- A page reload returns to the initial state and does not repeat the previous search.
- Automated backend and page tests continue to use fake or mocked providers.

## SvelteKit frontend transition

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

Phase 3 begins by moving the active browser interface into a TypeScript frontend under `frontend/`, using Svelte 5 and SvelteKit. FastAPI remains the server-side API and the existing Python domain, application, provider, and route code does not change for this transition.

The Svelte frontend preserves the completed Phase 2 behavior while separating it into focused pieces:

- typed API request functions and provider-independent browser models
- a location picker responsible for coordinate entry, debounced suggestions, and suggestion resolution
- one page-level search lifecycle that snapshots the selected location and radius only after an explicit **Search** action
- result cards that own their on-demand detail state and cache one successful detail response while the card remains rendered

During local development, SvelteKit runs on port `5173` and proxies `/api` requests to FastAPI on port `8000`. This keeps browser requests same-origin from the frontend's perspective and keeps the Google API key entirely inside the Python server. The static adapter also produces a production build, but deployment and static-file serving are not being coupled into FastAPI during this transition.

The previous Jinja template, CSS, and JavaScript remain temporarily as a fallback rather than being deleted during the migration. New product UI work belongs in the Svelte frontend.

### Request safeguards

- Rendering or reloading the Svelte page makes no location, nearby-search, or detail request.
- Editing coordinates or changing radius clears stale results but does not search.
- Autocomplete is debounced, aborts superseded requests, and ignores stale responses.
- Each explicit search receives one immutable criteria snapshot and creates one nearby-search request.
- Opening one result creates at most one successful detail request while that result card remains rendered; hide and reopen reuse it.
- Vitest component tests and Playwright end-to-end tests mock FoodFind API responses and do not call Google.

### Rationale

- Phase 3 will introduce enough reusable controls and shared browser state to justify the preferred SvelteKit stack.
- Keeping FastAPI as an API boundary avoids rewriting working backend behavior as part of a frontend migration.
- Component boundaries make later filters, sorting, smart-search criteria, and map selection easier to add without replacing the Phase 2 request flow.
- Preserving the old interface until parity is verified gives the project a simple fallback without maintaining it as the active path.

### Known transition limitation

As of 2026-07-18, `npm audit` reports one low-severity advisory in the transitive `cookie` package used by the current SvelteKit `2.70.0` toolchain. There are no moderate, high, or critical findings. npm's displayed automatic fix would replace current packages with incompatible pre-release versions, so FoodFind will not use `npm audit fix --force`; the dependency should be updated normally when SvelteKit publishes a compatible resolution. The current frontend is statically built and does not use SvelteKit server cookies.

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
- a normalized `SearchFilters` value
- a normalized `SearchSort` value

The browser offers 500 m, 1 km, 2 km, and 5 km presets. The API accepts and validates values from 100 m through 50,000 m, while the application use case passes the chosen value through the existing provider port without modification.

Phase 3 Step 1 established the filter and sorting contract with an initially empty filter object and `provider_default` sorting. The completed Pro and Enterprise groups extend that object with normalized place types, cuisines, common foods, Open now, minimum rating, distance sorting, and rating sorting. Svelte owns these values alongside location and radius, sends all four top-level values in one request snapshot, and FastAPI converts them into the corresponding domain objects.

The filter request model forbids unknown fields, and the sort enum accepts only `provider_default`, `distance`, and `rating`. A future filter or sort option becomes valid only when its roadmap step adds it deliberately across the browser, API, and application. Older callers that omit the new fields receive the same defaults for compatibility.

Changing the radius clears the visible result state but does not search. When the user explicitly starts a search, the browser snapshots the current location, radius, filters, and sorting state and disables the controls until the request completes.

### Rationale

- Later manual filters and smart-search interpretation can extend one normalized search object instead of adding unrelated function arguments.
- An always-present filter container and sort value avoid changing the top-level search contract for every future control.
- Strict boundary validation prevents unsupported criteria from being silently accepted or misrepresented as active.
- The API boundary remains authoritative even though the current UI exposes only valid presets.
- Snapshotting the controls prevents a request from displaying results under a location or radius that changed while it was running.
- Keeping the provider port in metres avoids UI-label and unit-conversion concerns inside provider adapters.

## Place-type filter

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

FoodFind's first editable filter supports four provider-independent `PlaceType` values:

- `restaurant`
- `cafe`
- `bar`
- `bakery`

Restaurant and café remain selected by default, preserving the earlier search behavior. Users may select any non-empty combination. Checkbox changes clear results from the old criteria but do not search; the next explicit **Search** action snapshots the ordered selection with the other criteria.

The FastAPI boundary accepts one to four unique supported values and rejects empty, duplicate, or unknown types with HTTP `422`. The application passes the normalized enum values through the `PlaceProvider` port. The Google adapter alone maps them to Google's identically named Nearby Search `includedTypes` values.

Google applies `includedTypes` during Nearby Search and returns places matching at least one selected type. This needs no new response field, client-side missing-data policy, or additional provider request. The existing field mask remains unchanged and therefore remains in Nearby Search Pro.

Google's current Nearby Search type table does not contain a generic `food_truck` request type. Food truck remains a product requirement for later provider or Text Search investigation, but it is not approximated with `meal_takeaway`, `food_delivery`, or another category that would misrepresent the user's choice.

### Rationale

- A small FoodFind-owned taxonomy keeps the UI and application independent from raw provider strings.
- Mapping at the adapter boundary lets another provider support the same FoodFind choices differently.
- Provider-side filtering avoids discarding scarce results from Google's maximum result set after the request.
- Keeping the default selection preserves existing behavior while making the constraint visible and editable.
- Deferring food truck is more honest than returning a broader or different business category.

### Current provider references

- Google documents up to 50 type values per Nearby Search restriction and OR behavior within `includedTypes`: [Nearby Search type restrictions](https://developers.google.com/maps/documentation/places/web-service/nearby-search#included-types).
- Restaurant, café, bar, and bakery are current request-filterable Table A values: [Google Place Types](https://developers.google.com/maps/documentation/places/web-service/place-types#table-a).
- Nearby Search billing is controlled by the response field mask; the existing summary mask remains Pro: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).

## Pro cuisine, common-food, and distance filters

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

The completed Pro group adds two small provider-independent specialty taxonomies:

- Cuisine: Chinese, Italian, Persian, Thai, and Indian
- Common food: pizza, burgers, steak, ramen, and kebab

The Google adapter maps those values to current Table A primary types such as `italian_restaurant`, `pizza_restaurant`, and `hamburger_restaurant`. Common-food choices describe the provider's business classification; they do not confirm menu-item availability. Pasta is omitted because Google does not expose a request-filterable pasta type.

Google allows multiple selected values within one positive primary-type restriction, but treats them as OR. Because cuisine and common food are separate FoodFind facets that should not silently become an OR across facets, only one of those groups may be active in a search. The browser disables the inactive group and explains how to switch; the API and domain also reject a conflicting request. Multiple choices within the active group still mean “match any selected choice.”

General place types remain in `includedTypes`; the active cuisine or common-food mapping uses `includedPrimaryTypes`. Google requires a result to satisfy both restriction categories, so a selected specialty also respects the selected kinds of food business.

The sort control supports `provider_default` and `distance`. The Google adapter omits `rankPreference` for provider default, which Google currently ranks by popularity, and sends `DISTANCE` for ascending distance. This remains one Nearby Search request and does not invoke a routing API.

None of these Pro request parameters adds response fields. The default nearby-search field mask remains unchanged in the Pro SKU. Higher-tier filters are governed separately and never become part of the Pro default merely because they have been implemented.

### Rationale

- FoodFind-owned enums prevent raw Google type names from leaking through the domain and browser contract.
- A deliberately small taxonomy avoids offering categories that Google cannot reliably apply.
- Rejecting an ambiguous cross-group combination is more honest than silently widening it to OR behavior.
- Provider-side type filtering and ranking preserve the maximum result set and require no extra request.
- Keeping the field mask unchanged provides a clear billing boundary before Enterprise work begins.

### Current provider references

- Google documents AND behavior across type-restriction categories and OR behavior within an included category: [Nearby Search type restrictions](https://developers.google.com/maps/documentation/places/web-service/nearby-search#included-types).
- The supported cuisine and common-food mappings are request-filterable Table A types: [Google Place Types](https://developers.google.com/maps/documentation/places/web-service/place-types#table-a).
- Google documents `POPULARITY` as the omitted/default ranking and `DISTANCE` as ascending distance: [Nearby Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby).
- Billing is controlled by requested response fields; the existing summary mask remains within Nearby Search Pro: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).

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

Phase 3 filter work is grouped by the highest Nearby Search billing tier required:

1. **Pro:** place type, cuisine, supported common food, and distance sorting
2. **Enterprise:** open now, minimum rating, and rating sorting
3. **Enterprise + Atmosphere:** dine-in and takeout

FoodFind pauses for review after each group. Completing a group does not automatically authorize starting the next billing tier.

Cuisine and supported common-food choices can be represented by Google request-filterable place types. Distance ordering is available through Nearby Search's `DISTANCE` rank preference. These request parameters do not require adding response fields, so the existing Pro field mask remains unchanged.

Nearby Search does not provide an `openNow` request parameter. Open now therefore needs `currentOpeningHours`; minimum-rating filtering and rating ordering need `rating`. Each completed Enterprise filter requests only its required response field when active. Dine-in and takeout require Enterprise + Atmosphere response fields and remain in the final group.

The Enterprise implementation must use one conditional Nearby Search request rather than fetching Place Details separately for every returned result. Missing-data behavior must be agreed and documented before each Enterprise or Enterprise + Atmosphere filter is implemented.

### Billing-group references

- Nearby Search supports type restrictions and `DISTANCE` or `POPULARITY` rank preference as request parameters: [Nearby Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby).
- Google lists request-filterable cuisine and food categories in its current Table A: [Google Place Types](https://developers.google.com/maps/documentation/places/web-service/place-types#table-a).
- Google classifies `currentOpeningHours` and `rating` as Nearby Search Enterprise fields and `dineIn` and `takeout` as Enterprise + Atmosphere fields: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).

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

## Open-now filter

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

`SearchFilters.open_now` is false by default. Changing it clears stale browser results but does not search. The next explicit search snapshots the value with the other criteria.

When false, the Google adapter uses the unchanged Pro field mask and the normalized place value is unknown. When true, the adapter adds only `places.currentOpeningHours` to the same Nearby Search request, making that request Enterprise, and maps `currentOpeningHours.openNow` to the provider-independent `Place.open_now` value.

Nearby Search does not accept an Open now request parameter. The application therefore filters Google's returned candidates after the single provider request. Only `open_now is True` satisfies the filter; false or missing data is excluded because FoodFind cannot claim an unknown place is currently open. Explicitly temporary and permanently closed businesses remain excluded independently of current hours.

Google returns at most 20 Nearby Search candidates before this application-side filter runs. The filtered list can therefore be short and is not guaranteed to include every open place in the radius. FoodFind does not issue additional searches or one detail request per candidate to fill the list.

Results retained by the filter carry `open_now=true` in the normalized summary and display an **Open now** tag without another request. The existing on-demand detail behavior remains available and unchanged.

### Rationale

- Conditional field masks keep ordinary searches at Pro and make the billing-tier change directly traceable to the active filter.
- Requiring an explicit true value gives the filter honest semantics when provider data is missing.
- One Nearby Search request preserves the project's request and cost safeguards.
- Domain-level filtering keeps the rule independent from Google's response shape and reusable by another provider.

### Current provider references

- Google's Nearby Search request schema contains no `openNow` filter and returns at most 20 candidates: [Nearby Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby).
- Google classifies `places.currentOpeningHours` as a Nearby Search Enterprise field: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).

## Enterprise rating filters

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

FoodFind supports four provider-independent minimum-rating thresholds: 3.0, 3.5, 4.0, and 4.5. No minimum is the default. The API rejects any other threshold instead of accepting a value the browser cannot represent.

A selected minimum keeps only places whose normalized rating is greater than or equal to the threshold. A missing rating does not satisfy a minimum because FoodFind cannot prove the place meets it.

`SearchSort.RATING` orders ratings highest-first. Places with missing ratings remain in the result set when no minimum is active and are placed last. Python's stable sort preserves Google's relative order for equal ratings and among missing ratings.

Nearby Search supports only popularity and distance ranking, so FoodFind does not send rating as a Google `rankPreference`. If a minimum rating or rating sorting is active, the adapter adds only `places.rating` to the field mask and maps it into `Place.rating`. If both are active, the field is added once. If Open now is also active, both Enterprise fields are added once to the same request.

Minimum rating and rating sorting operate on the maximum 20 candidates Google returns. A minimum may shorten the visible list, and rating sorting ranks only that candidate set; FoodFind does not make additional searches or per-result detail calls to fill or reorder a wider set.

When present, the summary displays the already-returned rating with Google Maps attribution. Default Pro searches do not request rating and do not display a summary rating.

### Rationale

- Half-star thresholds give useful control without implying precision beyond the product's simple UI.
- Strict allowed values keep browser, API, and domain behavior identical.
- Excluding missing values from a minimum filter is more honest than treating unknown as sufficient.
- Keeping missing values last during sorting avoids discarding otherwise useful places.
- Conditional field masking maintains the Pro default and avoids redundant Enterprise fields or provider calls.

### Current provider references

- Google classifies `places.rating` as a Nearby Search Enterprise field: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).
- Google's Nearby Search request supports only popularity and distance ranking and returns at most 20 candidates: [Nearby Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby).

## Enterprise + Atmosphere service filters

- **Date:** 2026-07-18
- **Status:** Current approach

### Decision

FoodFind supports independent Dine-in and Takeout filters. Both default to false. Changing either control clears stale results but does not search; the next explicit search snapshots both values with the other criteria.

The Google adapter adds `places.dineIn` only when Dine-in is active and `places.takeout` only when Takeout is active. Selecting both adds both fields once to the same Nearby Search request. With neither selected, both fields are absent, so these controls do not make an ordinary Pro or Enterprise search use the Enterprise + Atmosphere SKU.

Nearby Search has no request parameter for these services. FoodFind filters Google's returned candidates in the application layer. Only an explicit true value satisfies an active service filter; false or missing data is excluded because FoodFind cannot confirm that the place offers the requested service. When both filters are active, a place must explicitly support both.

The filters operate on the maximum 20 candidates Google returns. The visible result count can therefore be short, and FoodFind does not issue additional searches or per-place detail requests to fill the list. The normalized service values support filtering but are not added as result-card claims.

### Rationale

- Conditional field masks keep Enterprise + Atmosphere billing directly tied to an active service filter.
- Independent booleans allow either service or both without introducing a provider-specific filter model.
- Requiring explicit true values avoids presenting missing provider data as confirmed service availability.
- One provider request preserves the established lifecycle and cost safeguards.
- Application-layer filtering remains independent of Google's response shape and can be reused with another provider.

### Current provider references

- Google classifies `places.dineIn` and `places.takeout` as Nearby Search Enterprise + Atmosphere fields: [Nearby Search field masks](https://developers.google.com/maps/documentation/places/web-service/nearby-search#fieldmask).
- Google's Nearby Search request schema has no dine-in or takeout filter parameter and returns at most 20 candidates: [Nearby Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby).
