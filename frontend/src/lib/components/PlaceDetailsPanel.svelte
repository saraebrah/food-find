<script lang="ts">
	import { copyText } from '$lib/clipboard';
	import { phoneHref, providerName, websiteHref, websiteLabel } from '$lib/search';
	import type { BusinessStatus, PlaceDetails } from '$lib/types';

	interface Props {
		details: PlaceDetails;
		businessStatus: BusinessStatus | null;
	}

	let { details, businessStatus }: Props = $props();
	let copyStatus = $state<'idle' | 'copied' | 'error'>('idle');
	let websiteCopyStatus = $state<'idle' | 'copied' | 'error'>('idle');
	const callHref = $derived(details.phone_number ? phoneHref(details.phone_number) : null);
	const safeWebsiteHref = $derived(websiteHref(details.website_uri));
	const safeWebsiteLabel = $derived(safeWebsiteHref ? websiteLabel(safeWebsiteHref) : null);
	const callLabel = $derived(businessStatus === null ? 'Call to confirm' : 'Call');

	async function copyPhoneNumber(): Promise<void> {
		if (!details.phone_number) return;

		copyStatus = 'idle';
		try {
			await copyText(details.phone_number);
			copyStatus = 'copied';
		} catch {
			copyStatus = 'error';
		}
	}

	async function copyWebsite(): Promise<void> {
		if (!safeWebsiteHref) return;

		websiteCopyStatus = 'idle';
		try {
			await copyText(safeWebsiteHref);
			websiteCopyStatus = 'copied';
		} catch {
			websiteCopyStatus = 'error';
		}
	}
</script>

{#if details.rating !== null && Number.isFinite(details.rating)}
	<p class="place-rating">
		{providerName(details.provider)} rating: {details.rating}{details.user_rating_count !== null
			? ` (${details.user_rating_count.toLocaleString()})`
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
	<div class="place-contact-row">
		<span class="place-contact-kind-icon" aria-hidden="true">
			<svg viewBox="0 0 24 24" focusable="false">
				<path d="M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24c1.1.37 2.28.56 3.47.56A1.13 1.13 0 0 1 21 16.65v3.22A1.13 1.13 0 0 1 19.87 21C10.55 21 3 13.45 3 4.13A1.13 1.13 0 0 1 4.13 3h3.23a1.13 1.13 0 0 1 1.12 1.13c0 1.2.19 2.36.56 3.47a1 1 0 0 1-.24 1Z" />
			</svg>
		</span>
		<span class="place-phone-number">{details.phone_number}</span>
		<div class="place-contact-actions">
			{#if callHref}
				<a
					class="place-contact-action place-call-action"
					href={callHref}
					aria-label={`${callLabel} ${details.phone_number}`}
					title={callLabel}
				>
					<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
						<path d="M6.6 10.8a15.5 15.5 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24c1.1.37 2.28.56 3.47.56A1.13 1.13 0 0 1 21 16.65v3.22A1.13 1.13 0 0 1 19.87 21C10.55 21 3 13.45 3 4.13A1.13 1.13 0 0 1 4.13 3h3.23a1.13 1.13 0 0 1 1.12 1.13c0 1.2.19 2.36.56 3.47a1 1 0 0 1-.24 1Z" />
					</svg>
				</a>
			{/if}
			<button
				type="button"
				class="place-contact-action"
				aria-label={`Copy ${details.phone_number}`}
				title="Copy phone number"
				onclick={copyPhoneNumber}
			>
				<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
					<path d="M8 7V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-2" />
					<rect x="3" y="7" width="14" height="14" rx="2" />
				</svg>
			</button>
		</div>
	</div>
	{#if copyStatus !== 'idle'}
		<p class="place-copy-status" role="status" aria-live="polite">
			{copyStatus === 'copied'
				? 'Phone number copied'
				: 'Could not copy automatically. Select the number to copy it.'}
		</p>
	{/if}
{:else}
	<p class="place-missing">Phone unavailable</p>
{/if}

{#if safeWebsiteHref && safeWebsiteLabel}
	<div class="place-contact-row place-website-row">
		<span class="place-contact-kind-icon" aria-hidden="true">
			<svg viewBox="0 0 24 24" focusable="false" class="place-contact-outline-icon">
				<circle cx="12" cy="12" r="9" />
				<path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
			</svg>
		</span>
		<a
			class="place-website-link"
			href={safeWebsiteHref}
			target="_blank"
			rel="noopener noreferrer"
		>
			{safeWebsiteLabel}
		</a>
		<div class="place-contact-actions">
			<a
				class="place-contact-action"
				href={safeWebsiteHref}
				target="_blank"
				rel="noopener noreferrer"
				aria-label={`Open ${safeWebsiteLabel}`}
				title="Open website"
			>
				<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
					<path d="M14 3h7v7M21 3l-9 9" />
					<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
				</svg>
			</a>
			<button
				type="button"
				class="place-contact-action"
				aria-label={`Copy ${safeWebsiteLabel}`}
				title="Copy website link"
				onclick={copyWebsite}
			>
				<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
					<path d="M8 7V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-2" />
					<rect x="3" y="7" width="14" height="14" rx="2" />
				</svg>
			</button>
		</div>
	</div>
	{#if websiteCopyStatus !== 'idle'}
		<p class="place-copy-status" role="status" aria-live="polite">
			{websiteCopyStatus === 'copied'
				? 'Website link copied'
				: 'Could not copy automatically. Open or select the website link instead.'}
		</p>
	{/if}
{:else}
	<p class="place-missing">Website unavailable</p>
{/if}
