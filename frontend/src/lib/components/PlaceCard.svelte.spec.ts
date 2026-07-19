import { page } from 'vitest/browser';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import { getPlaceDetails } from '$lib/api';
import type { Place } from '$lib/types';
import PlaceCard from './PlaceCard.svelte';

vi.mock('$lib/api', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/api')>()),
	getPlaceDetails: vi.fn()
}));

const place: Place = {
	provider: 'google',
	provider_place_id: 'google-place-1',
	name: 'Example Restaurant',
	category: 'Restaurant',
	category_code: 'restaurant',
	address: '1 Front Street, Toronto, ON',
	coordinates: { latitude: 43.6454, longitude: -79.3805 },
	business_status: 'operational',
	open_now: true,
	rating: 4.6,
	dine_in: null,
	takeout: null,
	distance_meters: 421
};

describe('PlaceCard', () => {
	beforeEach(() => {
		vi.mocked(getPlaceDetails).mockReset().mockResolvedValue({
			provider: 'google',
			provider_place_id: 'google-place-1',
			rating: 4.6,
			user_rating_count: 321,
			open_now: true,
			opening_hours: ['Monday: 9:00 AM – 9:00 PM'],
			phone_number: '(416) 555-0100',
			website_uri: 'https://example.com/'
		});
	});

	it('renders summary actions without fetching details', async () => {
		render(PlaceCard, { place });

		await expect.element(page.getByRole('heading', { name: 'Example Restaurant' })).toBeVisible();
		await expect.element(page.getByText('421 m away')).toBeVisible();
		await expect.element(page.getByText('Open now')).toBeVisible();
		await expect.element(page.getByText('Google Maps rating: 4.6/5')).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'Get directions' })).toBeVisible();
		expect(getPlaceDetails).not.toHaveBeenCalled();
	});

	it('fetches details once and reuses them when reopened', async () => {
		render(PlaceCard, { place });

		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('Google Maps rating: 4.6/5 from 321 ratings')).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'Call' })).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'Visit website' })).toBeVisible();
		expect(getPlaceDetails).toHaveBeenCalledTimes(1);

		await page.getByRole('button', { name: 'Hide details' }).click();
		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('Google Maps rating: 4.6/5 from 321 ratings')).toBeVisible();
		expect(getPlaceDetails).toHaveBeenCalledTimes(1);
	});

	it('reveals the full number only when requested', async () => {
		render(PlaceCard, { place });

		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('Phone number: (416) 555-0100')).not.toBeVisible();
		await page.getByRole('button', { name: 'Show number' }).click();
		await expect.element(page.getByText('Phone number: (416) 555-0100')).toBeVisible();
		await page.getByRole('button', { name: 'Hide number' }).click();
		await expect.element(page.getByText('Phone number: (416) 555-0100')).not.toBeVisible();
	});
});
