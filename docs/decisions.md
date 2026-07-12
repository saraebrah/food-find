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

Google response models remain inside the Google adapter and are converted to the internal model before results leave that boundary. Optional provider fields remain `None` when unavailable instead of being inferred.

Category labels and codes are still provider-supplied at this stage. A shared FoodFind category taxonomy will be introduced only when manual place-type filtering requires one.

### Rationale

- Application code can search for places without depending on Google's response schema.
- Another provider can implement the same port and return the same internal model.
- Immutable domain objects make one normalized provider response a stable snapshot for later application and display steps.
- Delaying a shared category taxonomy avoids inventing filtering behavior before that feature is built.

## Fixed Toronto search lifecycle

- **Date:** 2026-07-11
- **Status:** Current Phase 1 behavior

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
