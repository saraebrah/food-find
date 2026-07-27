import {
	DeviceLocationError,
	type DeviceLocation,
	type DeviceLocationErrorCode,
	type DeviceLocationProvider
} from './geolocation-provider';

export const DEVICE_LOCATION_OPTIONS: PositionOptions = {
	enableHighAccuracy: true,
	maximumAge: 0,
	timeout: 10_000
};

function errorCode(error: GeolocationPositionError): DeviceLocationErrorCode {
	if (error.code === 1) return 'permission-denied';
	if (error.code === 3) return 'timeout';
	return 'unavailable';
}

function validPosition(position: GeolocationPosition): DeviceLocation | null {
	const { accuracy, latitude, longitude } = position.coords;
	if (
		!Number.isFinite(latitude) ||
		!Number.isFinite(longitude) ||
		latitude < -90 ||
		latitude > 90 ||
		longitude < -180 ||
		longitude > 180 ||
		!Number.isFinite(accuracy) ||
		accuracy < 0
	) {
		return null;
	}

	return {
		coordinates: { latitude, longitude },
		accuracyMeters: accuracy
	};
}

export class BrowserGeolocationProvider implements DeviceLocationProvider {
	private readonly geolocation: Geolocation | null;

	constructor(
		geolocation: Geolocation | null =
			typeof navigator === 'undefined' ? null : navigator.geolocation
	) {
		this.geolocation = geolocation ?? null;
	}

	getCurrentLocation(): Promise<DeviceLocation> {
		if (!this.geolocation) {
			return Promise.reject(new DeviceLocationError('unsupported'));
		}

		return new Promise((resolve, reject) => {
			this.geolocation?.getCurrentPosition(
				(position) => {
					const location = validPosition(position);
					if (location) resolve(location);
					else reject(new DeviceLocationError('unavailable'));
				},
				(error) => reject(new DeviceLocationError(errorCode(error))),
				DEVICE_LOCATION_OPTIONS
			);
		});
	}
}

export function createBrowserGeolocationProvider(): DeviceLocationProvider {
	return new BrowserGeolocationProvider();
}
