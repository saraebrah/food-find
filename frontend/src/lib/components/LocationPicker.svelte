<script lang="ts">
	import { onDestroy, untrack } from 'svelte';

	import { ApiError, autocompleteLocations, resolveLocation } from '$lib/api';
	import { looksLikeCoordinatePair, parseCoordinates } from '$lib/search';
	import type { LocationSuggestion, SelectedLocation } from '$lib/types';

	interface Props {
		disabled: boolean;
		initialLocation: SelectedLocation;
		onLocationChange: (location: SelectedLocation | null) => void;
		onStatus: (message: string) => void;
		onClearResults: () => void;
	}

	let { disabled, initialLocation, onLocationChange, onStatus, onClearResults }: Props = $props();
	let inputValue = $state(untrack(() => initialLocation.label));
	let suggestions = $state<LocationSuggestion[]>([]);
	let resolving = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let controller: AbortController | null = null;
	let requestNumber = 0;
	let sessionToken = crypto.randomUUID();

	onDestroy(() => {
		if (timer !== null) clearTimeout(timer);
		controller?.abort();
	});

	function resetPendingRequest() {
		if (timer !== null) {
			clearTimeout(timer);
			timer = null;
		}
		controller?.abort();
		controller = null;
		requestNumber += 1;
	}

	function handleInput(event: Event) {
		inputValue = (event.currentTarget as HTMLInputElement).value;
		suggestions = [];
		resetPendingRequest();
		onClearResults();

		const coordinates = parseCoordinates(inputValue);
		if (coordinates) {
			onLocationChange(coordinates);
			onStatus('Coordinates are ready. Select Search when you are ready.');
			return;
		}

		onLocationChange(null);
		const query = inputValue.trim();
		if (looksLikeCoordinatePair(query)) {
			onStatus('Enter valid coordinates as latitude, longitude.');
			return;
		}
		if (query.length < 3) {
			onStatus('Type at least 3 characters to find a location.');
			return;
		}

		onStatus('Finding location suggestions…');
		timer = setTimeout(() => void loadSuggestions(query), 350);
	}

	async function loadSuggestions(query: string) {
		timer = null;
		const currentRequest = ++requestNumber;
		controller = new AbortController();
		try {
			const matches = await autocompleteLocations(query, sessionToken, controller.signal);
			if (currentRequest !== requestNumber || query !== inputValue.trim()) return;
			suggestions = matches;
			onStatus(
				matches.length > 0
					? 'Choose a location from the suggestions.'
					: 'No location suggestions found. Try a more specific place or address.'
			);
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			if (currentRequest !== requestNumber) return;
			console.error(error instanceof ApiError ? error.message : error);
			onStatus('Location suggestions are temporarily unavailable. Try again.');
		} finally {
			if (currentRequest === requestNumber) controller = null;
		}
	}

	async function selectSuggestion(suggestion: LocationSuggestion) {
		resetPendingRequest();
		resolving = true;
		suggestions = [];
		onStatus('Selecting location…');
		controller = new AbortController();
		try {
			const location = await resolveLocation(suggestion, sessionToken, controller.signal);
			inputValue = location.label;
			onLocationChange(location);
			onClearResults();
			onStatus('Location selected. Select Search when you are ready.');
			sessionToken = crypto.randomUUID();
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			onLocationChange(null);
			onStatus('That location could not be selected. Try another suggestion.');
		} finally {
			resolving = false;
			controller = null;
		}
	}
</script>

<div class="location-control">
	<label for="location-input">Location</label>
	<input
		id="location-input"
		name="location"
		type="text"
		inputmode="search"
		autocomplete="off"
		spellcheck="false"
		aria-describedby="location-help"
		aria-autocomplete="list"
		aria-controls="location-suggestions"
		aria-expanded={suggestions.length > 0}
		role="combobox"
		value={inputValue}
		disabled={disabled || resolving}
		oninput={handleInput}
	/>
	{#if suggestions.length > 0}
		<div class="suggestions-panel">
			<ul id="location-suggestions" class="location-suggestions" role="listbox">
				{#each suggestions as suggestion (suggestion.provider_place_id)}
					<li role="option" aria-selected="false">
						<button
							type="button"
							class="suggestion-button"
							disabled={disabled || resolving}
							onclick={() => selectSuggestion(suggestion)}
						>
							{suggestion.label}
						</button>
					</li>
				{/each}
			</ul>
			<p class="google-maps-attribution" translate="no">Google Maps</p>
		</div>
	{/if}
</div>
