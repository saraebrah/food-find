<script lang="ts">
	interface Props {
		dineIn: boolean;
		takeout: boolean;
		disabled: boolean;
		onDineInChange: (checked: boolean) => void;
		onTakeoutChange: (checked: boolean) => void;
	}

	let { dineIn, takeout, disabled, onDineInChange, onTakeoutChange }: Props = $props();
</script>

<fieldset class="service-filter choice-filter">
	<legend>Service options</legend>
	<p>Only include places Google explicitly reports offer the selected service.</p>
	<div class="choice-options">
		<label class="choice-option">
			<input
				type="checkbox"
				checked={dineIn}
				{disabled}
				onchange={(event) =>
					onDineInChange((event.currentTarget as HTMLInputElement).checked)}
			/>
			<span>Dine-in</span>
		</label>
		<label class="choice-option">
			<input
				type="checkbox"
				checked={takeout}
				{disabled}
				onchange={(event) =>
					onTakeoutChange((event.currentTarget as HTMLInputElement).checked)}
			/>
			<span>Takeout</span>
		</label>
	</div>
</fieldset>
