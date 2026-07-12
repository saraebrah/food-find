const searchButton = document.querySelector("#search-button");
const searchStatus = document.querySelector("#search-status");
const resultsSection = document.querySelector("#results-section");
const resultCount = document.querySelector("#result-count");
const placeResults = document.querySelector("#place-results");

if (
  !(searchButton instanceof HTMLButtonElement) ||
  !(searchStatus instanceof HTMLParagraphElement) ||
  !(resultsSection instanceof HTMLElement) ||
  !(resultCount instanceof HTMLParagraphElement) ||
  !(placeResults instanceof HTMLUListElement)
) {
  throw new Error("FoodFind search interface could not be initialized.");
}

function addText(parent, elementName, className, text) {
  const element = document.createElement(elementName);
  element.className = className;
  element.textContent = text;
  parent.append(element);
}

function renderPlaces(places) {
  placeResults.replaceChildren();

  for (const place of places) {
    const item = document.createElement("li");
    item.className = "place-card";

    addText(item, "h3", "place-name", place.name);

    const category = place.category || place.category_code;
    if (category) {
      addText(item, "p", "place-category", category);
    }

    if (place.address) {
      addText(item, "p", "place-address", place.address);
    }

    const source = place.provider.charAt(0).toUpperCase() + place.provider.slice(1);
    addText(item, "p", "place-source", `Source: ${source}`);
    placeResults.append(item);
  }

  const label = places.length === 1 ? "place" : "places";
  resultCount.textContent = `${places.length} ${label} found`;
  resultsSection.hidden = false;
}

searchButton.addEventListener("click", async () => {
  if (searchButton.disabled) {
    return;
  }

  searchButton.disabled = true;
  searchStatus.textContent = "Searching Toronto…";

  try {
    const response = await fetch("/api/places/search", {
      method: "POST",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Search failed with status ${response.status}`);
    }

    const places = await response.json();
    renderPlaces(places);
    searchStatus.textContent =
      places.length === 0 ? "No places found." : "Search complete.";
  } catch (error) {
    console.error(error);
    resultsSection.hidden = true;
    searchStatus.textContent = "Search is unavailable. Please try again.";
  } finally {
    searchButton.disabled = false;
  }
});
