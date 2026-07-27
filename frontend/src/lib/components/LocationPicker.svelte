<script lang="ts">
	import { onDestroy, untrack } from 'svelte';

	import { ApiError, autocompleteLocations, resolveLocation } from '$lib/api';
	import type { DeviceLocation } from '$lib/geolocation/geolocation-provider';
	import { looksLikeCoordinatePair, parseCoordinates } from '$lib/search';
	import type { LocationSuggestion, SelectedLocation } from '$lib/types';
	import CurrentLocationButton from './CurrentLocationButton.svelte';

	interface Props {
		disabled: boolean;
		selectedLocation: SelectedLocation | null;
		onLocationChange: (location: SelectedLocation | null) => void;
		onBusyChange: (busy: boolean) => void;
		onDeviceLocation: (location: DeviceLocation) => void;
		onStatus: (message: string) => void;
		onClearResults: () => void;
	}

	let {
		disabled,
		selectedLocation,
		onLocationChange,
		onBusyChange,
		onDeviceLocation,
		onStatus,
		onClearResults
	}: Props = $props();
	let inputValue = $state(untrack(() => selectedLocation?.label ?? ''));
	let suggestions = $state<LocationSuggestion[]>([]);
	let menuOpen = $state(false);
	let deviceLocating = $state(false);
	let resolving = $state(false);
	let controlElement: HTMLDivElement;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let controller: AbortController | null = null;
	let requestNumber = 0;
	let sessionToken = crypto.randomUUID();
	let lastEmittedLocation = '';

	function locationSignature(location: SelectedLocation | null): string {
		return location
			? JSON.stringify({
					label: location.label,
					latitude: location.latitude,
					longitude: location.longitude,
					provider: location.provider ?? null,
					provider_place_id: location.provider_place_id ?? null
				})
			: '';
	}

	function emitLocation(location: SelectedLocation | null) {
		lastEmittedLocation = locationSignature(location);
		onLocationChange(location);
	}

	onDestroy(() => {
		if (timer !== null) clearTimeout(timer);
		controller?.abort();
	});

	$effect(() => {
		const signature = locationSignature(selectedLocation);
		if (!selectedLocation || signature === lastEmittedLocation) return;
		resetPendingRequest();
		suggestions = [];
		inputValue = selectedLocation.label;
		menuOpen = false;
	});

	$effect(() => {
		if (!disabled) return;
		resetPendingRequest();
		suggestions = [];
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
		menuOpen = true;
		suggestions = [];
		resetPendingRequest();
		onClearResults();

		const coordinates = parseCoordinates(inputValue);
		if (coordinates) {
			emitLocation(coordinates);
			onStatus('Coordinates are ready. Select Search places when you are ready.');
			return;
		}

		emitLocation(null);
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
			emitLocation(location);
			onClearResults();
			onStatus('Location selected. Select Search places when you are ready.');
			sessionToken = crypto.randomUUID();
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			emitLocation(null);
			onStatus('That location could not be selected. Try another suggestion.');
		} finally {
			resolving = false;
			controller = null;
		}
	}

	function handleFocusOut(event: FocusEvent) {
		if (deviceLocating) return;
		const nextTarget = event.relatedTarget;
		if (nextTarget instanceof Node && controlElement.contains(nextTarget)) return;
		menuOpen = false;
	}

	function handleDeviceBusyChange(busy: boolean) {
		deviceLocating = busy;
		if (busy) menuOpen = true;
		onBusyChange(busy);
	}
</script>

<div
	class="location-control"
	bind:this={controlElement}
	onfocusout={handleFocusOut}
>
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
		aria-expanded={menuOpen}
		role="combobox"
		value={inputValue}
		disabled={disabled || resolving}
		onfocus={() => (menuOpen = true)}
		oninput={handleInput}
	/>
	<div class="suggestions-panel" hidden={!menuOpen && !deviceLocating}>
		<ul id="location-suggestions" class="location-suggestions" role="listbox">
			<li role="option" aria-selected="false">
				<CurrentLocationButton
					{disabled}
					onBusyChange={handleDeviceBusyChange}
					onLocation={onDeviceLocation}
					{onStatus}
					variant="suggestion"
				/>
			</li>
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
		{#if suggestions.length > 0}
			<p class="google-maps-attribution" translate="no">Google Maps</p>
		{/if}
	</div>
</div>
