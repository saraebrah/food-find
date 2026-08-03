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

When details are retrieved for a place whose operational status is unconfirmed, FoodFind labels the call action **Call to confirm**. Other places use **Call**. The provider-formatted number remains visible and selectable. On hover or keyboard focus, its compact row highlights and reveals call then copy actions. Touch devices keep the actions visible because they have no hover. Copying uses the browser clipboard when available and otherwise leaves the number available for manual copying. Neither action creates a provider request.

The call action uses a `tel:` link so supported phones and configured desktop calling applications can handle it. The link can populate a device's dialer, but a web page cannot bypass the operating system's final confirmation and place a telephone call automatically.

Result actions are browser links rather than additional provider operations:

- Phone links use a sanitized `tel:` value, while the provider-supplied display number remains visible and is the value copied to the clipboard.
- Website values become links only when they use the `http:` or `https:` scheme. The compact details row displays the domain; hover or keyboard focus reveals open then copy actions, while touch devices keep them visible. The domain link and open icon launch the full URL in a separate tab with `noopener noreferrer`; copy uses that full URL.
- Directions use `https://www.google.com/maps/dir/?api=1` with the immutable submitted search-location snapshot as the origin and the result coordinates as the destination. When either endpoint came from Google, its Google place ID is included for precision; coordinates remain the provider-independent fallback.
- Supplying the origin avoids asking Google Maps to infer or request a different starting point. The link does not force a travel mode, so Google Maps can still offer relevant travel choices.

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
- **Status:** Superseded by removal of the filter on 2026-07-26

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

## Remove place type from editable search filters

- **Date:** 2026-07-26
- **Status:** Current

### Decision

Place type is removed from the browser controls, API filter model, domain `SearchFilters`, interpretation capabilities, and Gemini structured output. Location is the only input required before **Search places**; cuisine, common food, availability, rating, service options, smart search, and sorting remain optional.

FoodFind still searches for food businesses. The Google adapter uses the requested cuisine, common food, or free-form dish as the main query when one is present; otherwise it uses a broad fallback covering restaurants, cafés, bars, and bakeries. It defensively removes results whose known Google types fall outside that scope. It does not send `includedType` or expose provider categories as a user filter. Results with missing type data remain visible as unconfirmed.

Requests that still submit the removed `place_types` property receive HTTP `422` rather than having an ignored filter appear active.

### Rationale

- Choosing a broad business type did not provide useful control compared with cuisine, common-food, and smart-search criteria.
- Removing the control makes Location the one clear prerequisite for searching.
- Removing the field end to end prevents smart search from changing an invisible filter.
- Keeping the food-business scope inside the provider adapter preserves FoodFind's purpose without adding user work.

## Pro cuisine, common-food, and distance filters

- **Date:** 2026-07-18
- **Status:** Provider mapping and cuisine/common-food exclusion superseded by Text Search-only discovery on 2026-07-21

### Decision

The completed Pro group adds two small provider-independent specialty taxonomies:

- Cuisine: Chinese, Italian, Persian, Thai, Indian, Mexican, Japanese, Korean, Vietnamese, and Mediterranean
- Common food: pizza, burgers, steak, ramen, kebab, shawarma, ice cream, dessert, sweets, drinks, sushi, tacos, salad, soup, and pasta

The former Nearby Search adapter mapped the original values to Table A primary types such as `italian_restaurant`, `pizza_restaurant`, and `hamburger_restaurant`. The current Text Search adapter instead includes cuisine and common-food terms in `textQuery`, so a match represents provider relevance rather than a required business classification or confirmed menu item.

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

## Expanded cuisine allowlist

- **Date:** 2026-07-26
- **Status:** Current

### Decision

Mexican, Japanese, Korean, Vietnamese, and Mediterranean join the existing Chinese, Italian, Persian, Thai, and Indian cuisine options. Each is a FoodFind-owned enum value represented as natural-language relevance text in Google Text Search. Google currently lists corresponding restaurant types in its request-filterable Food and Drink taxonomy.

Cuisine options remain a reviewed allowlist rather than being downloaded dynamically from Google. Adding one requires coordinated updates to the Python domain enum and provider adapter plus the TypeScript type and visible option list; API validation, Gemini capabilities, field limits, and the search lifecycle derive from those definitions without separate use-case changes.

### Rationale

- A reviewed list keeps the interface manageable and prevents raw provider taxonomy from becoming the product model.
- Explicit cross-layer definitions provide compile-time and boundary validation in both Python and TypeScript.
- The current approach is suitable for a small list. A server-provided capabilities endpoint would be more appropriate if the option catalog becomes large or changes frequently.

## Expanded common-food allowlist

- **Date:** 2026-07-26
- **Status:** Current

### Decision

Shawarma, ice cream, dessert, sweets, drinks, sushi, tacos, salad, soup, and pasta join the existing pizza, burgers, steak, ramen, and kebab options. The interface uses the standard spelling **Shawarma**.

