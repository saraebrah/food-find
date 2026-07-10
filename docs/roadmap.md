# Roadmap

This file tracks the planned build sequence, current priorities, feature status, and what should be worked on next.

Each phase should leave FoodFind working. Relevant tests should be written with each task rather than postponed to a later phase.

Priority levels:

- **P0:** Required for the first useful version
- **P1:** Completes and improves the first version
- **P2:** Later enhancement

## Phase 1 — First real results

- **Priority:** P0
- **Status:** In progress

- [x] Create the basic web application.
- [x] Connect one place-data provider. Google adapter implemented with mocked automated tests and one controlled live smoke test.
- [ ] Search using a fixed Toronto location and radius.
- [ ] Normalize the provider response into FoodFind's place format.
- [ ] Display results in a simple list.

This phase comes first because it proves the central data flow and produces the smallest useful version of FoodFind.

## Phase 2 — Basic place discovery

- **Priority:** P0
- **Status:** Not started

1. Let users enter or select a location.
2. Let users choose a radius.
3. Add loading, error, and no-results states.
4. Show essential information for each result.
5. Add place details.
6. Add website, phone, and Google Maps direction actions.

This phase turns the fixed search from Phase 1 into a usable discovery flow.

## Phase 3 — Map experience

- **Priority:** P0
- **Status:** Not started

1. Display results on a map.
2. Keep map markers and result-list items connected.
3. Support selecting a business from either view.
4. Update the map when the location or radius changes.

The list and search behavior should work before map synchronization is added.

## Phase 4 — Manual filters and sorting

- **Priority:** P0
- **Status:** Not started

Add filters incrementally:

1. Place type
2. Open now
3. Minimum rating
4. Cuisine
5. Dine-in and takeout
6. Common food
7. Distance and rating sorting

Manual controls establish the search model that smart search will later use. A filter should only be added when the selected provider can support it reliably.

## Phase 5 — Current location

- **Priority:** P1
- **Status:** Not started

1. Request browser location permission.
2. Search around the user's position.
3. Handle denied or unavailable permission.
4. Keep manual location selection as a fallback.

Current location is useful but does not need to block the selected-location search flow.

## Phase 6 — Smart search

- **Priority:** P1
- **Status:** Not started

1. Accept keywords and natural-language requests.
2. Convert requests into the existing manual filter state.
3. Show interpreted criteria as editable controls.
4. Identify unsupported or ambiguous criteria.
5. Explain why results matched.

Smart search should reuse the proven manual search behavior rather than introduce a separate search system.

## Phase 7 — First-version cleanup

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

Build the fixed Toronto search flow using the Google provider adapter. Live requests must stay manual and sparse while local development uses API restrictions plus the `$2/month` budget alert instead of a hard daily quota.

## Open decisions

- Map provider
- Whether current-location support should move ahead of the map phase
