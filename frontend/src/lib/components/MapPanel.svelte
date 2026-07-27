<script lang="ts">
	import { onMount } from 'svelte';

	import { createGoogleMapsRenderer } from '$lib/maps/google-maps-renderer';
	import type { MapMount, MapRenderer, MapSnapshot } from '$lib/maps/map-renderer';
	import type { Coordinates, Place } from '$lib/types';

	interface Props {
		apiKey: string;
		center: Coordinates;
		radiusMeters: number;
		places: Place[];
		searchAreaSelected: boolean;
		selectedPlaceKey: string | null;
		onPlaceSelect(placeKey: string): void;
		onLocationSelect(coordinates: Coordinates): void;
		disabled: boolean;
		renderer?: MapRenderer;
	}

	let {
		apiKey,
		center,
		radiusMeters,
		places,
		searchAreaSelected,
		selectedPlaceKey,
		onPlaceSelect,
		onLocationSelect,
		disabled,
		renderer
	}: Props = $props();
	let mapElement: HTMLDivElement;
	let mapMount = $state<MapMount | null>(null);
	let loadState = $state<'loading' | 'ready' | 'missing-key' | 'error'>('loading');

	function handleLocationSelect(coordinates: Coordinates) {
		if (disabled) return;
		onLocationSelect(coordinates);
	}

	function snapshot(): MapSnapshot {
		return {
			center: {
				latitude: center.latitude,
				longitude: center.longitude
			},
			radiusMeters,
			places: places.map((place) => ({
				key: `${place.provider}:${place.provider_place_id}`,
				title: place.name,
				coordinates: {
					latitude: place.coordinates.latitude,
					longitude: place.coordinates.longitude
				}
			})),
			selectedPlaceKey,
			locationSelectionEnabled: !disabled,
			searchAreaSelected
		};
	}

	$effect(() => {
		mapMount?.render(snapshot());
	});

	onMount(() => {
		if (!apiKey.trim()) {
			loadState = 'missing-key';
			return;
		}

		let disposed = false;
		const activeRenderer = renderer ?? createGoogleMapsRenderer(apiKey);

		void activeRenderer
			.mount(mapElement, {
				center: {
					latitude: center.latitude,
					longitude: center.longitude
				},
				onPlaceSelect,
				onLocationSelect: handleLocationSelect
			})
			.then((mountedMap) => {
				if (disposed) {
					mountedMap.destroy();
					return;
				}
				mapMount = mountedMap;
				loadState = 'ready';
			})
			.catch((error: unknown) => {
				if (disposed) return;
				console.error(error);
				loadState = 'error';
			});

		return () => {
			disposed = true;
			mapMount?.destroy();
			mapMount = null;
		};
	});
</script>

<section class="map-panel" aria-labelledby="map-heading">
	<div class="map-heading">
		<div>
			<p class="eyebrow">Map</p>
			<h2 id="map-heading">Explore the area</h2>
		</div>
		<div class="map-actions">
			<p>
				{#if disabled}
					Map location selection is temporarily unavailable.
				{:else}
					Click the map to choose or change the location.
				{/if}
			</p>
		</div>
	</div>
	<div class="map-frame" aria-busy={loadState === 'loading'}>
		<div
			class="map-canvas"
			class:map-canvas-hidden={loadState !== 'ready'}
			bind:this={mapElement}
			role="region"
			aria-label="FoodFind map"
		></div>
		{#if loadState === 'loading'}
			<p class="map-message" role="status">Loading map…</p>
		{:else if loadState === 'missing-key'}
			<p class="map-message map-error" role="alert">
				Google Maps is not configured for this browser.
			</p>
		{:else if loadState === 'error'}
			<p class="map-message map-error" role="alert">
				The map could not load. Check the Maps JavaScript API key and website restrictions.
			</p>
		{:else}
			<p class="sr-only" role="status">Interactive map ready.</p>
		{/if}
	</div>
</section>
