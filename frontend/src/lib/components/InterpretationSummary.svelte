<script lang="ts">
	import type {
		AvailabilityWindow,
		DescriptiveRequirementKind,
		SearchInterpretation
	} from '$lib/types';

	interface Props {
		interpretation: SearchInterpretation;
		disabled: boolean;
		edited: boolean;
		onAvailabilityChange: (availability: AvailabilityWindow | null) => void;
		onStatus: (message: string) => void;
	}

	const requirementLabels: Record<DescriptiveRequirementKind, string> = {
		dish: 'Dish',
		dietary: 'Dietary',
		atmosphere: 'Atmosphere',
		other: 'Other'
	};

	let {
		interpretation,
		disabled,
		edited,
		onAvailabilityChange,
		onStatus
	}: Props = $props();
	const startsAtValue = $derived(
		interpretation.availability_window
			? toLocalInputValue(interpretation.availability_window.starts_at)
			: ''
	);
	const endsAtValue = $derived(
		interpretation.availability_window
			? toLocalInputValue(interpretation.availability_window.ends_at)
			: ''
	);

	function toLocalInputValue(value: string): string {
		const date = new Date(value);
		const pad = (part: number) => String(part).padStart(2, '0');
		return [
			date.getFullYear(),
			'-',
			pad(date.getMonth() + 1),
			'-',
			pad(date.getDate()),
			'T',
			pad(date.getHours()),
			':',
			pad(date.getMinutes())
		].join('');
	}

	function fromLocalInputValue(value: string): string | null {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) return null;
		const offsetMinutes = -date.getTimezoneOffset();
		const sign = offsetMinutes >= 0 ? '+' : '-';
		const absoluteOffset = Math.abs(offsetMinutes);
		const hours = String(Math.floor(absoluteOffset / 60)).padStart(2, '0');
		const minutes = String(absoluteOffset % 60).padStart(2, '0');
		return `${value}:00${sign}${hours}:${minutes}`;
	}

	function handleStartChange(event: Event) {
		const window = interpretation.availability_window;
		if (!window) return;
		const startsAt = fromLocalInputValue(
			(event.currentTarget as HTMLInputElement).value
		);
		if (!startsAt) return;
		const exactTime = window.starts_at === window.ends_at;
		updateAvailability({
			starts_at: startsAt,
			ends_at: exactTime ? startsAt : window.ends_at
		});
	}

	function handleEndChange(event: Event) {
		const window = interpretation.availability_window;
		if (!window) return;
		const endsAt = fromLocalInputValue(
			(event.currentTarget as HTMLInputElement).value
		);
		if (!endsAt) return;
		updateAvailability({ ...window, ends_at: endsAt });
	}

	function updateAvailability(window: AvailabilityWindow) {
		if (new Date(window.ends_at) < new Date(window.starts_at)) {
			onStatus('The availability end must not be before its start.');
			return;
		}
		onAvailabilityChange(window);
		onStatus('Availability updated. Select Search when you are ready.');
	}
</script>

<section class="interpretation-summary" aria-labelledby="interpretation-heading">
	<div class="interpretation-heading">
		<div>
			<p class="eyebrow">Smart search interpretation</p>
			<h2 id="interpretation-heading">Review what FoodFind understood</h2>
		</div>
		{#if edited}
			<p class="interpretation-edited">You edited the interpreted criteria.</p>
		{/if}
	</div>

	{#if interpretation.availability_window}
		<fieldset class="availability-window" {disabled}>
			<legend>Requested availability</legend>
			<div class="availability-inputs">
				<label>
					Available from
					<input
						type="datetime-local"
						value={startsAtValue}
						onchange={handleStartChange}
					/>
				</label>
				<label>
					Available until
					<input
						type="datetime-local"
						value={endsAtValue}
						min={startsAtValue}
						onchange={handleEndChange}
					/>
				</label>
			</div>
			<p>Timezone: {interpretation.timezone}</p>
			<button
				type="button"
				class="secondary-button"
				onclick={() => {
					onAvailabilityChange(null);
					onStatus('Time preference removed. Select Search when you are ready.');
				}}
			>
				Remove time preference
			</button>
		</fieldset>
	{/if}

	{#if interpretation.assumptions.length > 0}
		<div class="interpretation-group">
			<h3>Assumptions</h3>
			<ul>
				{#each interpretation.assumptions as assumption}
					<li>{assumption.interpretation}</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if interpretation.descriptive_requirements.length > 0}
		<div class="interpretation-group">
			<h3>Text-relevance preferences</h3>
			<ul>
				{#each interpretation.descriptive_requirements as requirement}
					<li>{requirementLabels[requirement.kind]}: {requirement.text}</li>
				{/each}
			</ul>
			<p>These are relevance signals, not verified facts.</p>
		</div>
	{/if}

	{#if interpretation.unsupported_criteria.length > 0}
		<div class="interpretation-group interpretation-warning">
			<h3>Could not apply</h3>
			<ul>
				{#each interpretation.unsupported_criteria as criterion}
					<li>{criterion.text}: {criterion.reason}</li>
				{/each}
			</ul>
			<p>These items are not sent to the place search. Search uses only the supported criteria shown above.</p>
		</div>
	{/if}

	<p class="interpretation-note">
		Review and edit these controls before searching. Text preferences guide Google
		relevance but are not verified facts. With a requested time, FoodFind keeps only
		places whose Google hours confirm they are open during at least part of that window.
	</p>
</section>
