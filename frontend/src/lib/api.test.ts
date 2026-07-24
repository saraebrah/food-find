import { afterEach, describe, expect, it, vi } from 'vitest';

import {
	ApiError,
	getPlaceDetails,
	interpretSearch,
	searchPlaces
} from './api';
import type { SearchCriteria } from './types';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('FoodFind API client', () => {
	it('posts one normalized criteria snapshot to the search endpoint', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response('[]', {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);

		await searchPlaces({
			location: {
				label: 'Toronto City Hall',
				latitude: 43.6532,
				longitude: -79.3832
			},
			radius_meters: 1_000,
			filters: {
				place_types: ['restaurant', 'cafe'],
				cuisines: [],
				common_foods: [],
				open_now: false,
				minimum_rating: null,
				dine_in: false,
				takeout: false
			},
			sort: 'provider_default',
			descriptive_requirements: [
				{ text: 'quiet atmosphere', kind: 'atmosphere' }
			],
			availability_window: {
				starts_at: '2026-07-23T18:00:00-04:00',
				ends_at: '2026-07-24T00:00:00-04:00'
			}
		});

		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(fetchMock).toHaveBeenCalledWith('/api/places/search', {
			method: 'POST',
			headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
			body: JSON.stringify({
				location: {
					label: 'Toronto City Hall',
					latitude: 43.6532,
					longitude: -79.3832
				},
				radius_meters: 1_000,
				filters: {
					place_types: ['restaurant', 'cafe'],
					cuisines: [],
					common_foods: [],
					open_now: false,
					minimum_rating: null,
					dine_in: false,
					takeout: false
				},
				sort: 'provider_default',
				descriptive_requirements: [
					{ text: 'quiet atmosphere', kind: 'atmosphere' }
				],
				availability_window: {
					starts_at: '2026-07-23T18:00:00-04:00',
					ends_at: '2026-07-24T00:00:00-04:00'
				}
			}),
			signal: undefined
		});
	});

	it('requests details only for the selected provider reference', async () => {
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					provider: 'google',
					provider_place_id: 'google-place-1',
					rating: null,
					user_rating_count: null,
					open_now: null,
					opening_hours: [],
					phone_number: null,
					website_uri: null
				}),
				{ status: 200, headers: { 'Content-Type': 'application/json' } }
			)
		);
		vi.stubGlobal('fetch', fetchMock);

		await getPlaceDetails('google', 'google-place-1');

		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
			provider: 'google',
			provider_place_id: 'google-place-1'
		});
	});

	it('posts one smart-search snapshot to the interpretation endpoint', async () => {
		const interpretation = {
			search_criteria: {
				location: {
					label: 'Toronto City Hall',
					latitude: 43.6532,
					longitude: -79.3832
				},
				radius_meters: 2_000,
				filters: {
					place_types: ['restaurant'],
					cuisines: ['persian'],
					common_foods: ['kebab'],
					open_now: false,
					minimum_rating: 4,
					dine_in: true,
					takeout: false
				},
				sort: 'rating'
			},
			descriptive_requirements: [],
			availability_window: null,
			assumptions: [],
			unsupported_criteria: [],
			timezone: 'America/Toronto'
		};
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(JSON.stringify(interpretation), {
				status: 200,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		vi.stubGlobal('fetch', fetchMock);
		const criteria: SearchCriteria = {
			location: {
				label: 'Toronto City Hall',
				latitude: 43.6532,
				longitude: -79.3832
			},
			radius_meters: 1_000,
			filters: {
				place_types: ['restaurant', 'cafe'],
				cuisines: [],
				common_foods: [],
				open_now: false,
				minimum_rating: null,
				dine_in: false,
				takeout: false
			},
			sort: 'provider_default'
		};

		await interpretSearch(
			'good rated Persian restaurant near me',
			criteria,
			'America/Toronto'
		);

		expect(fetchMock).toHaveBeenCalledTimes(1);
		expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
			query: 'good rated Persian restaurant near me',
			search_criteria: criteria,
			timezone: 'America/Toronto'
		});
	});

	it('preserves the response status without exposing a provider response body', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private', { status: 502 })));

		await expect(
			searchPlaces({
				location: { label: 'Toronto', latitude: 43.65, longitude: -79.38 },
				radius_meters: 1_000,
				filters: {
					place_types: ['restaurant', 'cafe'],
					cuisines: [],
					common_foods: [],
					open_now: false,
					minimum_rating: null,
					dine_in: false,
					takeout: false
				},
				sort: 'provider_default',
				descriptive_requirements: [],
				availability_window: null
			})
		).rejects.toEqual(new ApiError(502));
	});
});
