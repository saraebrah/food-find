import { describe, expect, it } from 'vitest';

import {
	directionsHref,
	formatDistance,
	looksLikeCoordinatePair,
	parseCoordinates,
	phoneHref,
	websiteHref
} from './search';

describe('coordinate parsing', () => {
	it('normalizes a valid latitude and longitude pair', () => {
		expect(parseCoordinates(' 43.6532, -79.3832 ')).toEqual({
			label: '43.6532, -79.3832',
			latitude: 43.6532,
			longitude: -79.3832
		});
	});

	it('rejects invalid and out-of-range pairs', () => {
		expect(parseCoordinates('Toronto')).toBeNull();
		expect(parseCoordinates('91, -79')).toBeNull();
		expect(parseCoordinates('43, 181')).toBeNull();
	});

	it('recognizes numeric pairs even when their ranges are invalid', () => {
		expect(looksLikeCoordinatePair('91, -79')).toBe(true);
		expect(looksLikeCoordinatePair('Toronto')).toBe(false);
	});
});

describe('result formatting', () => {
	it('formats metres, kilometres, and missing distances', () => {
		expect(formatDistance(421)).toBe('421 m away');
		expect(formatDistance(1_250)).toBe('1.3 km away');
		expect(formatDistance(null)).toBe('Distance unavailable');
	});
});

describe('action URLs', () => {
	it('creates a sanitized telephone URL', () => {
		expect(phoneHref('+1 (416) 555-0100')).toBe('tel:+14165550100');
		expect(phoneHref('not a number')).toBeNull();
	});

	it('accepts only HTTP website URLs', () => {
		expect(websiteHref('https://example.com/menu')).toBe('https://example.com/menu');
		expect(websiteHref('javascript:alert(1)')).toBeNull();
		expect(websiteHref('not a URL')).toBeNull();
	});

	it('builds an encoded Google Maps directions URL without an API key', () => {
		const href = directionsHref({
			provider: 'google',
			provider_place_id: 'google-place-1',
			name: 'Example Restaurant',
			address: '1 Front Street, Toronto, ON',
			coordinates: { latitude: 43.6454, longitude: -79.3805 }
		});

		expect(href).not.toBeNull();
		const url = new URL(href!);
		expect(url.origin + url.pathname).toBe('https://www.google.com/maps/dir/');
		expect(url.searchParams.get('api')).toBe('1');
		expect(url.searchParams.get('destination')).toBe('43.6454,-79.3805');
		expect(url.searchParams.get('destination_place_id')).toBe('google-place-1');
		expect(url.searchParams.has('key')).toBe(false);
	});
});
