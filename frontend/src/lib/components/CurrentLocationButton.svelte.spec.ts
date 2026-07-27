import { page } from 'vitest/browser';
import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import {
	DeviceLocationError,
	type DeviceLocation,
	type DeviceLocationProvider
} from '$lib/geolocation/geolocation-provider';
import CurrentLocationButton from './CurrentLocationButton.svelte';

describe('CurrentLocationButton', () => {
	it('requests location only after a click and reports its busy lifecycle', async () => {
		let resolveLocation:
			| ((location: {
					coordinates: { latitude: number; longitude: number };
					accuracyMeters: number;
			  }) => void)
			| undefined;
		const provider: DeviceLocationProvider = {
			getCurrentLocation: vi.fn(
				() =>
					new Promise<DeviceLocation>((resolve) => {
						resolveLocation = resolve;
					})
			)
		};
		const onBusyChange = vi.fn();
		const onLocation = vi.fn();
		const onStatus = vi.fn();

		render(CurrentLocationButton, {
			disabled: false,
			onBusyChange,
			onLocation,
			onStatus,
			provider
		});

		expect(provider.getCurrentLocation).not.toHaveBeenCalled();
		await page.getByRole('button', { name: 'Use current location' }).click();
		await expect
			.element(page.getByRole('button', { name: 'Finding location…' }))
			.toBeDisabled();
		expect(provider.getCurrentLocation).toHaveBeenCalledTimes(1);
		expect(onBusyChange).toHaveBeenLastCalledWith(true);
		expect(onStatus).toHaveBeenCalledWith('Finding your current location…');

		resolveLocation?.({
			coordinates: { latitude: 43.65, longitude: -79.39 },
			accuracyMeters: 25
		});
		await vi.waitFor(() =>
			expect(onLocation).toHaveBeenCalledWith({
				coordinates: { latitude: 43.65, longitude: -79.39 },
				accuracyMeters: 25
			})
		);
		expect(onBusyChange).toHaveBeenLastCalledWith(false);
	});

	it.each([
		[
			'permission-denied',
			'Location permission was denied. Allow it in your browser settings, or enter a location or choose one on the map.'
		],
		[
			'timeout',
			'Finding your location timed out. Try again, or enter a location or choose one on the map.'
		],
		[
			'unavailable',
			'Your current location could not be determined. Try again, or enter a location or choose one on the map.'
		],
		[
			'unsupported',
			'Current location is not available in this browser. Enter a location or choose one on the map.'
		]
	] as const)('shows recovery guidance for %s', async (code, message) => {
		const provider: DeviceLocationProvider = {
			getCurrentLocation: vi
				.fn()
				.mockRejectedValue(new DeviceLocationError(code))
		};
		const onBusyChange = vi.fn();
		const onStatus = vi.fn();

		render(CurrentLocationButton, {
			disabled: false,
			onBusyChange,
			onLocation: vi.fn(),
			onStatus,
			provider
		});

		await page.getByRole('button', { name: 'Use current location' }).click();
		await vi.waitFor(() => expect(onStatus).toHaveBeenLastCalledWith(message));
		expect(onBusyChange).toHaveBeenLastCalledWith(false);
		await expect
			.element(page.getByRole('button', { name: 'Use current location' }))
			.toBeEnabled();
	});
});
