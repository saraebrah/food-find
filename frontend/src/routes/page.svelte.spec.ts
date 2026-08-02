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

const mapRenderer = vi.hoisted(() => ({
	mount: vi.fn(),
	render: vi.fn()
}));
const deviceLocationProvider = vi.hoisted(() => ({
	getCurrentLocation: vi.fn()
}));

vi.mock('$env/dynamic/public', () => ({
	env: { PUBLIC_GOOGLE_MAPS_API_KEY: 'test-browser-key' }
}));

vi.mock('$lib/api', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/api')>()),
	autocompleteLocations: vi.fn(),
	interpretSearch: vi.fn(),
	resolveLocation: vi.fn(),
	searchPlaces: vi.fn()
}));

vi.mock('$lib/maps/google-maps-renderer', () => ({
	createGoogleMapsRenderer: vi.fn(() => mapRenderer)
}));
vi.mock('$lib/geolocation/browser-geolocation-provider', () => ({
	createBrowserGeolocationProvider: vi.fn(() => deviceLocationProvider)
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
			cuisines: ['persian'],
			common_foods: ['kebab'],
			open_now: false,
			minimum_rating: 4,
			rating_comparison: 'at_least',
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

async function chooseTorontoLocation() {
	await page
		.getByRole('combobox', { name: 'Location' })
		.fill('43.6532, -79.3832');
}

describe('FoodFind page request lifecycle', () => {
	beforeEach(() => {
		mapRenderer.render.mockReset();
		mapRenderer.mount
			.mockReset()
			.mockResolvedValue({ destroy: vi.fn(), render: mapRenderer.render });
		vi.mocked(searchPlaces).mockReset().mockResolvedValue([placeResult]);
		vi.mocked(autocompleteLocations).mockReset().mockResolvedValue([]);
		vi.mocked(interpretSearch).mockReset().mockResolvedValue(interpretation);
		vi.mocked(resolveLocation).mockReset();
		deviceLocationProvider.getCurrentLocation.mockReset().mockResolvedValue({
			coordinates: { latitude: 43.65, longitude: -79.39 },
			accuracyMeters: 25
		});
	});

	it('offers current location when the empty Location field is opened', async () => {
		render(FoodFindPage);

		await expect
			.element(page.getByRole('button', { name: 'Use current location' }))
			.not.toBeInTheDocument();
		await page.getByRole('combobox', { name: 'Location' }).click();
		await expect
			.element(page.getByRole('button', { name: 'Use current location' }))
			.toBeVisible();
		expect(deviceLocationProvider.getCurrentLocation).not.toHaveBeenCalled();
	});

	it('applies one interpretation and keeps later edits local', async () => {
		render(FoodFindPage);
		await chooseTorontoLocation();

		await page
			.getByRole('textbox', { name: 'Smart search' })
			.fill('good rated Persian restaurant serving kebab near me tonight');
		expect(interpretSearch).not.toHaveBeenCalled();
		await page.getByRole('button', { name: 'Apply request' }).click();

		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
		await expect
			.element(page.getByRole('group', { name: 'Place type' }))
			.not.toBeInTheDocument();
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
					'Request applied with 1 unsupported criterion. Review what could not be applied, then select Search places to use the supported criteria.'
				)
			)
			.toBeVisible();
		await expect.element(page.getByLabelText('Available from')).toBeVisible();
		await expect.element(page.getByLabelText('Available until')).toBeVisible();

		await page.getByLabelText('Available from').fill('2026-07-23T19:00');
		await page.getByLabelText('Minimum rating').selectOptions('4.5');
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
		await expect
			.element(page.getByText('You edited the interpreted criteria.'))
			.toBeVisible();

		await page.getByRole('button', { name: 'Search places' }).click();
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).toHaveBeenCalledTimes(1);
		expect(searchPlaces).toHaveBeenCalledWith(
			expect.objectContaining({
				filters: expect.objectContaining({
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

	it('preserves an exact smart-search rating until a manual preset replaces it', async () => {
		vi.mocked(interpretSearch).mockResolvedValueOnce({
			...interpretation,
			search_criteria: {
				...interpretation.search_criteria,
				filters: {
					...interpretation.search_criteria.filters,
					minimum_rating: 4.8,
					rating_comparison: 'greater_than'
				}
			},
			availability_window: null,
			assumptions: [],
			unsupported_criteria: []
		});
		render(FoodFindPage);
		await chooseTorontoLocation();
		await page
			.getByRole('textbox', { name: 'Smart search' })
			.fill('burger with rating greater than 4.8');

		await page.getByRole('button', { name: 'Apply request' }).click();

		await expect
			.element(page.getByRole('option', { name: 'Greater than 4.8 (smart search)' }))
			.toBeInTheDocument();
		expect(
			(await page.getByLabelText('Minimum rating').element() as HTMLSelectElement).value
		).toBe('custom');
		await page.getByRole('button', { name: 'Search places' }).click();
		expect(searchPlaces).toHaveBeenLastCalledWith(
			expect.objectContaining({
				filters: expect.objectContaining({
					minimum_rating: 4.8,
					rating_comparison: 'greater_than'
				})
			}),
			expect.any(AbortSignal)
		);

		await page.getByLabelText('Minimum rating').selectOptions('4.5');
		await page.getByRole('button', { name: 'Search places' }).click();
		expect(searchPlaces).toHaveBeenLastCalledWith(
			expect.objectContaining({
				filters: expect.objectContaining({
					minimum_rating: 4.5,
					rating_comparison: 'at_least'
				})
			}),
			expect.any(AbortSignal)
		);
	});

	it('keeps current criteria after one failed interpretation without retrying', async () => {
		vi.mocked(interpretSearch).mockRejectedValueOnce(new ApiError(502));
		render(FoodFindPage);
		await chooseTorontoLocation();

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
		await expect
			.element(page.getByRole('group', { name: 'Place type' }))
			.not.toBeInTheDocument();
		expect(interpretSearch).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('handles failed and empty searches without automatic retries', async () => {
		vi.mocked(searchPlaces)
			.mockRejectedValueOnce(new ApiError(502))
			.mockResolvedValueOnce([]);
		render(FoodFindPage);
		await chooseTorontoLocation();

		await page.getByRole('button', { name: 'Search places' }).click();
		await expect
			.element(
				page.getByText(
					'Search is temporarily unavailable. Select Search places to try again.'
				)
			)
			.toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(1);

		await page.getByRole('button', { name: 'Search places' }).click();
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
		await chooseTorontoLocation();

		await page.getByRole('button', { name: 'Search places' }).click();

		await expect
			.element(
				page.getByText(
					'Google can confirm requested opening hours only for today and the next six days. Edit or remove the time preference.'
				)
			)
			.toBeVisible();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
	});

	it('updates the map without requesting Places or Gemini on render or radius changes', async () => {
		render(FoodFindPage);

		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('');
		await expect
			.element(page.getByRole('button', { name: 'Search places' }))
			.toBeDisabled();
		await expect
			.element(page.getByRole('list', { name: 'Search requirements' }))
			.not.toBeInTheDocument();
		await expect
			.element(page.getByText(/Place type (ready|required)/))
			.not.toBeInTheDocument();
		const locationInput = await page
			.getByRole('combobox', { name: 'Location' })
			.element();
		const mapRegion = await page
			.getByRole('region', { name: 'FoodFind map' })
			.element();
		const smartSearch = await page
			.getByRole('textbox', { name: 'Smart search' })
			.element();
		const searchButton = await page
			.getByRole('button', { name: 'Search places' })
			.element();
		expect(
			locationInput.compareDocumentPosition(mapRegion) &
				Node.DOCUMENT_POSITION_FOLLOWING
		).toBeTruthy();
		expect(
			mapRegion.compareDocumentPosition(smartSearch) &
				Node.DOCUMENT_POSITION_FOLLOWING
		).toBeTruthy();
		expect(
			smartSearch.compareDocumentPosition(searchButton) &
				Node.DOCUMENT_POSITION_FOLLOWING
		).toBeTruthy();
		expect(mapRenderer.mount).toHaveBeenCalledTimes(1);
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith({
				center: { latitude: 43.6532, longitude: -79.3832 },
				radiusMeters: 1_000,
				places: [],
				selectedPlaceKey: null,
				locationSelectionEnabled: true,
				searchAreaSelected: false
			})
		);
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(interpretSearch).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();
		expect(deviceLocationProvider.getCurrentLocation).not.toHaveBeenCalled();

		await page.getByLabelText('Radius').selectOptions('2000');
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith({
				center: { latitude: 43.6532, longitude: -79.3832 },
				radiusMeters: 2_000,
				places: [],
				selectedPlaceKey: null,
				locationSelectionEnabled: true,
				searchAreaSelected: false
			})
		);
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('combobox', { name: 'Location' }).fill('43.7, -79.4');
		expect(autocompleteLocations).not.toHaveBeenCalled();
		await expect
			.element(page.getByRole('button', { name: 'Search places' }))
			.toBeEnabled();
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith({
				center: { latitude: 43.7, longitude: -79.4 },
				radiusMeters: 2_000,
				places: [],
				selectedPlaceKey: null,
				locationSelectionEnabled: true,
				searchAreaSelected: true
			})
		);

		await page.getByRole('combobox', { name: 'Location' }).fill('91, -79.4');
		await expect
			.element(page.getByRole('button', { name: 'Search places' }))
			.toBeDisabled();
		expect(mapRenderer.render).toHaveBeenLastCalledWith({
			center: { latitude: 43.7, longitude: -79.4 },
			radiusMeters: 2_000,
			places: [],
			selectedPlaceKey: null,
			locationSelectionEnabled: true,
			searchAreaSelected: false
		});
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(interpretSearch).not.toHaveBeenCalled();
	});

	it('cancels stale autocomplete as soon as device location begins', async () => {
		let resolveAutocomplete:
			| ((suggestions: Array<{
					provider: string;
					provider_place_id: string;
					label: string;
			  }>) => void)
			| undefined;
		let resolveDeviceLocation:
			| ((location: {
					coordinates: { latitude: number; longitude: number };
					accuracyMeters: number;
			  }) => void)
			| undefined;
		vi.mocked(autocompleteLocations).mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					resolveAutocomplete = resolve;
				})
		);
		deviceLocationProvider.getCurrentLocation.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					resolveDeviceLocation = resolve;
				})
		);
		render(FoodFindPage);

		await page.getByRole('combobox', { name: 'Location' }).fill('Toronto');
		await vi.waitFor(() => expect(autocompleteLocations).toHaveBeenCalledTimes(1));
		const autocompleteSignal = vi.mocked(autocompleteLocations).mock.calls[0][2];

		await page.getByRole('button', { name: 'Use current location' }).click();
		expect(autocompleteSignal).toBeInstanceOf(AbortSignal);
		expect(autocompleteSignal?.aborted).toBe(true);
		await expect
			.element(page.getByRole('button', { name: 'Finding location…' }))
			.toBeDisabled();

		resolveDeviceLocation?.({
			coordinates: { latitude: 43.65, longitude: -79.39 },
			accuracyMeters: 25
		});
		resolveAutocomplete?.([
			{
				provider: 'google',
				provider_place_id: 'stale-place',
				label: 'Stale Toronto suggestion'
			}
		]);

		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('Current location');
		await expect
			.element(page.getByText('Stale Toronto suggestion'))
			.not.toBeInTheDocument();
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('takes one criteria snapshot and makes one request for an explicit search', async () => {
		render(FoodFindPage);
		await chooseTorontoLocation();

		await page.getByRole('button', { name: 'Search places' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();
		const directionsUrl = new URL(
			(
				(await page.getByRole('link', { name: 'Get directions' }).element()) as HTMLAnchorElement
			).href
		);
		expect(directionsUrl.searchParams.get('origin')).toBe('43.6532,-79.3832');
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith({
				center: { latitude: 43.6532, longitude: -79.3832 },
				radiusMeters: 1_000,
				places: [
					{
						key: 'google:place-1',
						title: 'Test Kitchen',
						coordinates: { latitude: 43.6525, longitude: -79.3817 }
					}
				],
				selectedPlaceKey: null,
				locationSelectionEnabled: true,
				searchAreaSelected: true
			})
		);
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
					cuisines: [],
					common_foods: [],
					open_now: false,
					minimum_rating: null,
					rating_comparison: 'at_least',
					dine_in: false,
					takeout: false
				},
				sort: 'provider_default',
				descriptive_requirements: [],
				availability_window: null
			},
			expect.any(AbortSignal)
		);

		await page.getByRole('checkbox', { name: 'Mexican' }).click();
		await expect
			.element(page.getByRole('heading', { name: 'Test Kitchen' }))
			.not.toBeInTheDocument();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
	});

	it('synchronizes marker and card selection without fetching details', async () => {
		render(FoodFindPage);
		await chooseTorontoLocation();
		await page.getByRole('button', { name: 'Search places' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();

		const mountOptions = mapRenderer.mount.mock.calls[0][1];
		mountOptions.onPlaceSelect('google:place-1');

		await expect
			.element(page.getByRole('button', { name: 'Test Kitchen selected on map' }))
			.toHaveAttribute('aria-pressed', 'true');
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith(
				expect.objectContaining({ selectedPlaceKey: 'google:place-1' })
			)
		);
		expect(searchPlaces).toHaveBeenCalledTimes(1);

		await page.getByRole('button', { name: 'Test Kitchen selected on map' }).click();
		expect(searchPlaces).toHaveBeenCalledTimes(1);
	});

	it('sets a map location, clears stale results, and waits for Search', async () => {
		render(FoodFindPage);
		await chooseTorontoLocation();
		await page.getByRole('button', { name: 'Search places' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();

		const mountOptions = mapRenderer.mount.mock.calls[0][1];
		mountOptions.onLocationSelect({
			latitude: 43.65012349,
			longitude: -79.39098751
		});

		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('43.650123, -79.390988');
		await expect
			.element(page.getByRole('heading', { name: 'Test Kitchen' }))
			.not.toBeInTheDocument();
		await expect
			.element(
				page.getByText('Map location selected. Select Search places when you are ready.')
			)
			.toBeVisible();
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith({
				center: { latitude: 43.650123, longitude: -79.390988 },
				radiusMeters: 1_000,
				places: [],
				selectedPlaceKey: null,
				locationSelectionEnabled: true,
				searchAreaSelected: true
			})
		);
		expect(searchPlaces).toHaveBeenCalledTimes(1);
		expect(interpretSearch).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Search places' }).click();
		expect(searchPlaces).toHaveBeenCalledTimes(2);
		expect(searchPlaces).toHaveBeenLastCalledWith(
			expect.objectContaining({
				location: {
					label: '43.650123, -79.390988',
					latitude: 43.650123,
					longitude: -79.390988
				}
			}),
			expect.any(AbortSignal)
		);
	});

	it('uses one device position, warns about poor accuracy, and waits for Search', async () => {
		let resolveDeviceLocation:
			| ((location: {
					coordinates: { latitude: number; longitude: number };
					accuracyMeters: number;
			  }) => void)
			| undefined;
		deviceLocationProvider.getCurrentLocation.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					resolveDeviceLocation = resolve;
				})
		);
		render(FoodFindPage);
		await chooseTorontoLocation();
		await page.getByRole('button', { name: 'Search places' }).click();
		await expect.element(page.getByRole('heading', { name: 'Test Kitchen' })).toBeVisible();
		expect(deviceLocationProvider.getCurrentLocation).not.toHaveBeenCalled();

		await page.getByRole('combobox', { name: 'Location' }).click();
		await page.getByRole('button', { name: 'Use current location' }).click();
		await expect
			.element(page.getByRole('button', { name: 'Finding location…' }))
			.toBeDisabled();
		await expect.element(page.getByRole('button', { name: 'Search places' })).toBeDisabled();
		expect(deviceLocationProvider.getCurrentLocation).toHaveBeenCalledTimes(1);

		resolveDeviceLocation?.({
			coordinates: {
				latitude: 43.65012349,
				longitude: -79.39098751
			},
			accuracyMeters: 2_500
		});

		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('Current location');
		await expect
			.element(page.getByText(/browser estimates accuracy within 2.5 km/))
			.toBeVisible();
		await expect
			.element(page.getByRole('heading', { name: 'Test Kitchen' }))
			.not.toBeInTheDocument();
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith(
				expect.objectContaining({
					center: { latitude: 43.650123, longitude: -79.390988 },
					places: []
				})
			)
		);
		expect(searchPlaces).toHaveBeenCalledTimes(1);
		expect(interpretSearch).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Search places' }).click();
		expect(searchPlaces).toHaveBeenCalledTimes(2);
		expect(searchPlaces).toHaveBeenLastCalledWith(
			expect.objectContaining({
				location: {
					label: 'Current location',
					latitude: 43.650123,
					longitude: -79.390988
				}
			}),
			expect.any(AbortSignal)
		);
	});

	it('accepts a device position within the selected search radius without searching', async () => {
		render(FoodFindPage);

		await page.getByRole('combobox', { name: 'Location' }).click();
		await page.getByRole('button', { name: 'Use current location' }).click();

		await expect
			.element(
				page.getByText('Current location selected. Select Search places when you are ready.')
			)
			.toBeVisible();
		await expect
			.element(page.getByRole('combobox', { name: 'Location' }))
			.toHaveValue('Current location');
		await vi.waitFor(() =>
			expect(mapRenderer.render).toHaveBeenLastCalledWith(
				expect.objectContaining({
					center: { latitude: 43.65, longitude: -79.39 },
					searchAreaSelected: true
				})
			)
		);
		expect(deviceLocationProvider.getCurrentLocation).toHaveBeenCalledTimes(1);
		expect(searchPlaces).not.toHaveBeenCalled();
		expect(interpretSearch).not.toHaveBeenCalled();
		expect(autocompleteLocations).not.toHaveBeenCalled();
	});

	it('applies higher-tier filters and rating sorting only on explicit search', async () => {
		render(FoodFindPage);
		await chooseTorontoLocation();

		await page.getByRole('checkbox', { name: 'Mexican' }).click();
		await page.getByRole('checkbox', { name: 'Pizza' }).click();
		await expect.element(page.getByRole('checkbox', { name: 'Pizza' })).toBeEnabled();
		await page.getByRole('checkbox', { name: 'Open now' }).click();
		await page.getByRole('checkbox', { name: 'Dine-in' }).click();
		await page.getByRole('checkbox', { name: 'Takeout' }).click();
		await page.getByLabelText('Minimum rating').selectOptions('4.5');
		await page.getByLabelText('Sort').selectOptions('rating');
		expect(searchPlaces).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Search places' }).click();
		expect(searchPlaces).toHaveBeenCalledWith(
			expect.objectContaining({
				filters: {
					cuisines: ['mexican'],
					common_foods: ['pizza'],
					open_now: true,
					minimum_rating: 4.5,
					rating_comparison: 'at_least',
					dine_in: true,
					takeout: true
				},
				sort: 'rating'
			}),
			expect.any(AbortSignal)
		);
	});

	it('offers the expanded cuisine choices without searching', async () => {
		render(FoodFindPage);

		for (const cuisine of [
			'Mexican',
			'Japanese',
			'Korean',
			'Vietnamese',
			'Mediterranean'
		]) {
			await expect
				.element(page.getByRole('checkbox', { name: cuisine }))
				.toBeVisible();
		}
		expect(searchPlaces).not.toHaveBeenCalled();
	});

	it('offers the expanded common-food choices without searching', async () => {
		render(FoodFindPage);

		for (const food of [
			'Shawarma',
			'Ice cream',
			'Dessert',
			'Sweets',
			'Drinks',
			'Sushi',
			'Tacos',
			'Salad',
			'Soup',
			'Pasta'
		]) {
			await expect
				.element(page.getByRole('checkbox', { name: food }))
				.toBeVisible();
		}
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
