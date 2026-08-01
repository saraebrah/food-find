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
2. [x] Place type (implemented, then removed from the product on 2026-07-26 because it did not add useful user control)
3. [x] Cuisine, using a reviewed FoodFind allowlist represented in Google Text Search
4. [x] Common food, using reviewed Text Search relevance terms without claiming menu availability
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
- **Status:** Complete

1. [x] Migrate all food-business discovery from Nearby Search to Text Search while leaving location autocomplete and on-demand Place Details unchanged.
   - Build one deterministic `textQuery` from the selected cuisine, common food, or free-form dish, with a broad food-business fallback when no food-specific term is present.
   - Allow cuisine and common food to coexist. Treat the result as Google text relevance, not verified menu availability.
   - Keep business type out of the editable filter contract and remove returned places whose known Google types fall outside FoodFind's broad food-business scope.
   - Restrict Google to a rectangle enclosing the selected circle, calculate exact straight-line distance in FoodFind, and remove outside-radius candidates.
   - Send Open now and minimum rating as Text Search request filters. Continue to request only the response fields required by active filters and sorts.
   - Keep the MVP to one Google request per submitted search and one batch of up to 20 candidates. Pagination and infinite scrolling remain future enhancements.
2. [x] Define a provider-independent `SearchIntent` for the LLM's structured output.
   - Keep structured filters, descriptive requirements, assumptions, and unsupported criteria separate.
   - Use the agreed rating and time-language defaults in `docs/decisions.md`.
   - Preserve useful descriptive terms for Text Search, but do not present text relevance as a verified fact.
3. [x] Add a server-side LLM interpreter behind a replaceable port. Validate its structured output with Pydantic, keep its API key server-side, and mock all LLM responses in automated tests.
4. [x] Give the interpreter the selected location, current date and timezone, and FoodFind's supported capabilities. Until Phase 5 adds device location, interpret **near me** as the visible selected location and state that assumption.
5. [x] Add time-aware availability so phrases such as **open tonight** become a visible, editable time window rather than being approximated as **Open now**.
6. [x] Populate the existing manual controls from the interpretation, show the LLM's assumptions, and let the user edit criteria without another LLM call.
7. [x] Run a search only from an explicit submission. Typing, rendering, reloading, and editing interpreted controls make no LLM or Google request; one submitted smart search makes at most one LLM interpretation request and one Google search request.
   - Carry the reviewed structured filters, descriptive requirements, and availability window into the submitted place-search snapshot.
   - Add descriptive requirements to the deterministic Text Search query as relevance signals, not verified facts.
   - When a time window is active, request current opening periods and the place timezone in the same Text Search request. Keep a result only when Google-provided hours overlap a requested range or contain an exact requested time; missing hours do not count as confirmation.
   - Do not expose raw opening periods in the browser response or create per-result detail requests.
8. [x] Explain why each result matched using the validated interpretation and confirmed provider data rather than making an LLM call for every result.
   - Build deterministic `confirmed` and `relevance` reasons after application filtering, using the submitted criteria and data already returned for that place.
   - Confirm only facts FoodFind can support, such as radius, provider category, an active rating or service filter, and requested-time overlap.
   - Label cuisine, dish, dietary, atmosphere, and other text matches as relevance-only. Collapse duplicate structured and descriptive dish messages.
   - Include reasons in the existing search response and show them in a local **Why this matched** disclosure. Opening it makes no LLM, Text Search, or Place Details request.
9. [x] Handle invalid LLM output, interpreter failure, unsupported provider capabilities, missing place data, and no-result searches without inventing criteria or retry loops.
   - Revalidate interpreted criteria against FoodFind's capability snapshot. Treat malformed output, disabled capabilities, and interpreter failures as safe errors that leave the current criteria unchanged.
   - Limit requested-time confirmation to Google's current seven-day hours horizon. Reject an out-of-range interpreted or edited window before searching Google.
   - Keep unsupported criteria visible for review but out of the place-search request. Search may continue explicitly with only the supported criteria.
   - Do not infer missing place data. Show unavailable values or an operational-status warning, and exclude missing values when an active filter requires provider confirmation.
   - Give no-result and failure states distinct recovery guidance. Never retry interpretation or place search automatically.

