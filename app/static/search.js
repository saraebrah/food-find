const searchButton = document.querySelector("#search-button");
const locationInput = document.querySelector("#location-input");
const radiusSelect = document.querySelector("#radius-select");
const searchStatus = document.querySelector("#search-status");
const suggestionsPanel = document.querySelector("#suggestions-panel");
const locationSuggestions = document.querySelector("#location-suggestions");
const resultsSection = document.querySelector("#results-section");
const resultCount = document.querySelector("#result-count");
const placeResults = document.querySelector("#place-results");

if (
  !(searchButton instanceof HTMLButtonElement) ||
  !(locationInput instanceof HTMLInputElement) ||
  !(radiusSelect instanceof HTMLSelectElement) ||
  !(searchStatus instanceof HTMLParagraphElement) ||
  !(suggestionsPanel instanceof HTMLElement) ||
  !(locationSuggestions instanceof HTMLUListElement) ||
  !(resultsSection instanceof HTMLElement) ||
  !(resultCount instanceof HTMLParagraphElement) ||
  !(placeResults instanceof HTMLUListElement)
) {
  throw new Error("FoodFind search interface could not be initialized.");
}

let selectedLocation = parseCoordinates(locationInput.value);
let autocompleteTimer = null;
let autocompleteController = null;
let sessionToken = crypto.randomUUID();

function parseCoordinates(value) {
  const parts = value.split(",");
  if (parts.length !== 2) {
    return null;
  }

  const latitude = Number(parts[0].trim());
  const longitude = Number(parts[1].trim());

  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    latitude < -90 ||
    latitude > 90 ||
    longitude < -180 ||
    longitude > 180
  ) {
    return null;
  }

  return {
    label: `${latitude}, ${longitude}`,
    latitude,
    longitude,
  };
}

function looksLikeCoordinatePair(value) {
  const parts = value.split(",");
  return (
    parts.length === 2 &&
    Number.isFinite(Number(parts[0].trim())) &&
    Number.isFinite(Number(parts[1].trim()))
  );
}

function addText(parent, elementName, className, text) {
  const element = document.createElement(elementName);
  element.className = className;
  element.textContent = text;
  parent.append(element);
}

function hideSuggestions() {
  locationSuggestions.replaceChildren();
  suggestionsPanel.hidden = true;
  locationInput.setAttribute("aria-expanded", "false");
}

function clearResults() {
  placeResults.replaceChildren();
  resultCount.textContent = "";
  resultsSection.hidden = true;
}

function providerName(provider) {
  if (provider === "google") {
    return "Google Maps";
  }

  return provider.charAt(0).toUpperCase() + provider.slice(1);
}

function formatRadius(radiusMeters) {
  if (radiusMeters < 1_000) {
    return `${radiusMeters} m`;
  }

  return `${radiusMeters / 1_000} km`;
}

function renderPlaces(places) {
  clearResults();

  if (places.length === 0) {
    return;
  }

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

    addText(item, "p", "place-source", `Source: ${providerName(place.provider)}`);
    placeResults.append(item);
  }

  const label = places.length === 1 ? "place" : "places";
  resultCount.textContent = `${places.length} ${label} found`;
  resultsSection.hidden = false;
}

async function resolveSuggestion(suggestion) {
  if (autocompleteController !== null) {
    autocompleteController.abort();
  }

  hideSuggestions();
  searchButton.disabled = true;
  locationInput.disabled = true;
  searchStatus.textContent = `Selecting ${suggestion.label}…`;
  const resolvingSessionToken = sessionToken;

  try {
    const response = await fetch("/api/locations/resolve", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        provider_place_id: suggestion.provider_place_id,
        label: suggestion.label,
        session_token: resolvingSessionToken,
      }),
    });

    if (response.status === 422) {
      searchStatus.textContent = "That location selection is invalid. Please try again.";
      return;
    }

    if (!response.ok) {
      throw new Error(`Location resolution failed with status ${response.status}`);
    }

    selectedLocation = await response.json();
    locationInput.value = selectedLocation.label;
    sessionToken = crypto.randomUUID();
    searchStatus.textContent = "Location selected. Select search when you are ready.";
    searchButton.disabled = false;
  } catch (error) {
    console.error(error);
    selectedLocation = null;
    searchStatus.textContent = "That location could not be selected. Please try again.";
  } finally {
    locationInput.disabled = false;
  }
}

function renderSuggestions(suggestions) {
  locationSuggestions.replaceChildren();

  for (const suggestion of suggestions) {
    const item = document.createElement("li");
    item.setAttribute("role", "option");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion-button";
    button.textContent = suggestion.label;
    button.addEventListener("click", () => resolveSuggestion(suggestion));

    item.append(button);
    locationSuggestions.append(item);
  }

  suggestionsPanel.hidden = suggestions.length === 0;
  locationInput.setAttribute(
    "aria-expanded",
    suggestions.length === 0 ? "false" : "true",
  );
}

