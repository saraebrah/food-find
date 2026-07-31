# Phase 6 Step 1 — Google evidence probe

## Scope

On July 30, 2026, FoodFind evaluated every case then present in `docs/examples.md`. It used five valid query-and-radius combinations near **318 King St E, Toronto**:

- **creme brulee**, **chocolate cake**, **truffle pizza**, and **sushi taco** at 2 km;
- **crispy sushi taco** at 5 km.

Six explicitly confirmed Google Text Search requests were made in total. One initial **crispy sushi taco** request mistakenly used 2 km and was discarded; one corrective request used the documented 5 km radius.

- Every request returned at most 20 places and made no pagination request.
- Each requested place identity, ordinary reviews, and experimental query-related contextual content in one response.
- There were no retries, production search changes, or saved raw Google responses.
- Automated coverage uses mocked HTTP responses and never calls Google.

## Findings

- Each valid query returned 20 places and 20 corresponding contextual-content entries.
- The contextual `reviews` lists were empty, but review justifications contained short query-related highlights.
- The ordinary `places.reviews` lists contained five reviews per result, but those reviews were not reliably about the search term.
- Some review justifications directly supported the full query. Many others mentioned only part of it or gave generic food feedback.
- Query-related justifications can sometimes explain relevance, but they do not verify the current menu. A review can be old, and a business can stop serving an item.
- Evidence-based ranking cannot recover an expected business that is missing from Google's first 20 candidates.

### Comparison with `docs/examples.md`

| Query and business | Expected | Probe result | Assessment |
| --- | --- | --- | --- |
| creme brulee — The Rabbit Hole | Should not appear | Appeared because an older review mentioned the item | Did not match; stale-evidence risk |
| creme brulee — Muse Bistro + Bar | Should appear | Appeared with direct evidence | Matched |
| creme brulee — M Chá Bar | Should not appear | Did not appear | Matched |
| chocolate cake — CRAFT Beer Market | Should appear | Did not appear in the first 20 | Did not match |
| chocolate cake — Bellissimo Pizzeria | Should appear | Did not appear in the first 20 | Did not match |
| truffle pizza — Cantina Mercatto | Should not appear | Appeared with only generic pizza evidence | Did not match |
| truffle pizza — Pi Co. | Should appear | Appeared, but the returned evidence was generic | Matched result; weak evidence |
| sushi taco — Earls Financial District | Should not appear | Appeared with direct sushi-taco evidence | Recorded expectation needs rechecking |
| sushi taco — SUSHI YEON | Should appear | Appeared, but the returned evidence mentioned only sushi | Matched result; weak evidence |
| crispy sushi taco — Japan Taco | Should appear | Appeared first at the correct 5 km radius with sushi-and-taco evidence | Matched result; evidence did not confirm **crispy** |

Using the expectations exactly as recorded, five of ten examples matched. The Earls case may be stale or incorrect because the live evidence directly described sushi tacos; it should be rechecked before being used as a lasting evaluation case.

## Billing and attribution

Each request included `places.reviews`. Google classifies that field as **Text Search Enterprise + Atmosphere**, and a Text Search request is billed according to the highest-tier requested field. Six such requests were made, including the discarded-radius request. The Google Cloud billing report can take time to display individual requests.

If review evidence is displayed in FoodFind, the interface must:

- identify it as Google Maps content;
- credit the review author using the attribution returned by Google;
- link to the source review on Google Maps; and
- explain that reviews are selected or ordered by relevance.

## Step 1 conclusion

The probe was useful as research: it confirmed that Toronto receives query-related review justifications and exposed their limitations. It did not demonstrate consistent enough evidence to build Iteration 3 as currently planned.

Do not add review-supported production ranking yet. The evidence can be stale, partial, or generic, and two expected chocolate-cake businesses never entered the candidate set. Phase 6 remains paused after Step 1 while the next search-quality approach is reconsidered. Step 2 has not started.