Google's current Food and Drink taxonomy contains direct or closely corresponding types for shawarma, ice cream, dessert, sushi, tacos, salad, and soup. Sweets has related confectionery, candy-store, and dessert types. Generic drinks and pasta have no exact Google place type. All Common food options are therefore sent consistently as natural-language Text Search relevance terms rather than structured provider type filters.

Selecting any Common food option changes relevance only. It does not verify current menu availability, and FoodFind continues to show the agreed check-the-menu-or-call warning.

### Rationale

- One relevance-only behavior keeps exact provider categories and ordinary food terms from appearing more reliable than they are.
- The expanded list supports common discovery language without adding response fields or another Google request.
- Documenting the missing exact types prevents Pasta, Drinks, or Sweets from being mistaken for provider-verified categories.

### Current provider reference

- Google's Food and Drink taxonomy lists the supported structured types and does not currently include generic pasta or drinks types: [Google Place Types](https://developers.google.com/maps/documentation/places/web-service/place-types#table-a).

## Open-now filter

- **Date:** 2026-07-18
- **Status:** Provider request behavior superseded by Text Search-only discovery on 2026-07-21; missing-data behavior remains current

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
- **Status:** Provider request behavior superseded by Text Search-only discovery on 2026-07-21; threshold contract superseded by exact comparisons on 2026-07-31; sorting behavior remains current

### Decision

FoodFind's manual control supports four minimum-rating presets: 3.0, 3.5, 4.0, and 4.5. No minimum is the default. The current API and smart-search contract also support exact thresholds and comparison operators as documented in **Exact natural-language rating comparisons**.

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
- **Status:** Request endpoint superseded by Text Search-only discovery on 2026-07-21; conditional fields and filter behavior remain current

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

## Text Search-only food discovery

- **Date:** 2026-07-21
- **Status:** Current approach

### Decision

All food-business discovery uses Google Text Search. FoodFind does not route individual searches between Nearby Search and Text Search. Google location autocomplete, selected-location resolution, and on-demand Place Details remain separate and unchanged.

One explicit FoodFind search produces one Text Search request with `pageSize=20`. The current implementation does not request continuation batches; automatic top-up and infinite scrolling remain future work. Rendering, reloading, and editing criteria still produce no search request.

The Google adapter constructs a deterministic `textQuery` from the submitted cuisine, common food, and descriptive requirements. Cuisine and common food can coexist. When a specific dish already contains a selected common-food term, the adapter omits the repeated broad term from the provider query. Their presence means Google text relevance, not verified menu availability.

Place type is not submitted and the adapter does not send `includedType`. It removes a returned place when its known Google types do not match FoodFind's supported food-business types. Missing type data remains unconfirmed rather than being inferred.

Text Search can restrict a categorical query to a rectangle, not a circle. For ordinary locations, FoodFind calculates a rectangle enclosing the submitted circle. Near a pole or when the circle crosses the antimeridian, where one valid rectangle cannot represent that area, it uses a circular location bias instead. In every case, the application calculates exact straight-line distance from the immutable submitted location and removes results outside the selected radius.

An active Open now filter sends `openNow=true`; an active rating comparison sends the greatest half-point `minRating` that does not exceed the exact threshold. FoodFind still requests the corresponding response fields conditionally and verifies returned normalized values, including the exact rating comparison. Rating sorting remains application-side because Text Search does not rank by rating. Dine-in and Takeout remain conditional response fields followed by application-side filtering because Text Search has no request parameters for them.

### Rationale

- Text Search supports combined cuisine and common-food language instead of forcing both concepts into one misleading primary-type OR restriction.
- Provider-side Open now and minimum-rating filters preserve more relevant candidates than filtering those criteria only after a fixed Nearby Search result set.
- Continuation tokens provide a supported path to later automatic top-up and infinite scrolling.
- One discovery endpoint gives manual filters and the future LLM interpretation one consistent Google request path.
- Keeping the normalized provider port and application filtering preserves replaceability and testability.

### Tradeoffs

- Text relevance and defensive returned-type filtering are less exact than a single strict Google type.
- Rectangular restriction can return candidates outside the selected circle, so local filtering may shorten a batch.
- Text relevance does not verify that a restaurant currently serves a requested dish.
- The current single batch remains capped at 20 candidates and is not a complete business directory.

### Current provider references

