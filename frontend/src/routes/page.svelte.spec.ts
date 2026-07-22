import { page } from 'vitest/browser';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import { autocompleteLocations, resolveLocation, searchPlaces } from '$lib/api';
import type { Place } from '$lib/types';
import FoodFindPage from './+page.svelte';

vi.mock('$lib/api', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/api')>()),
	autocompleteLocations: vi.fn(),
	resolveLocation: vi.fn(),
	searchPlaces: vi.fn()
}));

const placeResult: Place = {
	provider: 'google',
	provider_place_id: 'place-1',
	name: 'Test Kitchen',
	category: 'Restaurant',
	category_code: 'restaurant',
	address: '100 Queen Street West, Toronto, ON',
	coordinates: { latitude: 43.6525, longitude: -79.3817 },
	business_status: 'operational',
	open_now: null,
	rating: null,
	dine_in: null,
	takeout: null,
	distance_meters: 175
};

describe('FoodFind page request lifecycle', () => {
	beforeEach(() => {
		vi.mocked(searchPlaces).mockReset().mockResolvedValue([placeResult]);
		vi.mocked(autocompleteLocations).mockReset().mockResolvedValue([]);
		vi.mocked(resolveLocation).mockReset();
	});

	it('does not request Google-backed data on render or radius changes', async () => {
		render(FoodFindPage);

		await expect.element(page.getByRole('button', { name: 'Search' })).toBeVisible();
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();

		await page.getByLabelText('Radius').selectOptions('2000');
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('combobox', { name: 'Location' }).fill('43.7, -79.4');
		expect(autocompleteLocations).not.toHaveBeenCalled();
		await expect.element(page.getByRole('button', { name: 'Search' })).toBeEnabled();

		await page.getByRole('combobox', { name: 'Location' }).fill('91, -79.4');
		await expect.element(page.getByRole('button', { name: 'Search' })).toBeDisabled();
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('takes one criteria snapshot and makes one request for an explicit search', async () => {
		render(FoodFindPage);

		await page.getByRole('button', { name: 'Search' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
		expect(searchPlaces).toHaveBeenCalledWith(
			{
				location: {
					label: '43.6532, -79.3832',
					latitude: 43.6532,
					longitude: -79.3832
				},
				radius_meters: 1000,
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
			},
			expect.any(AbortSignal)
		);

		await page.getByRole('checkbox', { name: 'Bakery' }).click();
		await expect
			.element(page.getByRole('heading', { name: 'Test Kitchen' }))
			.not.toBeInTheDocument();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
	});

	it('changes place types without searching and snapshots the chosen types', async () => {
		render(FoodFindPage);

		await expect.element(page.getByRole('checkbox', { name: 'Restaurant' })).toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Café' })).toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Bar' })).not.toBeChecked();
		await page.getByRole('checkbox', { name: 'Bar' }).click();
		await page.getByRole('checkbox', { name: 'Restaurant' }).click();
		await page.getByRole('checkbox', { name: 'Café' }).click();
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Search' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();
		expect(searchPlaces).toHaveBeenCalledWith(
			expect.objectContaining({
				filters: {
					place_types: ['bar'],
					cuisines: [],
					common_foods: [],
					open_now: false,
					minimum_rating: null,
					dine_in: false,
					takeout: false
				}
			}),
			expect.any(AbortSignal)
		);
	});

	it('applies higher-tier filters and rating sorting only on explicit search', async () => {
		render(FoodFindPage);

		await page.getByRole('checkbox', { name: 'Italian' }).click();
		await page.getByRole('checkbox', { name: 'Pizza' }).click();
		await expect.element(page.getByRole('checkbox', { name: 'Pizza' })).toBeEnabled();
		await page.getByRole('checkbox', { name: 'Open now' }).click();
		await page.getByRole('checkbox', { name: 'Dine-in' }).click();
		await page.getByRole('checkbox', { name: 'Takeout' }).click();
		await page.getByLabelText('Minimum rating').selectOptions('4.5');
		await page.getByLabelText('Sort').selectOptions('rating');
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Search' }).click();
		expect(searchPlaces).toHaveBeenCalledWith(
			expect.objectContaining({
				filters: {
					place_types: ['restaurant', 'cafe'],
					cuisines: ['italian'],
					common_foods: ['pizza'],
					open_now: true,
					minimum_rating: 4.5,
					dine_in: true,
					takeout: true
				},
				sort: 'rating'
			}),
			expect.any(AbortSignal)
		);
	});

	it('requires at least one place type before searching', async () => {
		render(FoodFindPage);

		await page.getByRole('checkbox', { name: 'Restaurant' }).click();
		await page.getByRole('checkbox', { name: 'Café' }).click();
		await expect.element(page.getByRole('button', { name: 'Search' })).toBeDisabled();
		await expect.element(page.getByText('Choose at least one place type.')).toBeVisible();
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('resolves a chosen address once without starting a place search', async () => {
		vi.mocked(autocompleteLocations).mockResolvedValue([
			{ provider: 'google', provider_place_id: 'location-1', label: 'Toronto City Hall' }
		]);
		vi.mocked(resolveLocation).mockResolvedValue({
			provider: 'google',
			provider_place_id: 'location-1',
			label: 'Toronto City Hall, Toronto, ON, Canada',
			latitude: 43.6534,
			longitude: -79.3841
		});
		render(FoodFindPage);

		await page.getByRole('combobox', { name: 'Location' }).fill('Toronto City Hall');
		await expect.element(page.getByRole('button', { name: 'Toronto City Hall' })).toBeVisible();
		await page.getByRole('button', { name: 'Toronto City Hall' }).click();
		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('Toronto City Hall, Toronto, ON, Canada');

		expect(autocompleteLocations).toHaveBeenCalledTimes(1);
		expect(resolveLocation).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
	});
});
