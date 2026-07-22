<script lang="ts">
	import type { CommonFood, Cuisine } from '$lib/types';

	interface Props {
		cuisines: Cuisine[];
		commonFoods: CommonFood[];
		disabled: boolean;
		onCuisinesChange: (cuisines: Cuisine[]) => void;
		onCommonFoodsChange: (commonFoods: CommonFood[]) => void;
	}

	const cuisineOptions: { value: Cuisine; label: string }[] = [
		{ value: 'chinese', label: 'Chinese' },
		{ value: 'italian', label: 'Italian' },
		{ value: 'persian', label: 'Persian' },
		{ value: 'thai', label: 'Thai' },
		{ value: 'indian', label: 'Indian' }
	];
	const commonFoodOptions: { value: CommonFood; label: string }[] = [
		{ value: 'pizza', label: 'Pizza' },
		{ value: 'burger', label: 'Burgers' },
		{ value: 'steak', label: 'Steak' },
		{ value: 'ramen', label: 'Ramen' },
		{ value: 'kebab', label: 'Kebab' }
	];

	let {
		cuisines,
		commonFoods,
		disabled,
		onCuisinesChange,
		onCommonFoodsChange
	}: Props = $props();

	function toggleCuisine(cuisine: Cuisine, checked: boolean) {
		const selected = new Set(cuisines);
		if (checked) selected.add(cuisine);
		else selected.delete(cuisine);
		onCuisinesChange(
			cuisineOptions.map(({ value }) => value).filter((value) => selected.has(value))
		);
	}

	function toggleCommonFood(commonFood: CommonFood, checked: boolean) {
		const selected = new Set(commonFoods);
		if (checked) selected.add(commonFood);
		else selected.delete(commonFood);
		onCommonFoodsChange(
			commonFoodOptions.map(({ value }) => value).filter((value) => selected.has(value))
		);
	}
</script>

<div class="specialty-filters">
	<fieldset class="choice-filter" aria-describedby="cuisine-help">
		<legend>Cuisine</legend>
		<p id="cuisine-help">Matches any selected cuisine.</p>
		<div class="choice-options">
			{#each cuisineOptions as option}
				<label class="choice-option">
					<input
						type="checkbox"
						value={option.value}
						checked={cuisines.includes(option.value)}
						disabled={disabled}
						onchange={(event) =>
							toggleCuisine(option.value, (event.currentTarget as HTMLInputElement).checked)}
					/>
					<span>{option.label}</span>
				</label>
			{/each}
		</div>
	</fieldset>

	<fieldset class="choice-filter" aria-describedby="common-food-help">
		<legend>Common food</legend>
		<p id="common-food-help">
			Can be combined with cuisine. A match does not confirm current menu availability.
		</p>
		<div class="choice-options">
			{#each commonFoodOptions as option}
				<label class="choice-option">
					<input
						type="checkbox"
						value={option.value}
						checked={commonFoods.includes(option.value)}
						disabled={disabled}
						onchange={(event) =>
							toggleCommonFood(
								option.value,
								(event.currentTarget as HTMLInputElement).checked
							)}
					/>
					<span>{option.label}</span>
				</label>
			{/each}
		</div>
	</fieldset>
</div>
