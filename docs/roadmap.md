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
- **Status:** Complete

- [x] Transition the temporary browser interface to Svelte 5 and SvelteKit while preserving the completed Phase 2 behavior and request safeguards.

The filters were implemented incrementally using Nearby Search and grouped by the highest Google billing tier they required. Phase 4 later migrated food discovery to Text Search while preserving these controls and conditional field masks.

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
12. [x] Review Enterprise + Atmosphere cost, missing-data behavior, and results before completing Phase 3.

For each filter, first confirm provider support, billing tier, missing-data behavior, and whether it can be applied by the provider or only to the returned result set. Implement and verify one filter before moving to the next.

Manual controls establish the search model that smart search will later use. A filter should only be added when the selected provider can support it reliably. Complete and review each billing group before the next group begins. Higher-tier fields must be requested only when an active filter in that group needs them; they do not become part of every default search.

## Phase 4 — Smart search

- **Priority:** P0
- **Status:** In progress

1. [x] Migrate all food-business discovery from Nearby Search to Text Search while leaving location autocomplete and on-demand Place Details unchanged.
   - Build one deterministic `textQuery` from the selected place types, cuisines, and common foods.
   - Allow cuisine and common food to coexist. Treat the result as Google text relevance, not verified menu availability.
   - When exactly one place type is selected, also use Text Search's strict `includedType`. When several are selected, mention them in the query and remove returned places whose known Google types do not match any selection.
   - Restrict Google to a rectangle enclosing the selected circle, calculate exact straight-line distance in FoodFind, and remove outside-radius candidates.
   - Send Open now and minimum rating as Text Search request filters. Continue to request only the response fields required by active filters and sorts.
   - Keep the MVP to one Google request per submitted search and one batch of up to 20 candidates. Pagination and infinite scrolling remain future enhancements.
2. [x] Define a provider-independent `SearchIntent` for the LLM's structured output.
   - Keep structured filters, descriptive requirements, assumptions, and unsupported criteria separate.
   - Use the agreed rating and time-language defaults in `docs/decisions.md`.
   - Preserve useful descriptive terms for Text Search, but do not present text relevance as a verified fact.
3. Add a server-side LLM interpreter behind a replaceable port. Validate its structured output with Pydantic, keep its API key server-side, and mock all LLM responses in automated tests.
4. Give the interpreter the selected location, current date and timezone, and FoodFind's supported capabilities. Until Phase 5 adds device location, interpret **near me** as the visible selected location and state that assumption.
5. Add time-aware availability so phrases such as **open tonight** become a visible, editable time window rather than being approximated as **Open now**.
6. Populate the existing manual controls from the interpretation, show the LLM's assumptions, and let the user edit criteria without another LLM call.
7. Run a search only from an explicit submission. Typing, rendering, reloading, and editing interpreted controls make no LLM or Google request; one submitted smart search makes at most one LLM interpretation request and one Google search request.
8. Explain why each result matched using the validated interpretation and confirmed provider data rather than making an LLM call for every result.
9. Handle invalid LLM output, interpreter failure, unsupported provider capabilities, missing place data, and no-result searches without inventing criteria or retry loops.

The LLM resolves language into a validated FoodFind intent; it does not call Google, construct field masks, or bypass application rules. Manual and natural-language input with the same normalized intent must produce the same Text Search semantics.

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

## Future enhancements

- **Priority:** P2

### Automatically fill the result list

- FoodFind's Text Search response can include a continuation token, but the current MVP intentionally ignores it after the first batch.
- Later, if a Text Search batch and FoodFind's filters leave fewer than 20 valid results, automatically request another batch and add its valid results. Continue until there are 20 valid results or Google has no more batches.
- Each additional batch is another Google API request. Before building this, set a maximum number of extra batches so one search cannot create too many requests or an accidental loop. For example, FoodFind might allow at most two extra batches for one search, but the actual limit will be decided when this enhancement is built.
- Stop requesting batches as soon as FoodFind has 20 valid results, Google has no more batches, the fixed batch limit is reached, or a request fails.
- Every extra batch must belong to the same submitted search. Apply the same location, radius, and filters, and do not show the same place twice.
- Page reloads, displaying existing results, and editing filters must not make these additional requests. They occur only while completing a search the user explicitly submitted.

See [Google Places Search Limitations](google-places-search-limitations.md) for the differences between Nearby Search and Text Search that affect this work.

### Scalable filter controls

- Replace long checkbox groups with accessible searchable multi-select dropdowns when the supported option lists become large enough to justify the added interaction.
- Keep selected values visible as removable chips or counts, preserve keyboard and screen-reader support, and do not hide active filters inside a closed dropdown.
- Keep Rating and Sort single-select unless their product behavior changes. A presentation change must not alter the normalized filter contract or search semantics.

### Verified menu and dish discovery

- Link to menus from restaurant-owned, licensed, or directly submitted sources, with the option to display appropriate menu content inside FoodFind later.
- Process permitted menu data so FoodFind can confirm that a restaurant currently offers a requested dish instead of relying only on Google category or Text Search relevance.
- Store source, last-checked time, and field-level provenance; do not infer menu availability from cuisine, business name, or an LLM response.
- Begin with a small Toronto-area experiment before expanding coverage or building menu search at scale.

### Broader category and provider coverage

- Revisit useful categories that the current FoodFind taxonomy does not represent reliably, including a generic food-truck filter and common foods such as pasta.
- Evaluate Text Search quality first, then another licensed provider or an open base dataset if Google remains insufficient.
- Preserve provider attribution, storage rights, entity matching, and deduplication when combining sources.

### Other product enhancements

- Saved favourites
- Shortlists and comparison
- Walking, transit, and driving travel times
- Multi-turn conversational refinement and follow-up instructions
- Reservation integration
- Native mobile application

## Current next task

Start Phase 4 Step 3 by adding a server-side LLM interpreter behind a replaceable port, validating its output with Pydantic, and using mocked LLM responses in automated tests.

## Open decisions

- Map provider
- LLM provider and model for development and later hosted use
