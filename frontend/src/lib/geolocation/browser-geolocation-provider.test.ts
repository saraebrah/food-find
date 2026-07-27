import { describe, expect, it, vi } from 'vitest';

import {
	BrowserGeolocationProvider,
	DEVICE_LOCATION_OPTIONS
} from './browser-geolocation-provider';
import { DeviceLocationError } from './geolocation-provider';

describe('BrowserGeolocationProvider', () => {
	it('requests one fresh high-accuracy position only when invoked', async () => {
		let succeed: PositionCallback | undefined;
		const getCurrentPosition = vi.fn(
			(
				success: PositionCallback,
				_error?: PositionErrorCallback | null,
				_options?: PositionOptions
			) => {
				succeed = success;
			}
		);
		const provider = new BrowserGeolocationProvider({
			getCurrentPosition
		} as unknown as Geolocation);

		expect(getCurrentPosition).not.toHaveBeenCalled();
		const locationPromise = provider.getCurrentLocation();
		expect(getCurrentPosition).toHaveBeenCalledTimes(1);
		expect(getCurrentPosition).toHaveBeenCalledWith(
			expect.any(Function),
			expect.any(Function),
			DEVICE_LOCATION_OPTIONS
		);

		succeed?.({
			coords: {
				accuracy: 24,
				latitude: 43.65012349,
				longitude: -79.39098751
			}
		} as GeolocationPosition);

		await expect(locationPromise).resolves.toEqual({
			coordinates: {
				latitude: 43.65012349,
				longitude: -79.39098751
			},
			accuracyMeters: 24
		});
	});

	it.each([
		[1, 'permission-denied'],
		[2, 'unavailable'],
		[3, 'timeout']
	] as const)('maps browser error %s to %s', async (browserCode, expectedCode) => {
		const geolocation = {
			getCurrentPosition(
				_success: PositionCallback,
				error: PositionErrorCallback
			) {
				error({ code: browserCode } as GeolocationPositionError);
			}
		} as Geolocation;

		await expect(
			new BrowserGeolocationProvider(geolocation).getCurrentLocation()
		).rejects.toMatchObject({
			name: 'DeviceLocationError',
			code: expectedCode
		});
	});

	it('reports unsupported or invalid browser data as unavailable', async () => {
		await expect(
			new BrowserGeolocationProvider(null).getCurrentLocation()
		).rejects.toEqual(new DeviceLocationError('unsupported'));

		const geolocation = {
			getCurrentPosition(success: PositionCallback) {
				success({
					coords: {
						accuracy: Number.NaN,
						latitude: 91,
						longitude: -79
					}
				} as GeolocationPosition);
			}
		} as Geolocation;
		await expect(
			new BrowserGeolocationProvider(geolocation).getCurrentLocation()
		).rejects.toEqual(new DeviceLocationError('unavailable'));
	});
});
