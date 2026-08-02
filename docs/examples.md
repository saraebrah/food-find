# Search-quality examples

This file is FoodFind's growing set of human-reviewed search examples. It is not limited to the Phase 6 probe.

Review the relevant examples whenever changing any part of search behavior, including:

- understanding the user's request;
- building the provider query;
- choosing or interpreting provider data;
- matching, filtering, and ranking results; and
- explaining why a result matches.

Use the examples to evaluate general search behavior. Do not hard-code rules for a named business. Expected results are based on the available evidence when an example is added, so recheck evidence that may have changed or is unclear.

## Example 1
Search: creme brulee
Location: 318 King St E, Toronto
Radius: 2 km

Business: The Rabbit Hole
Address or Google Maps link: 21 Adelaide St W, Toronto, ON M5H 1L6
Expected: should not appear
Reason: 
Evidence, if available: does not appears on the menu from the website

## Example 2
Search: creme brulee
Location: 318 King St E, Toronto
Radius: 2 km

Business: Muse Bistro + Bar
Address or Google Maps link: 203 Jarvis St, Toronto, ON M5B 0E7
Expected: should appear
Reason: 
Evidence, if available: appears on the menu from Google Maps

## Example 3
Search: creme brulee
Location: 318 King St E, Toronto
Radius: 2 km

Business: M Chá Bar (Dundas & Bay) x ORYZA Sushi
Address or Google Maps link: 120 Dundas St W, Toronto, ON M5G 1C3
Expected: should not appear
Reason: 
Evidence, if available: does not appear on the menu from Google Maps

## Example 4
Search: chocolate cake
Location: 318 King St E, Toronto
Radius: 2 km

Business: CRAFT Beer Market Toronto
Address or Google Maps link: 1 Adelaide St E, Toronto, ON M5C 2V9
Expected: should appear
Reason: 
Evidence, if available: menu from Google Maps inidicates a dessert that is a brownie, which functionally, is a chocolate dessert/cake variation

## Example 5
Search: chocolate cake
Location: 318 King St E, Toronto
Radius: 2 km

Business: Bellissimo Pizzeria & Ristorante
Address or Google Maps link: 164 The Esplanade, Toronto, ON M5A 4H2
Expected: should appear
Reason: chocolate cake appears in the reviews
Evidence, if available: appears on the menu from Google Maps

## Example 6
Search: truffle pizza
Location: 318 King St E, Toronto
Radius: 2 km

Business: Cantina Mercatto
Address or Google Maps link: 20 Wellington St E #1, Toronto, ON M5E 1C5
Expected: should not appear
Reason: menu from Google Maps indicates mushroom pizza, but that is not truffle pizza
Evidence, if available:

## Example 7
Search: truffle pizza
Location: 318 King St E, Toronto
Radius: 2 km

Business: Pi Co.
Address or Google Maps link: 60 Colborne St, Toronto, ON M5E 0B7
Expected: should appear
Reason: although the exact truffle pizza is not found anywhere, but they have a pizza flavored with truffle, which also includes mushrooms
Evidence, if available:

## Example 8
Search: sushi taco
Location: 318 King St E, Toronto
Radius: 2 km

Business: Earls Kitchen + Bar - Financial District (King & University)
Address or Google Maps link: 150 King St W #100, Toronto, ON M5H 1J9
Expected: should not appear
Reason: the place offers taco and sushi separately, but there is no indication of sushi taco in the Google Maps menu 
Evidence, if available:

## Example 9
Search: sushi taco
Location: 318 King St E, Toronto
Radius: 2 km

Business: SUSHI YEON
Address or Google Maps link: Retail 8, 59 Merchants' Wharf Unit G, Toronto, ON M5A 0R6
Expected: should appear
Reason: 
Evidence, if available: appears on the menu from Google Maps

## Example 10
Search: crispy sushi taco
Location: 318 King St E, Toronto
Radius: 5 km

Business: Japan Taco
Address or Google Maps link: 252 Queen St W, Toronto, ON M5T 2X9
Expected: should appear
Reason: reviews mention crispy which is the important part of the search, it's not just sushi taco, it's crispy sushi taco
Evidence, if available:

## Example 11
Search: steak
Location: 318 King St E, Toronto
Radius: 1 km

Business: Domino's Pizza
Address or Google Maps link: 67 Richmond St E, Toronto, ON M5C 0B7
Expected: should not appear
Reason:
Evidence, if available:
