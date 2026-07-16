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
const detailsByPlace = new Map();
const detailRequestsByPlace = new Map();

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
  for (const request of detailRequestsByPlace.values()) {
    request.controller.abort();
  }
  detailRequestsByPlace.clear();
  detailsByPlace.clear();
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

function formatDistance(distanceMeters) {
  if (!Number.isFinite(distanceMeters) || distanceMeters < 0) {
    return "Distance unavailable";
  }

  if (distanceMeters < 1_000) {
    return `${Math.round(distanceMeters)} m away`;
  }

  const distanceKilometers = distanceMeters / 1_000;
  const decimalPlaces = distanceKilometers < 10 ? 1 : 0;
  return `${distanceKilometers.toFixed(decimalPlaces)} km away`;
}

function placeKey(place) {
  return `${place.provider}:${place.provider_place_id}`;
}

function phoneHref(phoneNumber) {
  const prefix = phoneNumber.trim().startsWith("+") ? "+" : "";
  const dialableNumber = phoneNumber.replace(/[^\d*#;,]/g, "");
  return dialableNumber === "" ? null : `tel:${prefix}${dialableNumber}`;
}

function websiteHref(websiteUri) {
  if (typeof websiteUri !== "string" || websiteUri.trim() === "") {
    return null;
  }

  try {
    const url = new URL(websiteUri);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
}

function directionsHref(place) {
  const latitude = place.coordinates?.latitude;
  const longitude = place.coordinates?.longitude;
  const hasCoordinates =
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180;
  const destination = hasCoordinates
    ? `${latitude},${longitude}`
    : place.address || place.name;

  if (!destination) {
    return null;
  }

  const url = new URL("https://www.google.com/maps/dir/");
  url.searchParams.set("api", "1");
  url.searchParams.set("destination", destination);
  if (
    place.provider === "google" &&
    typeof place.provider_place_id === "string" &&
    place.provider_place_id !== ""
  ) {
    url.searchParams.set("destination_place_id", place.provider_place_id);
  }
  return url.href;
}

function renderPlaceDetails(container, details, businessStatus) {
  container.replaceChildren();
  container.dataset.state = "loaded";

  if (Number.isFinite(details.rating)) {
    const ratingCount = Number.isInteger(details.user_rating_count)
      ? ` from ${details.user_rating_count.toLocaleString()} ratings`
      : "";
    addText(
      container,
      "p",
      "place-rating",
      `${providerName(details.provider)} rating: ${details.rating}/5${ratingCount}`,
    );
  } else {
    addText(container, "p", "place-missing", "Rating unavailable");
  }

  const openStatus =
    details.open_now === true
      ? "Open now"
      : details.open_now === false
        ? "Closed now"
        : "Current open status unavailable";
  addText(
    container,
    "p",
    details.open_now == null ? "place-missing" : "place-open-status",
    openStatus,
  );

  if (Array.isArray(details.opening_hours) && details.opening_hours.length > 0) {
    addText(container, "h4", "place-detail-heading", "Hours");
    const hoursList = document.createElement("ul");
    hoursList.className = "place-hours";
    for (const description of details.opening_hours) {
      addText(hoursList, "li", "place-hours-row", description);
    }
    container.append(hoursList);
  } else {
    addText(container, "p", "place-missing", "Hours unavailable");
  }

  if (details.phone_number) {
    const callHref = phoneHref(details.phone_number);
    const phoneActions = document.createElement("div");
    phoneActions.className = "place-phone-actions";

    if (callHref !== null) {
      const callLink = document.createElement("a");
      callLink.className = "place-action place-call-action";
      callLink.href = callHref;
      callLink.textContent = businessStatus == null ? "Call to confirm" : "Call";
      phoneActions.append(callLink);
    }

    const phoneNumber = document.createElement("p");
    phoneNumber.id = `${container.id}-phone-number`;
    phoneNumber.className = "place-phone";
    phoneNumber.textContent = `Phone number: ${details.phone_number}`;
    phoneNumber.hidden = true;

    const showNumberButton = document.createElement("button");
    showNumberButton.type = "button";
    showNumberButton.className = "place-show-number-button";
    showNumberButton.textContent = "Show number";
    showNumberButton.setAttribute("aria-controls", phoneNumber.id);
    showNumberButton.setAttribute("aria-expanded", "false");
    showNumberButton.addEventListener("click", () => {
      phoneNumber.hidden = !phoneNumber.hidden;
      if (phoneNumber.hidden) {
        showNumberButton.textContent = "Show number";
        showNumberButton.setAttribute("aria-expanded", "false");
      } else {
        showNumberButton.textContent = "Hide number";
        showNumberButton.setAttribute("aria-expanded", "true");
      }
    });

    phoneActions.append(showNumberButton);
    container.append(phoneActions, phoneNumber);
  } else {
    addText(container, "p", "place-missing", "Phone unavailable");
  }

  const safeWebsiteHref = websiteHref(details.website_uri);
  if (safeWebsiteHref !== null) {
    const websiteRow = document.createElement("p");
    websiteRow.className = "place-website";
    websiteRow.append("Website: ");

    const websiteLink = document.createElement("a");
    websiteLink.className = "place-website-link";
    websiteLink.href = safeWebsiteHref;
    websiteLink.target = "_blank";
    websiteLink.rel = "noopener noreferrer";
    websiteLink.textContent = "Visit website";
    websiteRow.append(websiteLink);
    container.append(websiteRow);
  } else {
    addText(container, "p", "place-missing", "Website unavailable");
  }
}

async function requestPlaceDetails(place) {
  const key = placeKey(place);
  if (detailsByPlace.has(key)) {
    return detailsByPlace.get(key);
  }

  if (detailRequestsByPlace.has(key)) {
    return detailRequestsByPlace.get(key).promise;
  }

  const controller = new AbortController();
  const promise = (async () => {
    const response = await fetch("/api/places/details", {
      method: "POST",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        provider: place.provider,
        provider_place_id: place.provider_place_id,
      }),
    });

    if (!response.ok) {
      throw new Error(`Place details failed with status ${response.status}`);
    }

    const details = await response.json();
    detailsByPlace.set(key, details);
    return details;
  })();

  detailRequestsByPlace.set(key, { controller, promise });
  try {
    return await promise;
  } finally {
    if (detailRequestsByPlace.get(key)?.promise === promise) {
      detailRequestsByPlace.delete(key);
    }
  }
}

function addDetailsControl(item, place, resultIndex) {
  const detailsId = `place-details-${resultIndex}`;
  const detailsContainer = document.createElement("div");
  detailsContainer.id = detailsId;
  detailsContainer.className = "place-details";
  detailsContainer.hidden = true;
  detailsContainer.setAttribute("aria-live", "polite");

  const button = document.createElement("button");
  button.type = "button";
  button.className = "place-details-button";
  button.textContent = "View details";
  button.setAttribute("aria-controls", detailsId);
  button.setAttribute("aria-expanded", "false");

  button.addEventListener("click", async () => {
    if (!detailsContainer.hidden && detailsContainer.dataset.state !== "error") {
      detailsContainer.hidden = true;
      button.textContent = "View details";
      button.setAttribute("aria-expanded", "false");
      return;
    }

    detailsContainer.hidden = false;
    detailsContainer.dataset.state = "loading";
    detailsContainer.replaceChildren();
    addText(detailsContainer, "p", "place-detail-status", "Loading details…");
    button.disabled = true;
    button.textContent = "Loading…";
    button.setAttribute("aria-expanded", "true");

    try {
      const details = await requestPlaceDetails(place);
      renderPlaceDetails(detailsContainer, details, place.business_status);
      button.textContent = "Hide details";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      console.error(error);
      detailsContainer.dataset.state = "error";
      detailsContainer.replaceChildren();
      addText(
        detailsContainer,
        "p",
        "place-detail-error",
        "Details are temporarily unavailable. Please try again.",
      );
      button.textContent = "Try again";
    } finally {
      button.disabled = false;
    }
  });

  item.append(button, detailsContainer);
}

function addDirectionsAction(item, place) {
  const href = directionsHref(place);
  if (href === null) {
    return;
  }

  const directionsLink = document.createElement("a");
  directionsLink.className = "place-action place-directions-link";
  directionsLink.href = href;
  directionsLink.target = "_blank";
  directionsLink.rel = "noopener noreferrer";
  directionsLink.textContent = "Get directions";
  item.append(directionsLink);
}

function renderPlaces(places) {
  clearResults();

  if (places.length === 0) {
    return;
  }

  for (const [resultIndex, place] of places.entries()) {
    const item = document.createElement("li");
    item.className = "place-card";

    addText(item, "h3", "place-name", place.name);

    const category = place.category || place.category_code || "Category unavailable";
    addText(
      item,
      "p",
      place.category || place.category_code ? "place-category" : "place-missing",
      category,
    );

    addText(item, "p", "place-distance", formatDistance(place.distance_meters));

    addText(
      item,
      "p",
      place.address ? "place-address" : "place-missing",
      place.address || "Address unavailable",
    );

    if (place.business_status == null) {
      addText(
        item,
        "p",
        "place-status-warning",
        "Operational status unconfirmed. Call to confirm before visiting.",
      );
    }

    addText(item, "p", "place-source", `Source: ${providerName(place.provider)}`);
    addDirectionsAction(item, place);
    addDetailsControl(item, place, resultIndex);
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
