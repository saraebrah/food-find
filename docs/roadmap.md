# Roadmap

This file tracks the planned build sequence, current priorities, feature status, and what should be worked on next.

Each phase should leave FoodFind working. Relevant tests should be written with each task rather than postponed to a later phase.

Priority levels:

- **P0:** Required for the first useful version
- **P1:** Completes and improves the first version
- **P2:** Later enhancement

## Phase 1 — First real results

- **Priority:** P0
- **Status:** Complete

- [x] Create the basic web application.
- [x] Connect one place-data provider. Google adapter implemented with mocked automated tests and one controlled live smoke test.
- [x] Normalize provider responses into FoodFind's place format behind a provider port.
- [x] Search using a fixed Toronto location and radius through an explicit server endpoint.
- [x] Display normalized results in a simple list after an explicit search action.

This phase comes first because it proves the central data flow and produces the smallest useful version of FoodFind.

## Phase 2 — Basic place discovery

- **Priority:** P0
- **Status:** Complete

1. [x] Let users enter or select a location.
   - [x] **Step 1A:** Generalize search around a normalized selected location and accept decimal coordinates.
   - [x] **Step 1B:** Add Google place/address autocomplete and suggestion selection.
2. [x] Let users choose a radius.
3. [x] Add loading, error, and no-results states.
4. [x] Show an essential summary: name, category, address, straight-line distance, and source.
   - Exclude businesses explicitly reported temporarily or permanently closed.
   - Warn when operational status is unknown.
5. [x] Add Enterprise place details on demand: rating, hours and open status, phone, and website when available.
   - For an unconfirmed status, show an available phone number and **Call to confirm** action.
6. [x] Add website, phone, and Google Maps direction actions.

This phase turns the fixed search from Phase 1 into a usable discovery flow.

## Phase 3 — Manual filters and sorting

- **Priority:** P0
- **Status:** In progress

- [x] Transition the temporary browser interface to Svelte 5 and SvelteKit while preserving the completed Phase 2 behavior and request safeguards.

Add filters incrementally, grouped by the highest Google Nearby Search billing tier they require:

### Pro group

1. [x] Establish one normalized filter and sorting state shared by the browser, API, and application.
2. [x] Place type
3. [x] Cuisine, using only supported provider types
4. [x] Common food, using only reliable provider types and without claiming menu availability
5. [x] Distance sorting through the provider's distance rank preference
6. [x] Review the complete Pro filter group before requesting Enterprise search fields.

### Enterprise group

7. [x] Open now
8. [x] Minimum rating
9. [x] Rating sorting
10. [x] Review Enterprise cost, missing-data behavior, and results before continuing.

### Enterprise + Atmosphere group

11. [x] Dine-in and takeout
12. **Current pause:** review Enterprise + Atmosphere cost, missing-data behavior, and results before completing Phase 3.

For each filter, first confirm provider support, billing tier, missing-data behavior, and whether it can be applied by the provider or only to the returned result set. Implement and verify one filter before moving to the next.

Manual controls establish the search model that smart search will later use. A filter should only be added when the selected provider can support it reliably. Complete and review each billing group before the next group begins. Higher-tier fields must be requested only when an active filter in that group needs them; they do not become part of every default search.

## Phase 4 — Smart search

- **Priority:** P0
- **Status:** Not started

1. Accept keywords and natural-language requests.
2. Convert supported requests into the existing manual filter state.
3. Show interpreted criteria as editable controls.
4. Identify unsupported or ambiguous criteria.
5. Explain why results matched.

Smart search is a translator into the proven manual search model, not a separate search system. Start with deterministic interpretation of supported criteria; add more complex language handling only when needed.

## Phase 5 — Map and current location

- **Priority:** P0
- **Status:** Not started

1. Display the current results on a map.
2. Keep map markers and result-list items connected.
3. Support selecting a business from either view.
4. Let users select or adjust the search location on the map.
5. Add **Use current location** and request browser permission only after the user selects it.
6. Recenter and search around the user's position.
7. Handle denied, inaccurate, or unavailable location while keeping manual selection as a fallback.
8. Update the map when the location or radius changes.

This phase completes the spatial experience after the result criteria are useful and proven. Every map click and device location still produces the same normalized selected-location model used by coordinates and autocomplete.

## Phase 6 — First-version cleanup

- **Priority:** P1
- **Status:** Not started

1. Improve desktop and mobile layouts.
2. Add keyboard and accessibility support.
3. Handle missing provider fields consistently.
4. Add compliant short-lived caching if useful.
5. Verify the complete journey with automated tests.
6. Fix usability and performance problems found during real use.

This phase improves the complete working flow after the core behavior is established.

## Later work

- **Priority:** P2

- Saved favourites
- Shortlists and comparison
- Travel times
- Menu and dish discovery
- Conversational refinement
- Reservation integration
- Native mobile application

## Current next task

Review the completed Phase 3 Enterprise + Atmosphere filter group. Do not begin Phase 4 until it is explicitly approved.

## Open decisions

- Map provider