The LLM resolves language into a validated FoodFind intent; it does not call Google, construct field masks, or bypass application rules. Manual and natural-language input with the same normalized intent must produce the same Text Search semantics.

## Phase 5 — Map and current location

- **Priority:** P0
- **Status:** Complete

1. [x] Establish the Google Maps foundation.
   - Load Maps JavaScript once through a frontend adapter.
   - Handle missing-key, loading, and map-load failures.
   - Prepare for Google Advanced Markers with the development map ID.
   - Initializing or rendering the map must not make a Places search request.
2. [x] Display the search area and current results.
   - Show the selected search centre and radius boundary.
   - Add a marker for every returned result and fit the viewport to the relevant area.
   - Update the map when the location, radius, or completed search results change.
3. [x] Connect map markers and result cards.
   - Use provider and place ID as their shared identity.
   - Selecting either view highlights the corresponding marker and card.
   - Marker selection does not fetch details; **View details** remains explicit.
4. [x] Let users select or adjust the search location on the map.
   - A base-map click selects the location directly; no separate selection-mode button is required.
   - Convert the chosen point into the existing normalized selected-location model.
   - Use coordinates as its initial visible label, clear stale results, and wait for **Search**.
   - Panning and zooming alone never change the search location or trigger a search.
5. [x] Add **Use current location**.
   - Present it as the first option when the Location field is focused or edited.
   - Request browser permission only after the user selects it.
   - On success, set the normalized location, clear stale results, and recenter. Wait for **Search**.
   - Handle denial, timeout, unavailable location, and poor accuracy while keeping manual selection available.
   - **Near me** continues to mean the visible selected location and never silently requests device permission.
6. [x] Verify the complete map lifecycle.
   - Avoid recreating the map unnecessarily.
   - Confirm reloads, map movement, marker selection, and criteria edits make no Places request.
   - Mock Google Maps and browser geolocation in automated tests.
   - Document completed behavior and remaining limitations.

This phase completes the spatial experience after the result criteria are useful and proven. Every accepted map point and device location produces the same normalized selected-location model used by coordinates and autocomplete.

## Phase 6 — Evidence-supported food search

- **Priority:** P0
- **Status:** Paused after Step 1
- **Why paused:** Google does not expose complete menus or review evidence, and the available evidence is too incomplete or stale to support reliable food matching. Revisit when a better evidence source is identified.

1. [x] Run one controlled Google evidence probe for Toronto.
   - Submit one explicit food query through Text Search and request query-related review or contextual evidence in the same response.
   - Use the human-reviewed cases in [`docs/examples.md`](examples.md) to judge search quality. Add cases over time, but never hard-code behavior for a named business.
   - Confirm what Google actually returns for Toronto, whether the evidence is useful, the required attribution, and the billed SKU before building product behavior around it.
   - Stop after the probe and review the result. Do not assume experimental contextual content is available or useful.
   - The July 30, 2026 result and Step 1 conclusion are recorded in [`docs/phase-6-step-1-probe.md`](phase-6-step-1-probe.md).
   - A July 31 Pro-only pagination follow-up recovered one missing example on page 2 but not the other within 60 results. Consider on-demand pagination separately from evidence accuracy before Step 2.
2. [ ] If the probe is useful, build Iteration 3 as one conditional Enterprise + Atmosphere Text Search with review-supported ranking.
   - When list-wide evidence is needed, request it in the original Text Search. Do not make a Pro search followed by Place Details calls for every candidate.
   - Keep Place Details on demand for information needed only after the user opens one result.
   - Treat a relevant review mention as positive, potentially stale evidence—not verified menu availability. Promote supported results without removing a result merely because evidence is missing.
   - Define how evidence-supported ranking interacts with an explicit Distance or Rating sort before enabling it.
3. [ ] Add strict development and runtime cost safeguards.
   - Keep all automated tests on synthetic mocked responses. Never run live Google or supporting-provider calls in the normal test suite or CI.
   - Make live quality evaluation explicit and opt-in, with a configurable development limit initially set to 100 Enterprise + Atmosphere Text Searches per month.
   - Preserve the explicit **Search** boundary, prevent automatic retries and request loops, and use Cloud quotas and alerts where available.
   - Follow provider storage and attribution rules. Do not depend on persistent caching of Google content; stored Google Place IDs remain the permitted durable reference.
