# FoodFind Product Requirements Document

This document defines what FoodFind is, who it serves, and what the first version should do.

## Product overview

FoodFind is a web application that helps people discover suitable places to get food near a current or selected location.

Users can search with short keywords, natural-language requests, manual filters, or a combination of these methods. FoodFind converts each request into visible, editable search criteria and returns relevant restaurants, cafés, bars, bakeries, and similar businesses. Users can compare results and proceed to a business website, phone call, directions, or reservation page without repeating the search elsewhere.

A native mobile application may follow if the website proves useful and repeat mobile usage justifies it.

## Problem

Finding food often requires moving between maps, review platforms, restaurant websites, menus, reservation services, and navigation apps. FoodFind brings the information and next actions needed for this decision into one focused search experience.

## MVP user journey

1. Use the current location or select another location.
2. Choose a search radius.
3. Enter a request, set filters manually, or do both.
4. Review, filter, and sort matching businesses.
5. Open a result to see its details and why it matched.
6. Visit its website, call it, get directions, or follow a reservation link.

Example requests:

- `Thai food`
- `Pizza near Union Station`
- `Persian restaurants open now`
- `Cafés within a 15-minute walk`
- `Dine-in ramen sorted by rating`

## MVP requirements

### Search

- Current or selected location
- The selected-location control should eventually support:
  - place-name and address suggestions while the user types
  - selecting a suggested place or address
  - entering or pasting decimal latitude and longitude coordinates
  - selecting a point on the map once the map experience exists
  - using the device's current location with permission
- Every location input method must produce one visible, normalized selected location with a label and coordinates before a place search runs.
- Ambiguous, invalid, or unsupported location input must not silently start a search from an assumed location.
- Map
- The search box must accept short keywords, such as `Thai food`.
- The search box must accept natural-language requests, such as `Persian restaurants within three kilometres that are open now`.
- The interpreted request must be represented as visible, editable filters.
- Location or radius stated in the request must update the corresponding controls.
- Unsupported or ambiguous parts of a request must not silently become filters.
- The page should provide sample prompts that demonstrate supported searches.

### Filters and sorting

- Place type, such as restaurant, café, bar, bakery, or food truck
- Cuisine, such as Chinese, Italian, Persian, Thai, or Indian
- Common food, such as pizza, burgers, pasta, steak, ramen, or kebab
- Open now
- Dine-in and takeout
- Minimum rating
- Sort by distance or rating

Common-food filtering may initially use categories and keywords supported by the selected provider. FoodFind must not claim that a specific dish is available without reliable menu data.

### Results and place details

Show the following when available:

- Name and category
- Distance
- Source-labelled rating
- Hours and current open status
- Address
- Phone number
- Website
- Available service options
- A short explanation of why the result matched

Users must be able to open the business website, initiate a call on supported devices, open directions in Google Maps, and follow an available reservation link. Missing information must be identified as unavailable rather than inferred.

### Data

- Use a place-data provider instead of scraping Google or other platforms.
- Label ratings with their source and do not merge ratings from different platforms into one score.
- Obtain future menu data only from restaurant-owned, licensed, or directly submitted sources.
- Retain the source and last-checked time for menu data.

Start with one provider API, retrieve real results for a Toronto location, and replace or supplement it only if its data proves insufficient.

## Not included in the MVP

- Native mobile applications
- Multi-turn conversational assistance
- AI phone calls
- Direct reservation booking
- Automated menu scraping at scale
- User reviews inside FoodFind
- Complex personalization
- Food ordering or payment
- Per-person spending calculations

## First-version acceptance criteria

The first version is working when:

1. Users can search from a current or selected location within a chosen radius.
2. Supported typed criteria appear as editable controls.
3. Typed and manual inputs produce the same normalized search state.
4. Results respond correctly to every supported filter and sort option.
5. Each result displays available essential details, rating attribution, and its match reason.
6. Website, phone, directions, and available reservation actions open the correct destination.
7. Denied location access, missing data, no results, and provider failures have usable fallback states.
8. The core journey works on supported desktop and mobile browsers.


## Enhancements After MVP

### Easier comparison

- Walking, transit, and driving time
- Saved favourites
- Shared or comparable shortlists
- Incorrect-information reporting

### Menu and dish discovery

- Link to menus from appropriate sources, with the option to display the menu inside FF later
- Process menus so FoodFind can confirm that a place currently offers a requested food or dish

Menu intelligence may become an important advantage, but it should first be tested with a small number of restaurants in one Toronto area.

### Conversational assistance

- Turn the smart search box into a multi-turn conversation when useful
- Let users refine results with follow-up instructions instead of changing controls manually
- Let an AI assistant carry out requested steps, such as comparing options, checking reservation links, or preparing directions
- Ask for clarification when a request is incomplete or ambiguous
- Require conversational confirmation before consequential actions such as calling a business, sharing personal information, making a reservation, or cancelling one

Example:

> Find a highly rated Persian restaurant near me that is open tonight, choose the closest suitable option, and help me reserve a table for two at 7 p.m.

The assistant could complete the research and prepare the action without requiring the user to navigate through each screen or click multiple controls. The user would still approve the final reservation or call by replying in the conversation.


### Reservations

1. Link to restaurant reservation pages.
2. Link to reservation providers.
3. Integrate live availability if an approved partnership exists.
4. Evaluate agent-assisted calls only after simpler reservation methods are proven.

### Native mobile application

Consider a native application if the website attracts repeat mobile users and native features would materially improve their experience.

## Competitive direction

FoodFind should not try to replace Google Maps, Yelp, or OpenTable entirely.

**Yelp Places API** is a developer data service for searching local businesses and retrieving information such as categories, ratings, reviews, hours, and contact details. Its focus is supplying rich local-business data to consumer applications.

**OpenTable** is a restaurant discovery and reservation platform. Its focus is showing live availability at participating restaurants and allowing diners to book and manage tables.

**Sirved** is a menu-focused restaurant discovery service. Its focus is helping users search menus, cuisines, cravings, and dietary options to find restaurants serving particular food.

**BitePick** is a visual, dish-first discovery product. Its focus is helping users make a quick choice by swiping through individual nearby dishes with photos and prices.

FoodFind's opportunity is to make food discovery more focused:

- Combine useful filters in one place
- Include more kinds of food businesses
- Help users discover actual dishes, not only restaurant categories
- Make it clear why each result matches
- Connect discovery to immediate actions

## Immediate next step

Define the shared filter and sorting state, then add supported filters incrementally.
