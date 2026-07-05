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
- A low daily request quota must be configured in Google Cloud before live development calls begin.

The quota is configured in Google Cloud, not in this repository. Live Google integration remains blocked until that setup is confirmed.

### Rationale

Google Places supplies the basic place fields needed for the first version, and expected development usage should remain within its monthly free allowance. The existing provider interface decision keeps the application replaceable if that changes.
