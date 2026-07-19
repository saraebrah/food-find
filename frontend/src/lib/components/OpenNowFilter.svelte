<script lang="ts">
	interface Props {
		checked: boolean;
		disabled: boolean;
		onChange: (checked: boolean) => void;
	}

	let { checked, disabled, onChange }: Props = $props();
</script>

<fieldset class="availability-filter choice-filter">
	<legend>Availability</legend>
	<p>Only include places Google currently reports open.</p>
	<label class="choice-option">
		<input
			type="checkbox"
			{checked}
			{disabled}
			onchange={(event) =>
				onChange((event.currentTarget as HTMLInputElement).checked)}
		/>
		<span>Open now</span>
	</label>
</fieldset>
