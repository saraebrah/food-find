# FoodFind (FF) — Working Product Proposal

## The idea

FoodFind is a website that helps users discover places to get food near a current or selected location.

The user chooses a location and search radius. FoodFind returns relevant restaurants, cafés, bars, bakeries, and other food businesses. Users can type a simple or detailed request in a smart search box, select the filters manually, or combine both methods. They can then compare the results and take the next action without repeating the search elsewhere.

The website will be built first. A native mobile application will be considered after the website proves useful.

## The problem

Finding food often requires moving between several products:

- A map to find nearby places
- Reviews to judge them
- Restaurant websites to inspect menus
- Another service to make a reservation
- A navigation app to get there

FoodFind aims to make that decision simpler by bringing the most useful information and actions into one clear search experience.

## Core user experience

1. Use the current location or choose another location.
2. Select a search radius.
3. Enter a request in the smart search box or choose filters manually.
4. View, adjust, and sort the results.
5. Open a place to see its important details.
6. Visit its website, call it, get directions, or follow a reservation link.

The smart search box accepts both short keywords and natural-language requests. For example, the user can enter either:

> Thai food

or:

> Show me Thai restaurants and cafés within three kilometres that are open now and offer dine-in service. Sort them by distance.

FoodFind should translate the request into visible, editable filters. If the request includes a location or radius, those controls should update as well. Manual filters and typed requests use the same search system, so the user can move between them without starting over.

The search page can show sample prompts to help users understand what they can ask, such as:

- `Pizza near Union Station`
- `Persian restaurants open now`
- `Cafés within a 15-minute walk`
- `Dine-in ramen sorted by rating`

## First version: usable MVP

The first version should contain only the features needed to test whether people find FoodFind useful:

- Current or selected location
- Search radius
- Smart search box for short keywords or detailed natural-language requests
- Sample prompts
- Manual filters synchronized with the interpreted request
- Food-business results
- Place-type filter: restaurant, café, bar, bakery, food truck, and similar types
- Cuisine filter, such as Chinese, Italian, Persian, Thai, or Indian
- Common-food filter, such as pizza, burgers, pasta, steak, ramen, or kebab
- Open-now filter
- Dine-in and takeout filters
- Rating filter
- Sort by distance or rating
- Basic place details: name, category, source-labelled rating, hours, address, call option (phone), and website
- Open directions in Google Maps

In the MVP, the smart search box only needs to interpret the request and apply visible filters. It does not need to maintain a conversation or behave like a general-purpose AI assistant. Common-food filtering can initially use categories and keywords supported by the selected data provider; menu-based matching will improve its accuracy later. The user interface (UI) can be plain. Reliability and usability matter more than appearance at this stage.

## Later iterations

### Iteration 2 — Make choosing easier

- Walking, transit, or driving time
- Save favourites
- Share or compare a shortlist
- Report incorrect information

### Iteration 3 — Menu and dish discovery

- Link to menus from appropriate sources, with the option to display the menu inside FF later
- Process menus so FoodFind can confirm that a place currently offers a requested food or dish
- Expand from common-food categories to specific menu-item searches

Menu intelligence may become an important advantage, but it should first be tested with a small number of restaurants in one Toronto area.

### Iteration 4 — Conversational and agentic assistance

- Turn the smart search box into a multi-turn conversation when useful
- Let users refine results with follow-up instructions instead of changing controls manually
- Let an AI assistant carry out requested steps, such as comparing options, checking reservation links, or preparing directions
- Ask for clarification when a request is incomplete or ambiguous
- Require conversational confirmation before consequential actions such as calling a business, sharing personal information, making a reservation, or cancelling one

Example:

> Find a highly rated Persian restaurant near me that is open tonight, choose the closest suitable option, and help me reserve a table for two at 7 p.m.

The assistant could complete the research and prepare the action without requiring the user to navigate through each screen or click multiple controls. The user would still approve the final reservation or call by replying in the conversation.

### Iteration 5 — Reservations

Build reservation features in this order:

1. Link to the restaurant's reservation page.
2. Link to providers such as OpenTable.
3. Integrate live availability if a provider partnership becomes available.
4. Consider an AI agent that calls restaurants only after the simpler methods are proven.

### Iteration 6 — Mobile application

Consider a native application if the website attracts repeat mobile users and mobile-specific features would materially improve their experience.

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

## Data approach

The MVP should use an approved place-data provider rather than scraping Google or other platforms.

Before choosing a provider, FoodFind should compare coverage and cost in one Toronto test area. No provider should be assumed to contain every business.

Menus should initially come from restaurant-owned sources, licensed sources, or direct restaurant submissions. Every menu should retain its source and last-checked time.

Ratings may come from sources such as Google, Yelp, or Uber Eats when an approved API, licence, or partnership permits their use. Every rating should be labelled with its source—for example, “Google: 4.5” or “Uber Eats: 4.7.” FoodFind should not combine ratings from different platforms into one score unless it later develops and clearly explains a reliable method.

## What is not part of the MVP

- Native mobile applications
- AI phone calls
- Automated menu scraping at scale
- User reviews written inside FoodFind
- Complex personalization
- Food ordering and payment
- Spending-per-person calculations

A broad price-level filter can be considered later, but spending analysis is not a core FoodFind feature.

## Immediate next step

Choose one small Toronto test area and compare available place-data providers against a manually prepared list of local food businesses.

Once the data source is understood, the next proposal revision should define the exact MVP screens and acceptance criteria.


## Uncleaned Draft
I want you to organize this and make it readbale and usable. I'm writing whatever comes to my head.
I want you to list the features in order of it's difficulty and precedence in terms of development.
Ideally i want to build a mobile app, but for now i decided to first bulid the website and later after reconsideration invest in buliding the mobile app.
I want to bulid it sequesntionally and in iterations. Let us also do it in iteration. maybe first, tell me 
1. if there is already such a service out there
2. if the answer to 1 is yes, what can be my competetive advantage?
3. Is there anything you think I should add to the features?
I also want to give it a name, a palceholder maybe so that it is eaier to refer to it.
I think it needs a lot of APIs and maybe screen scraping. Accessing place's website, if any, finding the menu from it, or if it doesnt have a website, using the public pictures of the menu from google as the proxy for menu. 
It needs a UI but that is not my focus right now, I am okay to sacrifice prettiness of the website to its usability and features. 


I want to create a product that looks at the location that is provided by the user, either current location or a picked location, in addition to a search radius. 
I want it to list all places where the user can go get food. 
I want it to provide the following filtering:
- type of the place, if a resturant, if aa cafe, if a bar, ...
- if it's only takeout or both takeout and dine in
- type of the cusine, tai, persion, indian, italian
- if they offere common foods in their menue, like pizza, burger, steak, pasta, ...
- the range of the spending per person, can use the one that google provides, or directly looking at the menue and calculate it based on a formula

When user click on an aoption, they would be able to:
- visit the place's website, if there is a website for i
- call directly to reserve a table or leave your info, like how many ppl at what time, then AI agent would call and reserve the table on behalf of the user 
- click a button to get the direction from the google map, like the user would be directed to google maps and will be able to check the distance by public transport, car, or foot

I want it to let the user sort based on 
- distance
- rating (maybe from google, or uber eats)