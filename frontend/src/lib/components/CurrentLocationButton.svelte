<script lang="ts">
	import { onDestroy } from 'svelte';

	import { createBrowserGeolocationProvider } from '$lib/geolocation/browser-geolocation-provider';
	import {
		DeviceLocationError,
		type DeviceLocation,
		type DeviceLocationProvider
	} from '$lib/geolocation/geolocation-provider';

	interface Props {
		disabled: boolean;
		onBusyChange(busy: boolean): void;
		onLocation(location: DeviceLocation): void;
		onStatus(message: string): void;
		provider?: DeviceLocationProvider;
		variant?: 'default' | 'suggestion';
	}

	let {
		disabled,
		onBusyChange,
		onLocation,
		onStatus,
		provider,
		variant = 'default'
	}: Props = $props();
	let locating = $state(false);
	let requestNumber = 0;
	let disposed = false;

	onDestroy(() => {
		disposed = true;
		requestNumber += 1;
	});

	function recoveryMessage(error: unknown): string {
		const code =
			error instanceof DeviceLocationError ? error.code : 'unavailable';
		if (code === 'permission-denied') {
			return 'Location permission was denied. Allow it in your browser settings, or enter a location or choose one on the map.';
		}
		if (code === 'timeout') {
			return 'Finding your location timed out. Try again, or enter a location or choose one on the map.';
		}
		if (code === 'unsupported') {
			return 'Current location is not available in this browser. Enter a location or choose one on the map.';
		}
		return 'Your current location could not be determined. Try again, or enter a location or choose one on the map.';
	}

	async function locate() {
		if (disabled || locating) return;
		const currentRequest = ++requestNumber;
		const activeProvider = provider ?? createBrowserGeolocationProvider();
		locating = true;
		onBusyChange(true);
		onStatus('Finding your current location…');

		try {
			const location = await activeProvider.getCurrentLocation();
			if (disposed || currentRequest !== requestNumber) return;
			onLocation(location);
		} catch (error) {
			if (disposed || currentRequest !== requestNumber) return;
			onStatus(recoveryMessage(error));
		} finally {
			if (!disposed && currentRequest === requestNumber) {
				locating = false;
				onBusyChange(false);
			}
		}
	}
</script>

<button
	type="button"
	class:suggestion-button={variant === 'suggestion'}
	disabled={disabled || locating}
	onclick={locate}
>
	{locating ? 'Finding location…' : 'Use current location'}
</button>