4. [ ] Separately evaluate Foursquare as a supporting evidence provider.
   - Compare one controlled Foursquare food search with the same query, location, and radius used for Google.
   - Review Toronto coverage, tips and tastes, licensing, attribution, pricing, entity matching, and whether the evidence improves results before integrating anything.
   - Do not add a second provider request to every FoodFind search until its value and cost are demonstrated.
5. [ ] Establish a provider-independent food-evidence layer.
   - Normalize evidence, source, age, and confidence separately from place discovery so Google, Foursquare, open data, restaurant websites, or restaurant-owned menus can be added or replaced later.
   - Keep provider-specific response parsing in adapters. Ranking rules consume normalized evidence and must never treat missing evidence as proof that a food is unavailable.
   - Preserve and expand [`docs/examples.md`](examples.md) as the evaluation set for each search-quality change.

This phase improves FoodFind's central search quality with evidence rather than unsupported exclusions. The first live probe is a gate: if Google evidence is unavailable, weak, or too costly, review the Foursquare option before choosing an implementation.

## Phase 7 — First-version cleanup

- **Priority:** P1
- **Status:** Paused after Step 1

1. [x] Improve desktop and mobile layouts, beginning with a location-first search flow, map placement, concise location guidance, and a responsive final search action.
2. [ ] Add keyboard and accessibility support.
3. [ ] Handle missing provider fields consistently.
4. [ ] Add compliant short-lived caching if useful.
5. [ ] Verify the complete journey with automated tests.
6. [ ] Fix usability and performance problems found during real use.

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

### Further food-search relevance and explanations

- Common-food searches can return weak matches. For example, Gigi's Street Eats appeared for **burger** even though FoodFind had no reliable evidence that it offered burgers.
- The current explanation is also too generic. A business that is clearly categorized as a burger restaurant can still receive **Burger availability is not verified**, making FoodFind appear uncertain about why the result matched.
- Phase 6 uses the observed Gigi's Street Eats and The Burger's Priest cases to evaluate review-supported evidence and ranking. Later work can add stronger menu or restaurant-owned evidence without treating provider categories or missing evidence as proof.

### Walking, transit, and driving travel times

- Show route-based travel-time estimates for each mode. Choose the routing provider and request-cost limits when this is built.

### Multi-turn conversational refinement

- Let users explicitly refine the current search with follow-up instructions while keeping a new search separate. Show the resulting changes before searching.

### Map production readiness

- Device geolocation works on localhost during development but requires HTTPS when FoodFind is deployed.
- Google Advanced Markers require a map ID. Use Google's `DEMO_MAP_ID` during development, then create and configure a FoodFind map ID before deployment.

### Dependency maintenance

- Upgrade `google-genai` before moving to Python 3.17 so it no longer relies on Python's deprecated internal `_UnionGenericAlias`.

### Other product enhancements

- Reconsider whether **Use current location** should search immediately after resolving the position instead of waiting for a separate **Search** action.
- Saved favourites
- Shortlists and comparison
- Reservation integration
- Native mobile application

### New smart searches can retain filters from an earlier request

- **Status:** Resolved — 2026-07-31
- Applying a new smart-search sentence could preserve filters created by the previous sentence even when the new request did not mention them.
- Observed example: after applying a burger search, applying **Chinese food** selected Chinese cuisine but left **Burger** selected under Common food. The following place search therefore still included burger even though it was absent from the new sentence.

### Exact natural-language rating comparisons

- **Status:** Resolved — 2026-07-31
- FoodFind preserves exact textual and symbolic **greater than** and **at least** rating comparisons from smart search. It sends Google a safe lower half-point prefilter and applies the exact comparison to returned ratings without another request.
- Example: **rating greater than 4.8** sends Google `minRating: 4.5`, then FoodFind keeps only returned places rated above 4.8.

## Current next task

Start Phase 6 Step 1 with one controlled Toronto evidence probe. Pause afterward to review the returned evidence, attribution requirements, and billed SKU before building Iteration 3.
