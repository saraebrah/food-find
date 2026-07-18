<script lang="ts">
	import { phoneHref, providerName, websiteHref } from '$lib/search';
	import type { BusinessStatus, PlaceDetails } from '$lib/types';

	interface Props {
		details: PlaceDetails;
		businessStatus: BusinessStatus | null;
	}

	let { details, businessStatus }: Props = $props();
	let showNumber = $state(false);
	const componentId = $props.id();
	const callHref = $derived(details.phone_number ? phoneHref(details.phone_number) : null);
	const safeWebsiteHref = $derived(websiteHref(details.website_uri));
</script>

{#if details.rating !== null && Number.isFinite(details.rating)}
	<p class="place-rating">
		{providerName(details.provider)} rating: {details.rating}/5{details.user_rating_count !== null
			? ` from ${details.user_rating_count.toLocaleString()} ratings`
			: ''}
	</p>
{:else}
	<p class="place-missing">Rating unavailable</p>
{/if}

<p class:place-open-status={details.open_now !== null} class:place-missing={details.open_now === null}>
	{details.open_now === true
		? 'Open now'
		: details.open_now === false
			? 'Closed now'
			: 'Current open status unavailable'}
</p>

{#if details.opening_hours.length > 0}
	<h4 class="place-detail-heading">Hours</h4>
	<ul class="place-hours">
		{#each details.opening_hours as description}
			<li class="place-hours-row">{description}</li>
		{/each}
	</ul>
{:else}
	<p class="place-missing">Hours unavailable</p>
{/if}

{#if details.phone_number}
	<div class="place-phone-actions">
		{#if callHref}
			<a class="place-action place-call-action" href={callHref}>
				{businessStatus === null ? 'Call to confirm' : 'Call'}
			</a>
		{/if}
		<button
			type="button"
			class="place-show-number-button"
			aria-controls={`${componentId}-phone-number`}
			aria-expanded={showNumber}
			onclick={() => (showNumber = !showNumber)}
		>
			{showNumber ? 'Hide number' : 'Show number'}
		</button>
	</div>
	<p id={`${componentId}-phone-number`} class="place-phone" hidden={!showNumber}>
		Phone number: {details.phone_number}
	</p>
{:else}
	<p class="place-missing">Phone unavailable</p>
{/if}

{#if safeWebsiteHref}
	<p class="place-website">
		Website:
		<a
			class="place-website-link"
			href={safeWebsiteHref}
			target="_blank"
			rel="noopener noreferrer"
		>
			Visit website
		</a>
	</p>
{:else}
	<p class="place-missing">Website unavailable</p>
{/if}
