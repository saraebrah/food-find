import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, getPlaceDetails, searchPlaces } from './api';

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
			radius_meters: 1_000
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
				radius_meters: 1_000
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

	it('preserves the response status without exposing a provider response body', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private', { status: 502 })));

		await expect(
			searchPlaces({
				location: { label: 'Toronto', latitude: 43.65, longitude: -79.38 },
				radius_meters: 1_000
			})
		).rejects.toEqual(new ApiError(502));
	});
});
