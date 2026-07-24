<script lang="ts">
	import { onDestroy } from 'svelte';

	import { ApiError, interpretSearch, searchPlaces } from '$lib/api';
	import InterpretationSummary from '$lib/components/InterpretationSummary.svelte';
	import LocationPicker from '$lib/components/LocationPicker.svelte';
	import MinimumRatingFilter from '$lib/components/MinimumRatingFilter.svelte';
	import OpenNowFilter from '$lib/components/OpenNowFilter.svelte';
	import PlaceCard from '$lib/components/PlaceCard.svelte';
	import PlaceTypeFilter from '$lib/components/PlaceTypeFilter.svelte';
	import ServiceFilters from '$lib/components/ServiceFilters.svelte';
	import SpecialtyFilters from '$lib/components/SpecialtyFilters.svelte';
	import { formatRadius } from '$lib/search';
	import type {
		AvailabilityWindow,
		CommonFood,
		Cuisine,
		MinimumRating,
		Place,
		PlaceSearchRequest,
		PlaceType,
		SearchCriteria,
		SearchFilters,
		SearchInterpretation,
		SearchSort,
		SelectedLocation
	} from '$lib/types';

	const initialLocation: SelectedLocation = {
		label: '43.6532, -79.3832',
		latitude: 43.6532,
		longitude: -79.3832
	};

	let selectedLocation = $state<SelectedLocation | null>({ ...initialLocation });
	let radiusMeters = $state(1000);
	let filters = $state<SearchFilters>({
		place_types: ['restaurant', 'cafe'],
		cuisines: [],
		common_foods: [],
		open_now: false,
		minimum_rating: null,
		dine_in: false,
		takeout: false
	});
	let sort = $state<SearchSort>('provider_default');
	let places = $state<Place[]>([]);
	let status = $state('Select Search when you are ready.');
	let searching = $state(false);
	let interpreting = $state(false);
	let smartSearchQuery = $state('');
	let interpretation = $state<SearchInterpretation | null>(null);
	let interpretationEdited = $state(false);
	let searchVersion = $state(0);
	let controller: AbortController | null = null;
	let interpretationController: AbortController | null = null;
	const busy = $derived(searching || interpreting);
	const standardRadii = [500, 1000, 2000, 5000];

	onDestroy(() => {
		controller?.abort();
		interpretationController?.abort();
	});

	function clearResults() {
		places = [];
	}

	function markInterpretationEdited() {
		if (interpretation) interpretationEdited = true;
	}

	function handleLocationChange(location: SelectedLocation | null) {
		selectedLocation = location;
		markInterpretationEdited();
	}

	function handleRadiusChange(event: Event) {
		radiusMeters = Number((event.currentTarget as HTMLSelectElement).value);
		clearResults();
		markInterpretationEdited();
		status = 'Radius updated. Select Search to refresh the results.';
	}

	function handlePlaceTypesChange(placeTypes: PlaceType[]) {
		filters = { ...filters, place_types: placeTypes };
		clearResults();
		markInterpretationEdited();
		status =
			placeTypes.length > 0
				? 'Place types updated. Select Search to refresh the results.'
				: 'Choose at least one place type.';
	}

	function handleCuisinesChange(cuisines: Cuisine[]) {
		filters = { ...filters, cuisines };
		clearResults();
		markInterpretationEdited();
		status = 'Cuisine updated. Select Search to refresh the results.';
	}

	function handleCommonFoodsChange(commonFoods: CommonFood[]) {
		filters = { ...filters, common_foods: commonFoods };
		clearResults();
		markInterpretationEdited();
		status = 'Common food updated. Select Search to refresh the results.';
	}

	function handleOpenNowChange(openNow: boolean) {
		filters = { ...filters, open_now: openNow };
		clearResults();
		markInterpretationEdited();
		status = 'Availability updated. Select Search to refresh the results.';
	}

	function handleMinimumRatingChange(minimumRating: MinimumRating | null) {
		filters = { ...filters, minimum_rating: minimumRating };
		clearResults();
		markInterpretationEdited();
		status = 'Minimum rating updated. Select Search to refresh the results.';
	}

	function handleDineInChange(dineIn: boolean) {
		filters = { ...filters, dine_in: dineIn };
		clearResults();
		markInterpretationEdited();
		status = 'Service options updated. Select Search to refresh the results.';
	}

	function handleTakeoutChange(takeout: boolean) {
		filters = { ...filters, takeout };
		clearResults();
		markInterpretationEdited();
		status = 'Service options updated. Select Search to refresh the results.';
	}

	function handleSortChange(event: Event) {
		sort = (event.currentTarget as HTMLSelectElement).value as SearchSort;
		clearResults();
		markInterpretationEdited();
		status = 'Sort order updated. Select Search to refresh the results.';
	}

	function snapshotCriteria(): SearchCriteria | null {
		if (!selectedLocation) {
			status = 'Choose a suggested location or enter valid coordinates first.';
			return null;
		}
		if (filters.place_types.length === 0) {
			status = 'Choose at least one place type.';
			return null;
		}

		return {
			location: { ...selectedLocation },
			radius_meters: radiusMeters,
			filters: {
				place_types: [...filters.place_types],
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
			place_types: [...result.search_criteria.filters.place_types],
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
						}. Review what could not be applied, then select Search to use the supported criteria.`
					: 'Request applied to the controls. Review or edit them, then select Search.';
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
						: 'Search is temporarily unavailable. Select Search to try again.';
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
		<p class="eyebrow">Phase 4</p>
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
			<div class="smart-search-control">
				<label for="smart-search-input">Smart search</label>
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
							filters.place_types.length === 0 ||
							!smartSearchQuery.trim()}
						onclick={applySmartSearch}
					>
						{interpreting ? 'Applying…' : 'Apply request'}
					</button>
				</div>
			</div>
			<div class="search-action">
				<LocationPicker
					disabled={busy}
					{initialLocation}
					onLocationChange={handleLocationChange}
					onStatus={(message) => (status = message)}
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
				<div class="sort-control">
					<label for="sort-select">Sort</label>
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
					disabled={busy || !selectedLocation || filters.place_types.length === 0}
					onclick={search}
				>
					{searching ? 'Searching…' : 'Search'}
				</button>
			</div>
			<PlaceTypeFilter
				selected={filters.place_types}
				disabled={busy}
				onChange={handlePlaceTypesChange}
			/>
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

	{#if interpretation}
		<InterpretationSummary
			{interpretation}
			disabled={busy}
			edited={interpretationEdited}
			onAvailabilityChange={handleAvailabilityChange}
			onStatus={(message) => (status = message)}
		/>
	{/if}

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
