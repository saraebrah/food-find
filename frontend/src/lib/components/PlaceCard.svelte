<script lang="ts">
	import { onDestroy } from 'svelte';

	import { ApiError, getPlaceDetails } from '$lib/api';
	import { directionsHref, formatDistance, providerName } from '$lib/search';
	import type { Place, PlaceDetails } from '$lib/types';
	import PlaceDetailsPanel from './PlaceDetailsPanel.svelte';

	let { place }: { place: Place } = $props();
	const componentId = $props.id();
	const detailsId = `${componentId}-details`;
	const directions = $derived(directionsHref(place));
	let details = $state<PlaceDetails | null>(null);
	let detailsOpen = $state(false);
	let detailsLoading = $state(false);
	let detailsError = $state(false);
	let detailsController: AbortController | null = null;

	onDestroy(() => detailsController?.abort());

	async function toggleDetails() {
		if (detailsOpen && !detailsError) {
			detailsOpen = false;
			return;
		}

		detailsOpen = true;
		detailsError = false;
		if (details !== null) return;

		detailsLoading = true;
		detailsController = new AbortController();
		try {
			details = await getPlaceDetails(
				place.provider,
				place.provider_place_id,
				detailsController.signal
			);
		} catch (error) {
			if (error instanceof DOMException && error.name === 'AbortError') return;
			console.error(error instanceof ApiError ? error.message : error);
			detailsError = true;
		} finally {
			detailsLoading = false;
			detailsController = null;
		}
	}
</script>

<li class="place-card">
	<h3 class="place-name">{place.name}</h3>
	<p class:place-category={place.category || place.category_code} class:place-missing={!place.category && !place.category_code}>
		{place.category || place.category_code || 'Category unavailable'}
	</p>
	<p class="place-distance">{formatDistance(place.distance_meters)}</p>
	{#if place.rating !== null}
		<p class="place-rating">{providerName(place.provider)} rating: {place.rating}/5</p>
	{/if}
	<p class:place-address={place.address} class:place-missing={!place.address}>
		{place.address || 'Address unavailable'}
	</p>
	{#if place.open_now === true}
		<p class="place-open-status">Open now</p>
	{/if}
	{#if place.business_status === null}
		<p class="place-status-warning">
			Operational status unconfirmed. Call to confirm before visiting.
		</p>
	{/if}
	<p class="place-source">Source: {providerName(place.provider)}</p>

	{#if place.match_reasons.length > 0}
		<details class="place-match-reasons">
			<summary>Why this matched</summary>
			<ul>
				{#each place.match_reasons as reason}
					<li>
						<span
							class:match-confirmed={reason.kind === 'confirmed'}
							class:match-relevance={reason.kind === 'relevance'}
						>
							{reason.kind === 'confirmed' ? 'Confirmed' : 'Relevance only'}
						</span>
						<span>{reason.text}</span>
					</li>
				{/each}
			</ul>
		</details>
	{/if}

	{#if directions}
		<a
			class="place-action place-directions-link"
			href={directions}
			target="_blank"
			rel="noopener noreferrer"
		>
			Get directions
		</a>
	{/if}
	<button
		type="button"
		class="place-details-button"
		aria-controls={detailsId}
		aria-expanded={detailsOpen}
		disabled={detailsLoading}
		onclick={toggleDetails}
	>
		{detailsLoading ? 'Loading…' : detailsOpen && !detailsError ? 'Hide details' : detailsError ? 'Try again' : 'View details'}
	</button>

	{#if detailsOpen}
		<div id={detailsId} class="place-details" aria-live="polite">
			{#if detailsLoading}
				<p class="place-detail-status">Loading details…</p>
			{:else if detailsError}
				<p class="place-detail-error">Details are temporarily unavailable. Please try again.</p>
			{:else if details}
				<PlaceDetailsPanel {details} businessStatus={place.business_status} />
			{/if}
		</div>
	{/if}
</li>