async function requestSuggestions() {
  const query = locationInput.value.trim();
  if (query.length < 3 || looksLikeCoordinatePair(query)) {
    return;
  }

  if (autocompleteController !== null) {
    autocompleteController.abort();
  }

  const requestController = new AbortController();
  autocompleteController = requestController;
  const requestSessionToken = sessionToken;

  try {
    const response = await fetch("/api/locations/autocomplete", {
      method: "POST",
      signal: requestController.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        session_token: requestSessionToken,
      }),
    });

    if (response.status === 422) {
      searchStatus.textContent = "Enter a valid location search.";
      return;
    }

    if (!response.ok) {
      throw new Error(`Autocomplete failed with status ${response.status}`);
    }

    const suggestions = await response.json();
    if (locationInput.value.trim() !== query) {
      return;
    }

    renderSuggestions(suggestions);
    searchStatus.textContent =
      suggestions.length === 0
        ? "No matching locations found."
        : "Choose a suggested location.";
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return;
    }

    console.error(error);
    hideSuggestions();
    searchStatus.textContent = "Location suggestions are unavailable. Please try again.";
  } finally {
    if (autocompleteController === requestController) {
      autocompleteController = null;
    }
  }
}

searchButton.addEventListener("click", async () => {
  if (searchButton.disabled) {
    return;
  }

  const coordinateLocation = parseCoordinates(locationInput.value);
  if (coordinateLocation !== null) {
    selectedLocation = coordinateLocation;
    locationInput.value = coordinateLocation.label;
  }

  if (selectedLocation === null) {
    searchStatus.textContent =
      "Choose a suggested location or enter valid decimal coordinates.";
    locationInput.focus();
    return;
  }

  const location = { ...selectedLocation };
  const radiusMeters = Number(radiusSelect.value);
  if (
    !Number.isFinite(radiusMeters) ||
    radiusMeters < 100 ||
    radiusMeters > 50_000
  ) {
    searchStatus.textContent = "Choose a valid search radius.";
    return;
  }

  hideSuggestions();
  clearResults();
  searchButton.disabled = true;
  locationInput.disabled = true;
  radiusSelect.disabled = true;
  searchStatus.textContent =
    `Searching within ${formatRadius(radiusMeters)} of ${location.label}…`;

  try {
    const response = await fetch("/api/places/search", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ location, radius_meters: radiusMeters }),
    });

    if (response.status === 422) {
      searchStatus.textContent = "Check the selected location and search radius.";
      return;
    }

    if (!response.ok) {
      throw new Error(`Search failed with status ${response.status}`);
    }

    const places = await response.json();
    renderPlaces(places);
    searchStatus.textContent =
      places.length === 0 ? "No places found." : "Search complete.";
  } catch (error) {
    console.error(error);
    clearResults();
    searchStatus.textContent = "Search is temporarily unavailable. Please try again.";
  } finally {
    searchButton.disabled = false;
    locationInput.disabled = false;
    radiusSelect.disabled = false;
  }
});

locationInput.addEventListener("input", () => {
  selectedLocation = null;
  clearResults();
  hideSuggestions();

  if (autocompleteTimer !== null) {
    clearTimeout(autocompleteTimer);
  }
  if (autocompleteController !== null) {
    autocompleteController.abort();
  }

  const coordinateLocation = parseCoordinates(locationInput.value);
  if (coordinateLocation !== null) {
    selectedLocation = coordinateLocation;
    searchButton.disabled = false;
    searchStatus.textContent = "Coordinates ready. Select search when you are ready.";
    return;
  }

  if (looksLikeCoordinatePair(locationInput.value)) {
    searchButton.disabled = true;
    searchStatus.textContent =
      "Latitude must be from -90 to 90 and longitude from -180 to 180.";
    return;
  }

  searchButton.disabled = true;
  if (locationInput.value.trim().length < 3) {
    searchStatus.textContent = "Enter at least three characters for suggestions.";
    return;
  }

  searchStatus.textContent = "Finding location suggestions…";
  autocompleteTimer = setTimeout(requestSuggestions, 350);
});

radiusSelect.addEventListener("change", () => {
  clearResults();
  const radiusLabel = formatRadius(Number(radiusSelect.value));
  searchStatus.textContent =
    selectedLocation === null
      ? `Radius set to ${radiusLabel}. Choose a location to continue.`
      : `Radius set to ${radiusLabel}. Select search when you are ready.`;
});
