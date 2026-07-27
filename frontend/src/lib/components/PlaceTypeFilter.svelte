<script lang="ts">
	// Retained as an unused legacy component; the active search no longer exposes this filter.
	type LegacyPlaceType = 'restaurant' | 'cafe' | 'bar' | 'bakery';

	interface Props {
		selected: LegacyPlaceType[];
		disabled: boolean;
		onChange: (placeTypes: LegacyPlaceType[]) => void;
	}

	const options: { value: LegacyPlaceType; label: string }[] = [
		{ value: 'restaurant', label: 'Restaurant' },
		{ value: 'cafe', label: 'Café' },
		{ value: 'bar', label: 'Bar' },
		{ value: 'bakery', label: 'Bakery' }
	];

	let { selected, disabled, onChange }: Props = $props();

	function toggle(placeType: LegacyPlaceType, checked: boolean) {
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
