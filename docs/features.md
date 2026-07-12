# Features

This file breaks the product into individual features, including expected behavior, edge cases, acceptance criteria, and implementation notes.

## Fixed Toronto place search

### Current behavior

- `POST /api/places/search` runs one search centred on Toronto City Hall.
- The fixed radius is 1,000 metres.
- The fixed provider types are restaurant and café.
- The endpoint returns normalized FoodFind place objects.
- Loading or reloading the home page does not run a search.
- The Google client and server-side API key are created only when the search endpoint is called.
- The home page provides an explicit **Search Toronto** button.
- While a search is active, the button is disabled to prevent duplicate requests.
- Successful results appear in a list with the available name, category, address, and provider attribution.
- Missing category or address values are omitted instead of inferred.

The initial browser UI uses a small deferred JavaScript file. It attaches the API request only to the button's click event and does not run a search during page initialization.

### Acceptance criteria

- One endpoint request produces exactly one provider search.
- Repeated `GET /` requests produce zero provider searches.
- Automated tests replace the provider with a fake and never call Google.
- Search coordinates, radius, and included types are defined once in the application use case.
- Provider values are inserted with DOM text properties rather than interpreted as HTML.
- The result count and search status are announced through visible text and an ARIA live region.

The Phase 1 interface includes brief loading, empty, and failure messages so it never appears stuck. More complete state design and error recovery are scheduled for Phase 2.
