<script lang="ts">
	import type { MinimumRating } from '$lib/types';

	interface Props {
		minimumRating: MinimumRating | null;
		disabled: boolean;
		onChange: (minimumRating: MinimumRating | null) => void;
	}

	let { minimumRating, disabled, onChange }: Props = $props();

	function handleChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		onChange(value === '' ? null : (Number(value) as MinimumRating));
	}
</script>

<div class="minimum-rating-filter">
	<label for="minimum-rating-select">Minimum rating</label>
	<select
		id="minimum-rating-select"
		name="minimum-rating"
		value={minimumRating ?? ''}
		{disabled}
		onchange={handleChange}
	>
		<option value="">Any rating</option>
		<option value="3">3.0+</option>
		<option value="3.5">3.5+</option>
		<option value="4">4.0+</option>
		<option value="4.5">4.5+</option>
	</select>
	<p>Places without a rating do not match a selected minimum.</p>
</div>
