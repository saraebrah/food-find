<script lang="ts">
	import type { PlaceType } from '$lib/types';

	interface Props {
		selected: PlaceType[];
		disabled: boolean;
		onChange: (placeTypes: PlaceType[]) => void;
	}

	const options: { value: PlaceType; label: string }[] = [
		{ value: 'restaurant', label: 'Restaurant' },
		{ value: 'cafe', label: 'Café' },
		{ value: 'bar', label: 'Bar' },
		{ value: 'bakery', label: 'Bakery' }
	];

	let { selected, disabled, onChange }: Props = $props();

	function toggle(placeType: PlaceType, checked: boolean) {
		const selectedTypes = new Set(selected);
		if (checked) selectedTypes.add(placeType);
		else selectedTypes.delete(placeType);
		onChange(options.map(({ value }) => value).filter((value) => selectedTypes.has(value)));
	}
</script>

<fieldset class="place-type-filter" {disabled} aria-describedby="place-type-help">
	<legend>Place type</legend>
	<p id="place-type-help">Choose one or more kinds of food businesses.</p>
	<div class="place-type-options">
		{#each options as option}
			<label class="place-type-option">
				<input
					type="checkbox"
					value={option.value}
					checked={selected.includes(option.value)}
					onchange={(event) =>
						toggle(option.value, (event.currentTarget as HTMLInputElement).checked)}
				/>
				<span>{option.label}</span>
			</label>
		{/each}
	</div>
</fieldset>
