import type { Place, SelectedLocation } from './types';

export function parseCoordinates(value: string): SelectedLocation | null {
	const parts = value.split(',');
	if (parts.length !== 2) return null;

	const latitude = Number(parts[0].trim());
	const longitude = Number(parts[1].trim());
	if (
		!Number.isFinite(latitude) ||
		!Number.isFinite(longitude) ||
		latitude < -90 ||
		latitude > 90 ||
		longitude < -180 ||
		longitude > 180
	) {
		return null;
	}

	return {
		label: `${latitude}, ${longitude}`,
		latitude,
		longitude
	};
}

export function looksLikeCoordinatePair(value: string): boolean {
	const parts = value.split(',');
	return (
		parts.length === 2 &&
		Number.isFinite(Number(parts[0].trim())) &&
		Number.isFinite(Number(parts[1].trim()))
	);
}

export function providerName(provider: string): string {
	return provider === 'google'
		? 'Google Maps'
		: provider.charAt(0).toUpperCase() + provider.slice(1);
}

export function formatRadius(radiusMeters: number): string {
	return radiusMeters < 1_000 ? `${radiusMeters} m` : `${radiusMeters / 1_000} km`;
}

export function formatDistance(distanceMeters: number | null): string {
	if (distanceMeters === null || !Number.isFinite(distanceMeters) || distanceMeters < 0) {
		return 'Distance unavailable';
	}

	if (distanceMeters < 1_000) return `${Math.round(distanceMeters)} m away`;

	const distanceKilometers = distanceMeters / 1_000;
	const decimalPlaces = distanceKilometers < 10 ? 1 : 0;
	return `${distanceKilometers.toFixed(decimalPlaces)} km away`;
}

export function phoneHref(phoneNumber: string): string | null {
	const prefix = phoneNumber.trim().startsWith('+') ? '+' : '';
	const dialableNumber = phoneNumber.replace(/[^\d*#;,]/g, '');
	return dialableNumber === '' ? null : `tel:${prefix}${dialableNumber}`;
}

export function websiteHref(websiteUri: string | null): string | null {
	if (typeof websiteUri !== 'string' || websiteUri.trim() === '') return null;

	try {
		const url = new URL(websiteUri);
		return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
	} catch {
		return null;
	}
}

type DirectionPlace = Pick<
	Place,
	'provider' | 'provider_place_id' | 'name' | 'address' | 'coordinates'
>;

export function directionsHref(place: DirectionPlace): string | null {
	const { latitude, longitude } = place.coordinates;
	const hasCoordinates =
		Number.isFinite(latitude) &&
		Number.isFinite(longitude) &&
		latitude >= -90 &&
		latitude <= 90 &&
		longitude >= -180 &&
		longitude <= 180;
	const destination = hasCoordinates
		? `${latitude},${longitude}`
		: place.address || place.name;
	if (!destination) return null;

	const url = new URL('https://www.google.com/maps/dir/');
	url.searchParams.set('api', '1');
	url.searchParams.set('destination', destination);
	if (place.provider === 'google' && place.provider_place_id !== '') {
		url.searchParams.set('destination_place_id', place.provider_place_id);
	}
	return url.href;
}
