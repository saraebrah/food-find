<script lang="ts">
	import { onDestroy } from 'svelte';

	import { ApiError, searchPlaces } from '$lib/api';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import PlaceCard from '$lib/components/PlaceCard.svelte';
	import { formatRadius } from '$lib/search';
	import type { Place, SearchCriteria, SelectedLocation } from '$lib/types';

	const initialLocation: SelectedLocation = {
		label: '43.6532, -79.3832',
		latitude: 43.6532,
		longitude: -79.3832
	};

	let selectedLocation = $state<SelectedLocation | null>({ ...initialLocation });
	let radiusMeters = $state(1000);
	let places = $state<Place[]>([]);
	let status = $state('Select Search when you are ready.');
	let searching = $state(false);
	let searchVersion = $state(0);
	let controller: AbortController | null = null;

	onDestroy(() => controller?.abort());

	function clearResults() {
		places = [];
	}

	function handleRadiusChange(event: Event) {
		radiusMeters = Number((event.currentTarget as HTMLSelectElement).value);
		clearResults();
		status = 'Radius updated. Select Search to refresh the results.';
	}

	async function search() {
		if (!selectedLocation) {
			status = 'Choose a suggested location or enter valid coordinates first.';
			return;
		}

		const criteria: SearchCriteria = {
			location: { ...selectedLocation },
			radius_meters: radiusMeters
		};
		clearResults();
		searchVersion += 1;
		searching = true;
		status = `Searching within ${formatRadius(criteria.radius_meters)} of ${criteria.location.label}…`;
		controller = new AbortController();
		try {
			places = await searchPlaces(criteria, controller.signal);
			status =
				places.length > 0
					? `Found ${places.length} ${places.length === 1 ? 'place' : 'places'}.`
					: 'No matching places found in this area. Try a larger radius or another location.';
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			status =
				error instanceof ApiError && error.status === 422
					? 'Check the location and radius, then try again.'
					: 'Search is temporarily unavailable. Please try again.';
		} finally {
			searching = false;
			controller = null;
		}
	}
</script>

<svelte:head>
	<title>FoodFind</title>
	<meta
		name="description"
		content="Find nearby food businesses around a selected location."
	/>
</svelte:head>

<main>
	<header class="hero">
		<p class="eyebrow">Phase 3 foundation</p>
		<h1>FoodFind</h1>
		<p class="intro">Nearby food discovery starts here.</p>
	</header>

	<section class="search-panel" aria-labelledby="search-heading">
		<div class="search-copy">
			<h2 id="search-heading">Choose a location</h2>
			<p id="location-help">
				Start typing a place or address, or enter decimal coordinates as latitude, longitude.
				Then choose how far around it to search.
			</p>
		</div>
		<div class="search-controls">
			<div class="search-action">
				<LocationPicker
					disabled={searching}
					{initialLocation}
					onLocationChange={(location) => (selectedLocation = location)}
					onStatus={(message) => (status = message)}
					onClearResults={clearResults}
				/>
				<div class="radius-control">
					<label for="radius-select">Radius</label>
					<select
						id="radius-select"
						name="radius"
						value={radiusMeters}
						disabled={searching}
						onchange={handleRadiusChange}
					>
						<option value="500">500 m</option>
						<option value="1000">1 km</option>
						<option value="2000">2 km</option>
						<option value="5000">5 km</option>
					</select>
				</div>
				<button type="button" disabled={searching || !selectedLocation} onclick={search}>
					{searching ? 'Searching…' : 'Search'}
				</button>
			</div>
		</div>
	</section>

	<p class="search-status" role="status" aria-live="polite">{status}</p>

	{#if places.length > 0}
		<section id="results-section" aria-labelledby="results-heading">
			<div class="results-heading">
				<h2 id="results-heading">Places</h2>
				<p>{places.length} {places.length === 1 ? 'result' : 'results'}</p>
			</div>
			<ul class="place-results">
				{#each places as place (`${searchVersion}:${place.provider}:${place.provider_place_id}`)}
					<PlaceCard {place} />
				{/each}
			</ul>
		</section>
	{/if}

	<noscript>JavaScript is required to run the place search.</noscript>
</main>