- Text Search supports `textQuery`, one `includedType`, `strictTypeFiltering`, `openNow`, `minRating`, `rankPreference`, `pageSize`, and continuation tokens: [Text Search request reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchText).
- Text Search location restriction accepts a rectangular viewport: [Text Search location restriction](https://developers.google.com/maps/documentation/places/web-service/text-search#location-restriction).
- Text Search billing is controlled by the requested response field mask: [Text Search field masks](https://developers.google.com/maps/documentation/places/web-service/text-search#fieldmask).

## Focus Google Text Search on the requested food

- **Date:** 2026-07-29
- **Status:** Current

### Decision

When a search includes a cuisine, common food, or free-form dish, FoodFind uses those terms as the main Google `textQuery`. It no longer prefixes every such query with **restaurants or cafes or bars or bakeries**. If no food-specific term is present, the broad food-business query remains the fallback.

Location and radius remain separate request data. Known non-food results are still removed defensively. The change adds no request, response field, or higher billing tier.

### Rationale

- A focused query gives Google's relevance system a clearer statement of what the user wants.
- The fallback keeps searches such as **quiet atmosphere** scoped to food businesses.
- The provider-specific wording remains isolated in the Google adapter.
- Text relevance is still not proof that a requested dish is currently available.

## Evaluate list-wide Google review evidence before adoption

- **Date:** 2026-07-29
- **Status:** Closed without production adoption — 2026-07-30

### Decision

FoodFind evaluated Google review evidence with one controlled, list-level Enterprise + Atmosphere Text Search instead of making a Pro search followed by Place Details requests for every candidate.

The evaluation did not justify production implementation. Google did not expose sufficiently complete, current menu or review evidence, and some expected businesses were absent from the candidate set. FoodFind therefore did not add review-supported ranking, a supporting evidence provider, or a provider-independent food-evidence layer. Reconsider this work only when a stronger, current evidence source is identified.

Place Details remains on demand for information needed only after the user opens one result. Missing evidence is unknown, not proof that a food is unavailable.

The human-reviewed cases in `docs/examples.md` remain evaluation material. They do not train Gemini, provide runtime business evidence, or justify named-business conditions in production code.

### Rationale

- One list-level request avoids turning a result batch into many per-place calls.
- Separating list ranking from on-demand details keeps request cost tied to the user-visible need.
- The controlled probe prevented FoodFind from depending on incomplete or stale provider evidence.
- Missing evidence and omitted candidates made dependable food matching impossible with this approach.
- Reviewed examples can compare future search changes without becoming production rules.

## Treat Google query-related review evidence as useful but potentially stale

- **Date:** 2026-07-30
- **Status:** Accepted after the completed evidence probe

### Decision

The controlled Toronto evaluation returned query-related review justifications and showed that they can sometimes explain a result. They must not be used as proof that an item is currently on the menu, and they must not cause strict inclusion or exclusion by themselves.

The evidence may be used only as positive, potentially stale support. Missing evidence remains unknown. Any later product use must include Google Maps and review-author attribution, a link to the source review, and an explanation of how review evidence is selected.

The expanded evaluation did not approve review-supported production ranking: only five of ten recorded outcomes matched, some evidence covered only part of the query, and expected businesses missing from Google's first 20 could not benefit from ranking. The complete outcome is recorded in [`phase-6-step-1-probe.md`](phase-6-step-1-probe.md). The investigation ended after the probe, and no follow-on evidence implementation is planned until a stronger, current source is identified.

### Rationale

- Five of ten recorded outcomes matched the live results.
- A business expected not to appear was returned because an older review mentioned the requested food.
- Other justifications mentioned only a broad category or part of a multi-word dish.
- Two expected chocolate-cake businesses were absent from the candidate set.
- The mismatch demonstrates that review relevance and current menu availability are different claims.
- The probe requested `places.reviews`, which Google classifies as Text Search Enterprise + Atmosphere.

## Defer food-match precision

- **Date:** 2026-07-25
- **Status:** Future enhancement

### Decision

FoodFind will not currently infer food availability from a business name, LLM response, or unexplained Text Search rank. Common-food terms remain relevance signals, which can produce weak matches.

Future work must improve food-search accuracy and make match explanations less confusing while remaining honest about unverified menu items. The evidence sources, filtering behavior, ranking behavior, and explanation rules will be researched and decided when that work begins.

### Rationale

- Removing weak matches without reliable evidence could hide relevant businesses.
- Provider classification and verified menu availability are different claims and need different explanations.

## Smart-search interpretation defaults

- **Date:** 2026-07-22
- **Status:** Accepted for Phase 4

### Decision

The LLM produces a provider-independent `SearchIntent`. It keeps structured filters, descriptive requirements, resolved assumptions, and unsupported criteria separate so FoodFind can validate them before searching.

Rating language uses these defaults:

- **Good rated:** minimum 4.0
- **Highly rated:** minimum 4.5
- **Best** or **top rated:** sort by rating without inventing a minimum
- An explicit numeric threshold keeps its exact number and operator: **greater than**, `>` with or without spaces, and an obvious unambiguous misspelling of the phrase are strict; **at least**, **or higher**, `>=`, `≥`, and `+` are inclusive.

Time language uses these editable defaults:

- **Tonight:** 6 p.m. to midnight
- **Dinner:** 5 p.m. to 10 p.m.
- **At 7 p.m.:** open at that exact time, represented by equal start and end timestamps rather than an invented duration
- If a time window is already underway, start it at the current time.
- If an implied time or window has fully passed, use its next occurrence and show that assumption.
- Do not silently move an explicit past date; identify it as unsupported.

Multiple values within one group use **OR**, while different groups combine with **AND**. For example, Persian or Italian cuisines serving pizza or kebab.

Requirements without a dedicated filter, such as a dish or atmosphere preference, remain in the intent and may be included in Text Search. FoodFind does not present text relevance as proof. For example: **“Kebab availability is not verified—check the menu or call.”** A criterion that cannot be used safely is shown as unsupported rather than silently discarded or claimed as satisfied.

Gemini normalizes an obvious misspelling in a food, dish, or cuisine name only when the surrounding context makes the intended meaning clear. The standard spelling is used in the search intent, and the correction is shown as an assumption with the user's original wording. FoodFind does not use a hard-coded spelling list or silently correct ambiguous wording.

`SearchIntent` now keeps five explicit parts:

- `search_criteria`: the existing location, radius, structured filters, and sort
- `descriptive_requirements`: useful text-relevance criteria without dedicated filters
- `availability_window`: optional timezone-aware start and end times
- `assumptions`: the original phrase and its visible interpretation
- `unsupported_criteria`: the request and the reason it cannot be applied safely

The place-search use case now executes `search_criteria`, `descriptive_requirements`, and `availability_window`. Assumptions and unsupported criteria remain review information and are not sent to the place provider. Keeping these parts separate prevents unsupported meaning from being silently treated as satisfied.

### Rationale

This preserves what the user asked for while keeping assumptions reviewable and preventing likely matches from being presented as verified facts.

## Gemini free tier as the first LLM adapter

- **Date:** 2026-07-23
- **Status:** Current development approach

### Decision

FoodFind uses a provider-neutral `SearchInterpreter` port. Google Gemini is the first adapter, with stable `gemini-3.6-flash` as the configurable default.

The adapter uses Google's `google-genai` Python SDK and sends the Pydantic-generated JSON Schema through `response_json_schema`. This path preserves strict object validation, exact numeric rating thresholds, and the rating-comparison enum. FoodFind validates the returned value again before converting it into the domain `SearchIntent`. Provider failures become a provider-neutral `SearchInterpreterError`.

`GEMINI_API_KEY` stays in the server-side `.env` file and is separate from the Google Maps key. `GEMINI_MODEL` may replace the default without changing domain or application code. Automated tests inject a fake Gemini client and never make a live request.

The Gemini free tier is suitable for local development, but its limits and availability are controlled by Google. Google states that free-tier content may be used to improve its products. FoodFind must not send secrets or unnecessary sensitive data. The interpreter receives only the submitted search state and the location, time, timezone, and capability context required for interpretation.

The adapter is connected only to the explicit `POST /api/search/interpret` endpoint. Creating or loading the application still makes no Gemini request.

### Rationale

- The free tier avoids an initial per-request development cost.
- Structured output and Pydantic validation fit the existing Python domain boundary.
- The port keeps OpenAI, Anthropic, Ollama, or another provider replaceable.
- Connecting the endpoint only after location and time context were defined keeps each request complete and reviewable.

### Current provider references

- [Gemini 3.6 Flash and current model guidance](https://ai.google.dev/gemini-api/docs/latest-model)
- [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini API pricing and free-tier data use](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key)

## Immutable smart-search context and **near me**

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

Each interpretation receives one immutable `SearchInterpretationContext`. It contains one timezone-aware current-time snapshot, an IANA timezone name, and FoodFind's supported cuisines, common foods, ratings, sorts, radius limits, boolean filters, and descriptive-requirement kinds.

The submitted `SearchCriteria` supplies the selected-location label and coordinates. The same snapshot is used throughout one interpretation; the adapter does not re-read mutable browser state or the clock.

Until Phase 5 adds device location, **near me** always means the visible submitted selected location. `InterpretSearch` records this assumption deterministically and preserves the submitted location even if an LLM response is incomplete or inconsistent. This policy belongs to the application layer and therefore remains the same if Gemini is replaced.

Capabilities explicitly say that device location and arbitrary location resolution from a sentence are not available yet. The interpreter must identify those requests as unsupported rather than inventing a value. Time-aware availability is enabled and uses the existing immutable date and timezone context.

### Rationale

- One immutable snapshot prevents location or time context from changing partway through interpretation.
- An explicit capability contract prevents the model from treating future features as current behavior.
- Enforcing **near me** outside the model makes the user-visible assumption reliable and provider-independent.

## Time-aware availability interpretation

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

Gemini resolves time language into the provider-independent `AvailabilityWindow` using the current datetime and IANA timezone from `SearchInterpretationContext`. It must use the correct local UTC offset and must not approximate a future or broader window with the **Open now** filter.

FoodFind applies the agreed defaults for **tonight**, **dinner**, and exact times. An exact time uses equal start and end timestamps, which represents a point without inventing a duration. Ranges may have different start and end timestamps but cannot end before they start.

The application layer normalizes accepted output to the context timezone. If a range is already underway, its start becomes the immutable current time. An output with the wrong local UTC offset or a window entirely in the past is rejected as an interpreter error. For implied language that has already passed, the model uses the next occurrence and records an assumption; an explicit past date remains unsupported.

This step established validated availability data without adding an endpoint itself. Phase 4 Step 6 now displays it as editable criteria through the explicit interpretation endpoint; page loads still do not call Gemini.

### Rationale

- Concrete timezone-aware timestamps make relative language stable after interpretation.
- Exact points preserve the user's request without inventing an arbitrary interval.
- Application-layer checks keep time safety consistent if the LLM provider changes.
- Separating interpretation from UI wiring preserves the explicit-submission lifecycle.

## Explicit interpretation and local review

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

FoodFind exposes `POST /api/search/interpret` as the only user-facing LLM entry point. The request contains the submitted sentence, one immutable snapshot of the selected location and current manual criteria, and the browser's IANA timezone. The server supplies one current UTC time snapshot and injects the configured `SearchInterpreter`.

Selecting **Apply request** makes exactly one interpretation request. Typing, rendering, page loading or reloading, and editing interpreted controls make no LLM request. Interpretation does not automatically make a Google Places request.

A validated response replaces the browser's radius, structured filters, and sort, clears stale place results, and displays:

- resolved assumptions
- descriptive text-relevance requirements
- unsupported criteria and their reasons
- a timezone-labelled, editable availability window

The browser marks the interpretation as edited after a manual change but keeps the original assumptions visible for review. Removing or editing availability remains local. A custom interpreted radius is shown in the existing radius selector even when it is not one of the predefined choices.

The review panel states that descriptive requirements are relevance signals rather than verified facts. Phase 4 Step 7 now carries the reviewed descriptive requirements and availability window through the explicit Search action.

The Gemini client and key remain server-side. The dependency is created only for the interpretation endpoint and closed after the request. Missing configuration returns a safe `503`; provider or invalid-output failures return a safe `502`, all with `Cache-Control: no-store`.

### Rationale

- Separating interpretation from search lets the user review and correct the model's output.
- One explicit action and one immutable snapshot prevent request loops and state drift.
- Local editing avoids repeat LLM cost and latency.
- Honest staging prevents unimplemented time or relevance behavior from appearing functional.

## Explicit reviewed-intent search

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

Selecting **Search** creates one immutable request containing the current structured criteria, descriptive requirements, and optional availability window. The browser sends it once to `POST /api/places/search`; it does not call Gemini again. Typing, rendering, reloading, interpreting, and editing remain request-free until the user explicitly selects **Apply request** or **Search**.

The provider port accepts descriptive requirements and an availability window without exposing Google-specific fields to the application. The Google adapter adds descriptive text to its deterministic Text Search query. This changes relevance only and is not evidence that a dish, dietary request, or atmosphere is actually available.

When availability is active, the adapter conditionally requests `places.currentOpeningHours` and `places.timeZone` in the same Text Search response. This makes that search Enterprise because current opening hours are an Enterprise field; it does not create Place Details calls for each result. The adapter converts Google periods into provider-independent timezone-aware opening periods, and the application applies the time rule:

- a non-empty requested range matches when an opening period overlaps any part of it
- an exact requested time matches only when it falls inside an opening period
- missing or unusable hours cannot confirm the requirement, so the candidate is excluded

Raw opening periods are used only during server-side filtering and are excluded from the result response. The existing one-batch, one-Google-request limit remains unchanged.

### Rationale

- One explicit snapshot preserves the reviewed intent without request loops or state drift.
- Application-layer time matching stays testable and provider-independent.
- Conditional fields preserve the lower-cost default search when no time window is active.
- Excluding unconfirmed candidates avoids presenting missing hours as proof of availability.

Google lists `currentOpeningHours` under Text Search Enterprise and `timeZone` under Text Search Pro in its [Places API field table](https://developers.google.com/maps/documentation/places/web-service/data-fields).

## Deterministic match explanations

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

`SearchPlaces` creates each result's match reasons after all provider-independent filtering is complete. A reason contains a short deterministic message and one of two evidence labels:

- **Confirmed:** supported by the submitted criteria, FoodFind's distance calculation, or data already returned by the provider
- **Relevance only:** a cuisine, food, dish, dietary, atmosphere, or other text term that influenced provider search relevance but is not a verified fact

Confirmed explanations may identify the provider category, selected radius, an active Open now or minimum-rating condition, active dine-in or takeout requirements, and provider hours overlapping a requested time. Explanations mention only active criteria; sorting alone is not described as proof that a result matched.

A single selected common food uses the agreed warning, such as **“Kebab availability is not verified—check the menu or call.”** If a descriptive dish requirement repeats an active common-food filter, FoodFind keeps one message. Other descriptive requirements retain the reviewed text and state the appropriate verification limitation.

Match reasons are serialized in the existing search response. The result card renders them inside a native **Why this matched** disclosure. Expanding or collapsing it is entirely local and creates no Gemini, Google Text Search, or Place Details request.

### Rationale

- Deterministic explanations are testable and cannot add unsupported LLM claims.
- Evidence labels make provider-confirmed data visibly different from text relevance.
- Reusing the submitted snapshot and existing response prevents extra cost and request loops.
- A compact disclosure keeps result cards manageable while satisfying the PRD's explanation requirement.

## Smart-search failure and capability boundary

- **Date:** 2026-07-23
- **Status:** Accepted for Phase 4

### Decision

FoodFind does not trust valid JSON alone. After Pydantic validation, the application revalidates every interpreted filter, sort, radius, descriptive-requirement kind, and availability request against the immutable capability snapshot supplied for that interpretation. A disabled or unknown capability is an interpreter failure; it is not silently accepted.

Malformed model output and interpreter failures return a safe error and leave the browser's current criteria unchanged. Unsupported criteria the interpreter identifies correctly remain visible in the review panel but are not sent to place search. The user may explicitly search using only the supported criteria.

Google's `currentOpeningHours` covers today and the next six days. FoodFind includes this seven-day horizon in the interpreter capability contract. An interpreted window beyond it is rejected as invalid output. Because the user can edit the window locally, place search validates it again and returns a safe input error before calling Google when it is in the past or beyond the same horizon.

Missing place data is never inferred. Cards show an unavailable label or operational-status warning where appropriate. A missing field fails any active filter that requires provider confirmation. An empty result set receives actionable guidance distinct from invalid input or temporary failure.

Interpretation and place search are retried only through another explicit user action. Loading, reloading, rendering, errors, and empty results never create an automatic retry.

### Rationale

- Application-side enforcement keeps the capability boundary reliable if the prompt or LLM provider changes.
- Validating edited time windows before provider access avoids a Google request that cannot confirm the requested time.
- Preserving unsupported criteria lets the user see what was omitted without misrepresenting it as applied.
- Explicit recovery avoids request loops and unexpected Gemini or Google cost.

Google documents `currentOpeningHours` as covering the next seven days, including today, in the [Place resource reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places).

## Exact natural-language rating comparisons

- **Date:** 2026-07-31
- **Status:** Current behavior

### Decision

FoodFind preserves an explicit rating threshold from 0 to 5 and whether the user requested **greater than** or **at least**. Manual controls remain the simple 3.0+, 3.5+, 4.0+, and 4.5+ presets. An exact smart-search comparison appears as a custom value in the same rating control; choosing a manual preset replaces it.

The interpreter treats textual and symbolic forms consistently. `> 4.7` and `>4.7` are the same strict comparison as **greater than 4.7**; `>= 4.7`, `≥4.7`, and `4.7+` are inclusive. An obvious unambiguous misspelling in the comparison phrase may be normalized without changing the number or operator.

Google rounds `minRating` upward to a half-point value. FoodFind therefore sends the greatest half-point that does not exceed the requested threshold, then applies the exact comparison to the returned normalized ratings. For **rating greater than 4.8**, Google receives `minRating: 4.5`; FoodFind excludes ratings of 4.8 or lower. **At least 4.8** includes 4.8. Missing ratings do not satisfy either comparison.

This remains one Enterprise Text Search request with `places.rating`. It creates no Place Details request and does not change the explicit-search lifecycle. The safe coarse prefilter can still leave fewer than 20 visible candidates because continuation batches remain deferred.

### Rationale

- Preserving the number and operator keeps the user's request exact.
- A lower safe provider prefilter avoids losing valid 4.9 results through Google's upward rounding.
- Local verification makes the behavior provider-independent and testable with mocked responses.

## Phase 5 map provider and current-location submission

- **Date:** 2026-07-25
- **Status:** Accepted for Phase 5

### Decision

FoodFind will use Google Maps for the Phase 5 embedded map.

After the user explicitly selects **Use current location** and grants permission, FoodFind sets the normalized selected location and recenters the map. It does not search until the user presses **Search**. Immediate search after resolving the device location remains a possible future enhancement.

The embedded map will use a separate browser-restricted Google Maps JavaScript API key. The existing Google Places key remains server-side and is not reused in the frontend.

### Rationale

- Google Places results displayed on a map must be shown on a Google map under Google's Places policies.
- Waiting for **Search** keeps location selection consistent with other location inputs and avoids an unexpected Places request.
- A separate browser key can be restricted to approved website referrers and the Maps JavaScript API without exposing the server-side Places credential.

## Google Maps frontend boundary

- **Date:** 2026-07-26
- **Status:** Accepted for Phase 5 Step 1

### Decision

FoodFind loads Maps JavaScript through the official `@googlemaps/js-api-loader` package behind a FoodFind-owned frontend `MapRenderer` port. The adapter configures the loader once, imports only the Maps library needed by the current step, and owns creation and cleanup of the Google map instance.

The browser reads its separately restricted key from `PUBLIC_GOOGLE_MAPS_API_KEY` in `frontend/.env`. It uses Google's `DEMO_MAP_ID` during development so later steps can use Advanced Markers without requiring another setup action now. A FoodFind-specific map ID and HTTPS deployment remain future production-readiness work.

Missing configuration and provider-load failures are visible component states. Automated tests inject a fake renderer or mock the loader and never request Google Maps.

### Rationale

- The port keeps Svelte component behavior testable without depending directly on Google's global API.
- Loading through one shared promise prevents duplicate Maps JavaScript script requests within the page lifecycle.
- The browser-only key can be restricted independently without exposing the server-side Places key.
- Google recommends Advanced Markers over the deprecated legacy marker and requires a map ID for them.

Current references: [Load the Maps JavaScript API](https://developers.google.com/maps/documentation/javascript/load-maps-js-api) and [Advanced Markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/add-marker).

## Provider-neutral map snapshots

- **Date:** 2026-07-26
- **Status:** Accepted for Phase 5 Step 2

### Decision

The Svelte page passes the map component its current selected coordinates, radius, and normalized place results. The component converts them into a provider-neutral `MapSnapshot` containing only centre coordinates, radius metres, and minimal marker summaries. The snapshot is rendered through the existing `MapRenderer` port.

The Google adapter keeps one map and one radius circle alive. For every new snapshot it updates the circle, removes superseded result markers, creates Advanced Markers for current results, and fits the viewport around the radius plus returned coordinates. The search-centre marker remains visually above result markers.

Map updates never call a FoodFind endpoint, the Google Places library, or Place Details. Location and radius edits update the map but retain the existing rule that only **Search** starts place discovery. Result markers remain non-interactive until Phase 5 Step 3 connects them to result cards.

### Rationale

- One immutable snapshot keeps the map consistent with the visible Svelte state.
- Reusing the map and circle avoids unnecessary Maps JavaScript loads and lifecycle drift.
- Passing only FoodFind-owned values keeps Google classes outside the component and page.
- Removing old markers before adding current ones prevents stale or duplicated businesses.

Google documents circle radius values in metres and `fitBounds` as fitting the viewport to supplied bounds: [Shapes and circles](https://developers.google.com/maps/documentation/javascript/shapes) and [Map reference](https://developers.google.com/maps/documentation/javascript/reference/map).

## Synchronized map and result selection

- **Date:** 2026-07-26
- **Status:** Accepted for Phase 5 Step 3

### Decision

The page owns one selected-result key in the form `provider:provider_place_id`. It passes that key to the map snapshot and derives each result card's selected state from the same value. The Google adapter reports marker selection through the `MapRenderer` port rather than exposing Google marker objects to Svelte.

Result markers use place-name titles and Google Advanced Markers' clickable behavior so they can be selected with a pointer or keyboard. The matching card has an explicit **Show on map** control. Selecting either view highlights both, and marker selection scrolls the card into view.

Selection is presentation state only. It does not call place search or Place Details, and changing only the selection does not refit the map viewport. **View details** remains a separate explicit action.

### Rationale

- One page-owned key prevents marker and card selection from drifting apart.
- Keeping provider events behind the existing port preserves a mockable, replaceable map boundary.
- A dedicated card control avoids ambiguous clicks around links and detail actions.
- Separating selection from data loading prevents accidental Google requests.

Google documents accessible Advanced Markers through `gmpClickable`, titles, and the `gmp-click` event: [Accessible markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/accessible-markers) and [Advanced Marker reference](https://developers.google.com/maps/documentation/javascript/reference/advanced-markers).

## Explicit map location selection

- **Date:** 2026-07-26
- **Status:** Superseded by direct map location selection

### Decision

FoodFind changes the search location from a map click only after the user selects **Choose location on map**. The `MapRenderer` port reports the chosen coordinates without exposing Google objects. The page rounds them to six decimal places, creates the existing provider-neutral `SelectedLocation`, clears stale results, and updates the Location field.

The selected point is initially labelled with its coordinates; FoodFind does not make a reverse-geocoding request. It recentres the existing map but waits for the user to select **Search** before requesting places. Panning, zooming, cancelling, and result-marker selection do not change the location.

### Rationale

- An explicit mode prevents ordinary map exploration from silently changing search criteria.
- Reusing `SelectedLocation` keeps map, typed-coordinate, autocomplete, and future device locations on one lifecycle.
- A coordinate label is immediately available without another paid or failure-prone provider request.
- Six decimal places keep the label readable while retaining more precision than this search experience needs.

Google's map click event supplies the clicked latitude and longitude and remains separate from marker clicks: [Map events](https://developers.google.com/maps/documentation/javascript/reference/map).

## Integrated location choices and direct map selection

- **Date:** 2026-07-26
- **Status:** Current

### Decision

Focusing or typing in the Location field opens its choice list with **Use current location** first, followed by any matching Google suggestions. Merely opening the list never requests device permission; only selecting **Use current location** does.

FoodFind no longer requires a **Choose location on map** mode. Clicking an empty point on the base map directly updates the normalized location, clears stale results, and waits for **Search**. Panning, zooming, and selecting a result marker remain separate and do not change the search centre.

### Rationale

- Location choices belong together at the Location field instead of competing as separate controls.
- A direct base-map click makes the visible map behave as a location input without a selection/cancel mode.
- Explicitly selecting the current-location option preserves the privacy and permission boundary.
- Waiting for **Search** preserves the existing request lifecycle and prevents accidental Places or Gemini calls.

## Browser geolocation boundary and accuracy

- **Date:** 2026-07-26
- **Status:** Accepted for Phase 5 Step 5

### Decision

FoodFind accesses `navigator.geolocation` through a frontend `DeviceLocationProvider` port only after the user selects **Use current location**. It makes one `getCurrentPosition()` request with `enableHighAccuracy: true`, `maximumAge: 0`, and a 10-second timeout. No permission check or position request occurs during rendering, reload, **near me** interpretation, or testing.

While the request is pending, other search and criteria actions are disabled. A valid result enters the same coordinate-normalization lifecycle as map selection, clears stale results, recentres the existing map, and waits for **Search**.

The browser's reported accuracy is compared with the selected radius. If it exceeds that radius, FoodFind still accepts the position but warns that it may be imprecise and keeps manual and map adjustment available. Permission denial, timeout, unavailable or unsupported geolocation, and invalid position data receive separate recovery guidance.

### Rationale

- A user action before geolocation protects privacy and prevents surprise permission prompts.
- One shared coordinate lifecycle prevents typed, map, and device locations from diverging.
- Locking other actions prevents search results for the old location from arriving after the new position.
- Reported accuracy is an estimate; warning preserves user control without unnecessarily rejecting a usable position.
- The port makes browser behavior replaceable and keeps automated tests independent of real devices.

The browser API requires permission, supports the selected position options, and reports standardized failure codes: [W3C Geolocation](https://www.w3.org/TR/geolocation/) and [MDN `getCurrentPosition()`](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition).

## Phase 5 map lifecycle verification

- **Date:** 2026-07-26
- **Status:** Complete

### Decision

The Phase 5 lifecycle keeps one Google map instance for each mounted map panel. Reactive location, radius, result, and result-selection state updates the existing instance through immutable snapshots. Panning and zooming have no application callback; a base-map click can report coordinates directly, while result-marker clicks remain result selection.

Rendering and reloads make no Places, Place Details, Gemini, autocomplete, or device-geolocation request. Criteria edits, marker/card selection, map movement, accepted map points, and accepted device positions also make no place-search request; only **Search** does. Automated tests replace both Google Maps and browser geolocation.

The final audit also established two ordering rules:

- When location text becomes unresolved or invalid, the map retains the last valid centre instead of reverting to the default.
- When another operation disables the location picker, any pending autocomplete or location-resolution request is immediately cancelled and its stale response is ignored.

### Rationale

- A stable map centre avoids displaying a location the user did not select.
- Cancelling older location work prevents asynchronous responses from overwriting newer map or device choices.
- Explicit request boundaries prevent reload loops and accidental provider costs.
- Mocked external adapters make every lifecycle rule deterministic in automated tests.

## Location-first search page and empty default

- **Date:** 2026-07-26
- **Status:** Accepted for current Phase 6 Step 2

### Decision

FoodFind starts with no selected location and an empty Location field. Toronto City Hall remains only the map's neutral starting camera position and autocomplete bias; it is not valid search criteria and produces no centre marker or radius circle.

The page order is:

1. Location—with **Use current location** inside its choice list—and Radius
2. Map
3. Optional smart search and manual criteria
4. A concise location requirement, Sort, and **Search places**

Location is the only required input and all search criteria remain optional. The page states this in Step 3 without showing a separate required/ready card. Location feedback stays near the location controls. The final search action remains disabled until a location is selected.

Device geolocation uses **Current location** as its visible label while retaining normalized coordinates internally. It updates the Location field, map centre, marker, and radius without reverse geocoding or automatically searching.

### Rationale

- An empty field prevents an assumed Toronto search and makes the user's first decision explicit.
- Keeping the map directly beside the location step makes its purpose and updates easier to understand.
- Concise requirement text explains the disabled action without duplicating the same information in a large status card.
- **Current location** communicates the source more clearly than raw coordinates; the coordinates remain available to the application.
