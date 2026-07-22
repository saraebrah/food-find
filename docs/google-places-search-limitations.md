# Google Places Search Provider Limitations

This is a numbered, living list of Google Places limitations that affect FoodFind. It separates restrictions imposed by Google from FoodFind decisions made to avoid misleading behavior.

FoodFind currently uses Text Search for food-business discovery. The Nearby Search limitations remain documented because they explain why FoodFind migrated away from that endpoint and may matter if the provider strategy is revisited.

The information was last reviewed on 2026-07-21. Google's API behavior, fields, billing tiers, and usage terms can change, so verify the linked documentation before implementing related work.

## 1. Nearby Search returns at most 20 results

Nearby Search accepts a `maxResultCount` from 1 through 20. Its response has no continuation token, so FoodFind cannot ask for results 21–40 from the same search.

These are Google's top candidates ranked by popularity or distance, not a complete list of every matching business. If Google returns 20 candidates and FoodFind's filters retain only 12, the MVP can show only those 12.

Changing the ranking, category, or geographic area would create a different search, not a true next batch. Combining such searches could produce duplicates, gaps, inconsistent ranking, and more API requests without guaranteeing complete coverage.

Reference: [Nearby Search request and response](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchNearby)

## 2. Nearby Search cannot express cuisine AND common food through primary types

The former Nearby Search implementation used Google's `includedTypes` for general place types such as restaurant, café, bar, and bakery. It used `includedPrimaryTypes` for both cuisines and common-food business categories.

Google treats multiple `includedPrimaryTypes` as **OR**. For example:

```json
{
  "includedPrimaryTypes": ["persian_restaurant", "kebab_shop"]
}
```

This means **Persian restaurant OR kebab shop**, not **a Persian restaurant that serves kebab**. A place has one primary type, so this filter cannot require both primary types at once.

FoodFind previously prevented cuisine and common-food filters from being active together to avoid suggesting an AND search that Google was not performing. The current Text Search implementation allows both concepts in one text query, although the result represents text relevance rather than verified menu availability.

Multiple choices within one facet can still intentionally mean OR. For example, Persian plus Italian cuisine means Persian **or** Italian. A general place type and one specialty restriction can still work together: Restaurant plus Persian requires both the restaurant type and Persian primary type.

References: [Nearby Search type restrictions](https://developers.google.com/maps/documentation/places/web-service/nearby-search#included-types) and [Google place types](https://developers.google.com/maps/documentation/places/web-service/place-types)

## 3. Some Nearby Search filters reduce an already limited candidate set

Nearby Search does not have request parameters for every FoodFind filter. Under the former implementation, Open now, minimum rating, Dine-in, and Takeout were read from Google's response and then filtered by FoodFind.

Google selects at most 20 candidates before this happens. For example, it might return 20 places but only 6 may explicitly confirm both Open now and Dine-in. Because Nearby Search has no next batch, FoodFind cannot refill the shortened list.

## 4. Text Search strictly accepts only one place type

Text Search's structured `includedType` parameter accepts one string, not a list. FoodFind can strictly request restaurants or cafés in one call, but cannot strictly request restaurants, cafés, bars, and bakeries together through this parameter.

FoodFind now handles this as follows:

- One selected type is sent through `includedType` with strict filtering.
- Several selected types are mentioned in `textQuery`. FoodFind requests Google's returned `types` and removes a place when its known types match none of the selections.
- Missing returned type data remains unconfirmed rather than being guessed.

This keeps one request, but Google still chooses the candidate set using text relevance rather than several strict included types.

Reference: [Text Search `includedType` and `strictTypeFiltering`](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/searchText)

## 5. Text Search restricts to a rectangle, not an exact circle

Text Search can strictly restrict results to a rectangular viewport, but not a circle. FoodFind searches a rectangle enclosing the selected circle, calculates each returned place's distance, and removes places outside the circle. Near a pole or across the antimeridian, it uses a circular location bias and applies the same exact local removal.

This preserves FoodFind's radius meaning, but some results in each batch may be discarded.

Reference: [Text Search location restriction](https://developers.google.com/maps/documentation/places/web-service/text-search#location-restriction)

## 6. Text Search pagination requires additional requests

Text Search returns up to 20 results in one batch. If Google supplies a `nextPageToken`, FoodFind can make another request for the next batch and append its valid results to the same screen. This permits automatic top-up or infinite scrolling without visible numbered website pages.

The current MVP intentionally requests only the first batch. Future continuation work will need a request limit and must stop when Google provides no continuation token, the limit is reached, or a request fails. Every additional batch will be another Google API request.

Pagination also does not guarantee a complete directory. Text Search remains relevance-ranked, and Google may stop providing continuation tokens before every potentially matching business has been exposed.

Reference: [Text Search pagination](https://developers.google.com/maps/documentation/places/web-service/text-search#specify-number-results-to-return-per-page)

## 7. Google categories and text relevance do not prove menu availability

A Google business category such as `kebab_shop` does not prove that a specific dish is currently available. Similarly, a Text Search match for `Persian restaurant serving kebab` is relevant evidence, not verified menu data.

Some useful concepts also lack a suitable structured Nearby Search type. FoodFind currently defers generic food trucks and pasta rather than mapping them to inaccurate substitutes. Verified dish availability will require restaurant-owned, licensed, or directly submitted menu data.

## 8. Data can be missing, stale, or costly to request

Google may not provide every field for every place, and returned information may be outdated. FoodFind must show that information is unknown rather than infer it.

Each search and continuation batch is an API request. The requested response fields also determine the highest Google billing tier used for that request, so broader searches and richer data can increase cost.
