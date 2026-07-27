import type { Coordinates } from '$lib/types';

export type DeviceLocationErrorCode =
	| 'permission-denied'
	| 'timeout'
	| 'unavailable'
	| 'unsupported';

export class DeviceLocationError extends Error {
	readonly code: DeviceLocationErrorCode;

	constructor(code: DeviceLocationErrorCode) {
		super(code);
		this.name = 'DeviceLocationError';
		this.code = code;
	}
}

export interface DeviceLocation {
	coordinates: Coordinates;
	accuracyMeters: number;
}

export interface DeviceLocationProvider {
	getCurrentLocation(): Promise<DeviceLocation>;
}
