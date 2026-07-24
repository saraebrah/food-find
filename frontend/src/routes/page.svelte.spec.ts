import { page } from 'vitest/browser';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import {
	ApiError,
	autocompleteLocations,
	interpretSearch,
	resolveLocation,
	searchPlaces
} from '$lib/api';
import type { Place, SearchInterpretation } from '$lib/types';
import FoodFindPage from './+page.svelte';

vi.mock('$lib/api', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/api')>()),
	autocompleteLocations: vi.fn(),
	interpretSearch: vi.fn(),
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
	distance_meters: 175,
	match_reasons: [
		{ kind: 'confirmed', text: 'Inside your selected 2 km radius.' }
	]
};

const interpretation: SearchInterpretation = {
	search_criteria: {
		location: {
			label: '43.6532, -79.3832',
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
	descriptive_requirements: [{ text: 'serves kebab', kind: 'dish' }],
	availability_window: {
		starts_at: '2026-07-23T18:00:00-04:00',
		ends_at: '2026-07-24T00:00:00-04:00'
	},
	assumptions: [
		{
			source_text: 'good rated',
			interpretation: 'Minimum rating of 4.0'
		},
		{
			source_text: 'near me',
			interpretation: 'Using the selected location: 43.6532, -79.3832'
		}
	],
	unsupported_criteria: [
		{
			text: 'not crowded',
			reason: 'Current crowd levels are unavailable'
		}
	],
	timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
};

describe('FoodFind page request lifecycle', () => {
	beforeEach(() => {
		vi.mocked(searchPlaces).mockReset().mockResolvedValue([placeResult]);
		vi.mocked(autocompleteLocations).mockReset().mockResolvedValue([]);
		vi.mocked(interpretSearch).mockReset().mockResolvedValue(interpretation);
		vi.mocked(resolveLocation).mockReset();
	});

	it('applies one interpretation and keeps later edits local', async () => {
		render(FoodFindPage);

		await page
			.getByRole('textbox', { name: 'Smart search' })
			.fill('good rated Persian restaurant serving kebab near me tonight');
		expect(interpretSearch).not.toHaveBeenCalled();
		await page.getByRole('button', { name: 'Apply request' }).click();

		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
		await expect.element(page.getByRole('checkbox', { name: 'Restaurant' })).toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Café' })).not.toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Persian' })).toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Kebab' })).toBeChecked();
		expect(
			(await page.getByRole('combobox', { name: 'Radius' }).element() as HTMLSelectElement)
				.value
		).toBe('2000');
		expect(
			(
				(await page
					.getByRole('combobox', { name: 'Minimum rating' })
					.element()) as HTMLSelectElement
			).value
		).toBe('4');
		expect(
			(await page.getByRole('combobox', { name: 'Sort' }).element() as HTMLSelectElement)
				.value
		).toBe('rating');
		await expect.element(page.getByText('Minimum rating of 4.0')).toBeVisible();
		await expect
			.element(page.getByText('Using the selected location: 43.6532, -79.3832'))
			.toBeVisible();
		await expect.element(page.getByText('Dish: serves kebab')).toBeVisible();
		await expect
			.element(page.getByText('not crowded: Current crowd levels are unavailable'))
			.toBeVisible();
		await expect
			.element(
				page.getByText(
					'Request applied with 1 unsupported criterion. Review what could not be applied, then select Search to use the supported criteria.'
				)
			)
			.toBeVisible();
		await expect.element(page.getByLabelText('Available from')).toBeVisible();
		await expect.element(page.getByLabelText('Available until')).toBeVisible();

		await page.getByLabelText('Available from').fill('2026-07-23T19:00');
		await page.getByRole('checkbox', { name: 'Bakery' }).click();
		await page.getByLabelText('Minimum rating').selectOptions('4.5');
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
		await expect
			.element(page.getByText('You edited the interpreted criteria.'))
			.toBeVisible();

		await page.getByRole('button', { name: 'Search' }).click();
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).toHaveBeenCalledTimes(1);
		expect(searchPlaces).toHaveBeenCalledWith(
			expect.objectContaining({
				filters: expect.objectContaining({
					place_types: ['restaurant', 'bakery'],
					minimum_rating: 4.5
				}),
				descriptive_requirements: [
					{ text: 'serves kebab', kind: 'dish' }
				],
				availability_window: expect.objectContaining({
					starts_at: expect.stringContaining('2026-07-23T19:00:00')
				})
			}),
			expect.any(AbortSignal)
		);
	});

	it('keeps current criteria after one failed interpretation without retrying', async () => {
		vi.mocked(interpretSearch).mockRejectedValueOnce(new ApiError(502));
		render(FoodFindPage);

		await page
			.getByRole('textbox', { name: 'Smart search' })
			.fill('an unsupported or malformed request');
		await page.getByRole('button', { name: 'Apply request' }).click();

		await expect
			.element(
				page.getByText(
					'Smart search could not apply that request safely. Your current criteria were not changed.'
				)
			)
			.toBeVisible();
		await expect.element(page.getByRole('checkbox', { name: 'Restaurant' })).toBeChecked();
		await expect.element(page.getByRole('checkbox', { name: 'Café' })).toBeChecked();
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('handles failed and empty searches without automatic retries', async () => {
		vi.mocked(searchPlaces)
			.mockRejectedValueOnce(new ApiError(502))
			.mockResolvedValueOnce([]);
		render(FoodFindPage);

		await page.getByRole('button', { name: 'Search' }).click();
		await expect
			.element(
				page.getByText(
					'Search is temporarily unavailable. Select Search to try again.'
				)
			)
			.toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(1);

		await page.getByRole('button', { name: 'Search' }).click();
		await expect
			.element(
				page.getByText(
					'No places matched the current criteria. Try removing a filter, choosing a larger radius, or selecting another location.'
				)
			)
			.toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(2);
	});

	it('explains the unsupported seven-day availability range', async () => {
		vi.mocked(searchPlaces).mockRejectedValueOnce(new ApiError(400));
		render(FoodFindPage);

		await page.getByRole('button', { name: 'Search' }).click();

		await expect
			.element(
				page.getByText(
					'Google can confirm requested opening hours only for today and the next six days. Edit or remove the time preference.'
				)
			)
			.toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
	});

	it('does not request Google-backed data on render or radius changes', async () => {
		render(FoodFindPage);

		await expect.element(page.getByRole('button', { name: 'Search' })).toBeVisible();
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(interpretSearch).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();

		await page.getByLabelText('Radius').selectOptions('2000');
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('combobox', { name: 'Location' }).fill('43.7, -79.4');
		expect(autocompleteLocations).not.toHaveBeenCalled();
		await expect.element(page.getByRole('button', { name: 'Search' })).toBeEnabled();

		await page.getByRole('combobox', { name: 'Location' }).fill('91, -79.4');
		await expect.element(page.getByRole('button', { name: 'Search' })).toBeDisabled();
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(interpretSearch).not.toHaveBeenCalled();
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
				sort: 'provider_default',
				descriptive_requirements: [],
				availability_window: null
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
