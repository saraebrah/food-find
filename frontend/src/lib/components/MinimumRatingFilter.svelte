<script lang="ts">
	import type { MinimumRating, RatingComparison } from '$lib/types';

	interface Props {
		minimumRating: MinimumRating | null;
		ratingComparison: RatingComparison;
		disabled: boolean;
		onChange: (
			minimumRating: MinimumRating | null,
			ratingComparison: RatingComparison
		) => void;
	}

	let { minimumRating, ratingComparison, disabled, onChange }: Props = $props();
	let selectedValue = $state('');
	let customLabel = $state('');
	const presets = [3, 3.5, 4, 4.5];

	$effect(() => {
		const isPreset =
			minimumRating !== null &&
			ratingComparison === 'at_least' &&
			presets.includes(minimumRating);
		selectedValue = minimumRating === null ? '' : isPreset ? String(minimumRating) : 'custom';
		customLabel =
			minimumRating === null
				? ''
				: ratingComparison === 'greater_than'
					? `Greater than ${minimumRating.toFixed(1)} (smart search)`
					: `${minimumRating.toFixed(1)}+ (smart search)`;
	});

	function handleChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		if (value === 'custom') return;
		onChange(value === '' ? null : Number(value), 'at_least');
	}
</script>

<div class="minimum-rating-filter">
	<label for="minimum-rating-select">Minimum rating</label>
	<select
		id="minimum-rating-select"
		name="minimum-rating"
		bind:value={selectedValue}
		{disabled}
		onchange={handleChange}
	>
		<option value="">Any rating</option>
		{#if customLabel}
			<option value="custom" disabled>{customLabel}</option>
		{/if}
		<option value="3">3.0+</option>
		<option value="3.5">3.5+</option>
		<option value="4">4.0+</option>
		<option value="4.5">4.5+</option>
	</select>
	<p>Places without a rating do not match a selected minimum.</p>
</div>
