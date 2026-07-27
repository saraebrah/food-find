<script lang="ts">
	import { env } from '$env/dynamic/public';
	import { onDestroy } from 'svelte';

	import { ApiError, interpretSearch, searchPlaces } from '$lib/api';
	import InterpretationSummary from '$lib/components/InterpretationSummary.svelte';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import MapPanel from '$lib/components/MapPanel.svelte';
	import MinimumRatingFilter from '$lib/components/MinimumRatingFilter.svelte';
	import OpenNowFilter from '$lib/components/OpenNowFilter.svelte';
	import PlaceCard from '$lib/components/PlaceCard.svelte';
	import ServiceFilters from '$lib/components/ServiceFilters.svelte';
	import SpecialtyFilters from '$lib/components/SpecialtyFilters.svelte';
	import type { DeviceLocation } from '$lib/geolocation/geolocation-provider';
	import {
		formatRadius,
		selectedLocationFromCoordinates
	} from '$lib/search';
	import type {
		AvailabilityWindow,
		CommonFood,
		Coordinates,
		Cuisine,
		MinimumRating,
		Place,
		PlaceSearchRequest,
		SearchCriteria,
		SearchFilters,
		SearchInterpretation,
		SearchSort,
		SelectedLocation
	} from '$lib/types';

	const initialMapCenter: Coordinates = {
		latitude: 43.6532,
		longitude: -79.3832
	};

	let selectedLocation = $state<SelectedLocation | null>(null);
	let mapCenter = $state<Coordinates>({
		latitude: initialMapCenter.latitude,
		longitude: initialMapCenter.longitude
	});
	let radiusMeters = $state(1000);
	let filters = $state<SearchFilters>({
		cuisines: [],
		common_foods: [],
		open_now: false,
		minimum_rating: null,
		dine_in: false,
		takeout: false
	});
	let sort = $state<SearchSort>('provider_default');
	let places = $state<Place[]>([]);
	let selectedPlaceKey = $state<string | null>(null);
	let locationStatus = $state('Choose a location to define the search area.');
	let status = $state('Choose what to find, then select Search places.');
	let searching = $state(false);
	let interpreting = $state(false);
	let locating = $state(false);
	let smartSearchQuery = $state('');
	let interpretation = $state<SearchInterpretation | null>(null);
	let interpretationEdited = $state(false);
	let searchVersion = $state(0);
	let controller: AbortController | null = null;
	let interpretationController: AbortController | null = null;
	const busy = $derived(searching || interpreting || locating);
	const standardRadii = [500, 1000, 2000, 5000];

	onDestroy(() => {
		controller?.abort();
		interpretationController?.abort();
	});

	function clearResults() {
		places = [];
		selectedPlaceKey = null;
	}

	function placeKey(place: Place): string {
		return `${place.provider}:${place.provider_place_id}`;
	}

	function handlePlaceSelect(key: string) {
		if (!places.some((place) => placeKey(place) === key)) return;
		selectedPlaceKey = key;
	}

	function markInterpretationEdited() {
		if (interpretation) interpretationEdited = true;
	}

	function handleLocationChange(location: SelectedLocation | null) {
		selectedLocation = location;
		if (location) {
			mapCenter = {
				latitude: location.latitude,
				longitude: location.longitude
			};
		}
		markInterpretationEdited();
	}

	function applyCoordinateLocation(
		coordinates: Coordinates,
		label?: string
	): boolean {
		const normalizedLocation = selectedLocationFromCoordinates(coordinates);
		if (!normalizedLocation) return false;
		const location = {
			...normalizedLocation,
			label: label ?? normalizedLocation.label
		};
		selectedLocation = location;
		mapCenter = {
			latitude: location.latitude,
			longitude: location.longitude
		};
		clearResults();
		markInterpretationEdited();
		return true;
	}

	function handleMapLocationSelect(coordinates: {
		latitude: number;
		longitude: number;
	}) {
		if (!applyCoordinateLocation(coordinates)) {
			locationStatus = 'That map point could not be selected. Try another point.';
			return;
		}
		locationStatus = 'Map location selected. Select Search places when you are ready.';
	}

	function handleCurrentLocation(location: DeviceLocation) {
		if (!applyCoordinateLocation(location.coordinates, 'Current location')) {
			locationStatus = 'Your current location could not be used. Enter a location or choose one on the map.';
			return;
		}
		if (location.accuracyMeters > radiusMeters) {
			const accuracy =
				location.accuracyMeters < 1_000
					? `${Math.round(location.accuracyMeters)} m`
					: `${(location.accuracyMeters / 1_000).toFixed(1)} km`;
			locationStatus =
				`Current location selected, but your browser estimates accuracy within ${accuracy}. ` +
				'Adjust it manually or on the map if needed, then select Search places.';
			return;
		}
		locationStatus = 'Current location selected. Select Search places when you are ready.';
	}

	function handleRadiusChange(event: Event) {
		radiusMeters = Number((event.currentTarget as HTMLSelectElement).value);
		clearResults();
		markInterpretationEdited();
		locationStatus = 'Radius updated. Select Search places to refresh the results.';
	}

	function handleCuisinesChange(cuisines: Cuisine[]) {
		filters = { ...filters, cuisines };
		clearResults();
		markInterpretationEdited();
		status = 'Cuisine updated. Select Search places to refresh the results.';
	}

	function handleCommonFoodsChange(commonFoods: CommonFood[]) {
		filters = { ...filters, common_foods: commonFoods };
		clearResults();
		markInterpretationEdited();
		status = 'Common food updated. Select Search places to refresh the results.';
	}

	function handleOpenNowChange(openNow: boolean) {
		filters = { ...filters, open_now: openNow };
		clearResults();
		markInterpretationEdited();
		status = 'Availability updated. Select Search places to refresh the results.';
	}

	function handleMinimumRatingChange(minimumRating: MinimumRating | null) {
		filters = { ...filters, minimum_rating: minimumRating };
		clearResults();
		markInterpretationEdited();
		status = 'Minimum rating updated. Select Search places to refresh the results.';
	}

	function handleDineInChange(dineIn: boolean) {
		filters = { ...filters, dine_in: dineIn };
		clearResults();
		markInterpretationEdited();
		status = 'Service options updated. Select Search places to refresh the results.';
	}

	function handleTakeoutChange(takeout: boolean) {
		filters = { ...filters, takeout };
		clearResults();
		markInterpretationEdited();
		status = 'Service options updated. Select Search places to refresh the results.';
	}

	function handleSortChange(event: Event) {
		sort = (event.currentTarget as HTMLSelectElement).value as SearchSort;
		clearResults();
		markInterpretationEdited();
		status = 'Sort order updated. Select Search places to refresh the results.';
	}

	function snapshotCriteria(): SearchCriteria | null {
		if (!selectedLocation) {
			status = 'Choose a suggested location or enter valid coordinates first.';
			return null;
		}
		return {
			location: { ...selectedLocation },
			radius_meters: radiusMeters,
			filters: {
				cuisines: [...filters.cuisines],
				common_foods: [...filters.common_foods],
				open_now: filters.open_now,
				minimum_rating: filters.minimum_rating,
				dine_in: filters.dine_in,
				takeout: filters.takeout
			},
			sort
		};
	}

	function applyInterpretation(result: SearchInterpretation) {
		radiusMeters = result.search_criteria.radius_meters;
		filters = {
			cuisines: [...result.search_criteria.filters.cuisines],
			common_foods: [...result.search_criteria.filters.common_foods],
			open_now: result.search_criteria.filters.open_now,
			minimum_rating: result.search_criteria.filters.minimum_rating,
			dine_in: result.search_criteria.filters.dine_in,
			takeout: result.search_criteria.filters.takeout
		};
		sort = result.search_criteria.sort;
		interpretation = {
			...result,
			search_criteria: {
				...result.search_criteria,
				location: { ...result.search_criteria.location },
				filters: { ...result.search_criteria.filters }
			},
			descriptive_requirements: [...result.descriptive_requirements],
			availability_window: result.availability_window
				? { ...result.availability_window }
				: null,
			assumptions: [...result.assumptions],
			unsupported_criteria: [...result.unsupported_criteria]
		};
		interpretationEdited = false;
	}

	function handleAvailabilityChange(availabilityWindow: AvailabilityWindow | null) {
		if (!interpretation) return;
		interpretation = {
			...interpretation,
			availability_window: availabilityWindow
				? { ...availabilityWindow }
				: null
		};
		interpretationEdited = true;
		clearResults();
	}

	async function applySmartSearch() {
		const query = smartSearchQuery.trim();
		if (!query) {
			status = 'Describe what you want before applying a smart search.';
			return;
		}
		const criteria = snapshotCriteria();
		if (!criteria) return;

		clearResults();
		interpreting = true;
		status = 'Interpreting your request…';
		interpretationController = new AbortController();
		const timezone =
			Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
		try {
			const result = await interpretSearch(
				query,
				criteria,
				timezone,
				interpretationController.signal
			);
			applyInterpretation(result);
			const unsupportedCount = result.unsupported_criteria.length;
			status =
				unsupportedCount > 0
					? `Request applied with ${unsupportedCount} unsupported ${
							unsupportedCount === 1 ? 'criterion' : 'criteria'
						}. Review what could not be applied, then select Search places to use the supported criteria.`
					: 'Request applied to the controls. Review or edit them, then select Search places.';
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			status =
				error instanceof ApiError && error.status === 422
					? 'Check the request and selected location, then try again.'
					: error instanceof ApiError && error.status === 503
						? 'Smart search is not configured on this server.'
						: 'Smart search could not apply that request safely. Your current criteria were not changed.';
		} finally {
			interpreting = false;
			interpretationController = null;
		}
	}

	async function search() {
		const criteria = snapshotCriteria();
		if (!criteria) return;
		const searchRequest: PlaceSearchRequest = {
			...criteria,
			descriptive_requirements:
				interpretation?.descriptive_requirements.map((requirement) => ({
					...requirement
				})) ?? [],
			availability_window: interpretation?.availability_window
				? { ...interpretation.availability_window }
				: null
		};

		clearResults();
		searchVersion += 1;
		searching = true;
		status =
			`Searching within ${formatRadius(criteria.radius_meters)} ` +
			`of ${criteria.location.label}…`;
		controller = new AbortController();
		try {
			places = await searchPlaces(searchRequest, controller.signal);
			status =
				places.length > 0
					? `Found ${places.length} ${places.length === 1 ? 'place' : 'places'}.`
					: 'No places matched the current criteria. Try removing a filter, choosing a larger radius, or selecting another location.';
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			status =
				error instanceof ApiError && error.status === 400
					? 'Google can confirm requested opening hours only for today and the next six days. Edit or remove the time preference.'
					: error instanceof ApiError && error.status === 422
						? 'Check the location, radius, filters, and requested time, then try again.'
						: 'Search is temporarily unavailable. Select Search places to try again.';
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
		<p class="eyebrow">Find food nearby</p>
		<h1>FoodFind</h1>
		<p class="intro">Nearby food discovery starts here.</p>
	</header>

	<section class="search-panel location-panel" aria-labelledby="location-heading">
		<div class="search-copy">
			<p class="step-label">Step 1 · Required</p>
			<h2 id="location-heading">Choose where to search</h2>
			<p id="location-help">
				Start typing a place or address, or enter decimal coordinates as latitude, longitude.
				Then choose how far around it to search.
			</p>
		</div>
		<div class="location-actions">
			<LocationPicker
				disabled={busy}
				{selectedLocation}
				onLocationChange={handleLocationChange}
				onBusyChange={(value) => (locating = value)}
				onDeviceLocation={handleCurrentLocation}
				onStatus={(message) => (locationStatus = message)}
				onClearResults={clearResults}
			/>
			<div class="radius-control">
				<label for="radius-select">Radius</label>
				<select
					id="radius-select"
					name="radius"
					bind:value={radiusMeters}
					disabled={busy}
					onchange={handleRadiusChange}
				>
					{#if !standardRadii.includes(radiusMeters)}
						<option value={radiusMeters}>{formatRadius(radiusMeters)}</option>
					{/if}
					<option value={500}>500 m</option>
					<option value={1000}>1 km</option>
					<option value={2000}>2 km</option>
					<option value={5000}>5 km</option>
				</select>
			</div>
		</div>
		<p class="search-status" role="status" aria-live="polite">{locationStatus}</p>
	</section>

	<MapPanel
		apiKey={env.PUBLIC_GOOGLE_MAPS_API_KEY ?? ''}
		center={mapCenter}
		{radiusMeters}
		{places}
		searchAreaSelected={selectedLocation !== null}
		{selectedPlaceKey}
		onPlaceSelect={handlePlaceSelect}
		onLocationSelect={handleMapLocationSelect}
		disabled={busy}
	/>

	<section class="search-panel criteria-panel" aria-labelledby="criteria-heading">
		<div class="search-copy">
			<p class="step-label">Step 2 · Choose what to find</p>
			<h2 id="criteria-heading">Describe or refine your search</h2>
			<p>
				Use the optional smart search as a shortcut, then review or adjust any filters.
			</p>
		</div>
		<div class="search-controls">
			<div class="smart-search-control">
				<label for="smart-search-input">Smart search <span>(optional)</span></label>
				<textarea
					id="smart-search-input"
					name="smart-search"
					rows="3"
					placeholder="Try: good rated Persian restaurant serving kebab near me tonight"
					bind:value={smartSearchQuery}
					disabled={busy}
				></textarea>
				<div class="smart-search-footer">
					<p>Applying a request updates the controls but does not search for places.</p>
					<button
						type="button"
						disabled={busy ||
							!selectedLocation ||
							!smartSearchQuery.trim()}
						onclick={applySmartSearch}
					>
						{interpreting ? 'Applying…' : 'Apply request'}
					</button>
				</div>
			</div>

			{#if interpretation}
				<InterpretationSummary
					{interpretation}
					disabled={busy}
					edited={interpretationEdited}
					onAvailabilityChange={handleAvailabilityChange}
					onStatus={(message) => (status = message)}
				/>
			{/if}

			<div class="manual-filter-heading">
				<h3>Manual filters</h3>
				<p>Review anything filled by smart search, or choose filters yourself.</p>
			</div>
			<SpecialtyFilters
				cuisines={filters.cuisines}
				commonFoods={filters.common_foods}
				disabled={busy}
				onCuisinesChange={handleCuisinesChange}
				onCommonFoodsChange={handleCommonFoodsChange}
			/>
			<OpenNowFilter
				checked={filters.open_now}
				disabled={busy}
				onChange={handleOpenNowChange}
			/>
			<MinimumRatingFilter
				minimumRating={filters.minimum_rating}
				disabled={busy}
				onChange={handleMinimumRatingChange}
			/>
			<ServiceFilters
				dineIn={filters.dine_in}
				takeout={filters.takeout}
				disabled={busy}
				onDineInChange={handleDineInChange}
				onTakeoutChange={handleTakeoutChange}
			/>
		</div>
	</section>

	<section class="search-review" aria-labelledby="review-heading">
		<div>
			<p class="step-label">Step 3 · Review and search</p>
			<h2 id="review-heading">Ready to find places?</h2>
			<p>Location is required. Filters and smart search are optional.</p>
		</div>
		<div class="search-submit-row">
			<div class="sort-control">
				<label for="sort-select">Sort results</label>
				<select
					id="sort-select"
					name="sort"
					bind:value={sort}
					disabled={busy}
					onchange={handleSortChange}
				>
					<option value="provider_default">Recommended</option>
					<option value="distance">Distance</option>
					<option value="rating">Rating</option>
				</select>
			</div>
			<button
				type="button"
				class="search-submit-button"
				disabled={busy || !selectedLocation}
				onclick={search}
			>
				{searching ? 'Searching…' : 'Search places'}
			</button>
		</div>
		<p class="search-status" role="status" aria-live="polite">{status}</p>
	</section>

	{#if places.length > 0}
		<section id="results-section" aria-labelledby="results-heading">
			<div class="results-heading">
				<h2 id="results-heading">Places</h2>
				<p>{places.length} {places.length === 1 ? 'result' : 'results'}</p>
			</div>
			<ul class="place-results">
				{#each places as place (`${searchVersion}:${place.provider}:${place.provider_place_id}`)}
					<PlaceCard
						{place}
						selected={selectedPlaceKey === placeKey(place)}
						onSelect={() => handlePlaceSelect(placeKey(place))}
					/>
				{/each}
			</ul>
		</section>
	{/if}

	<noscript>JavaScript is required to run the place search.</noscript>
</main>
