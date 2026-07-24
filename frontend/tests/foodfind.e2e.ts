import { expect, test } from '@playwright/test';

test('searches explicitly and caches an opened place detail response', async ({ page }) => {
	let searchRequests = 0;
	let detailRequests = 0;
	const searchBodies: unknown[] = [];

	await page.route('**/api/places/search', async (route) => {
		searchRequests += 1;
		searchBodies.push(route.request().postDataJSON());
		await route.fulfill({
			contentType: 'application/json',
			body: JSON.stringify([
				{
					provider: 'google',
					provider_place_id: 'place-1',
					name: 'Browser Test Cafe',
					category: 'Cafe',
					category_code: 'cafe',
					address: '1 Test Street, Toronto, ON',
					coordinates: { latitude: 43.6535, longitude: -79.3833 },
					business_status: 'operational',
					open_now: null,
					rating: 4.7,
					distance_meters: 80,
					match_reasons: [
						{
							kind: 'confirmed',
							text: 'Inside your selected 1 km radius.'
						}
					]
				}
			])
		});
	});

	await page.route('**/api/places/details', async (route) => {
		detailRequests += 1;
		await route.fulfill({
			contentType: 'application/json',
			body: JSON.stringify({
				provider: 'google',
				provider_place_id: 'place-1',
				rating: 4.5,
				user_rating_count: 42,
				open_now: true,
				opening_hours: ['Monday: 8:00 AM – 6:00 PM'],
				phone_number: '+1 416-555-0100',
				website_uri: 'https://example.com/'
			})
		});
	});

	await page.goto('/');
	expect(searchRequests).toBe(0);
	expect(detailRequests).toBe(0);

	await page.getByRole('button', { name: 'Search' }).click();
	await expect(page.getByRole('heading', { name: 'Browser Test Cafe' })).toBeVisible();
	expect(searchRequests).toBe(1);
	expect(searchBodies[0]).toMatchObject({
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
	});
	expect(detailRequests).toBe(0);
	await page.getByText('Why this matched').click();
	await expect(page.getByText('Inside your selected 1 km radius.')).toBeVisible();
	expect(searchRequests).toBe(1);
	expect(detailRequests).toBe(0);

	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('button', { name: 'Hide details' }).click();
	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('checkbox', { name: 'Bakery' }).click();
	await page.getByRole('checkbox', { name: 'Thai' }).click();
	await page.getByRole('checkbox', { name: 'Pizza' }).click();
	await page.getByRole('checkbox', { name: 'Open now' }).click();
	await page.getByRole('checkbox', { name: 'Dine-in' }).click();
	await page.getByRole('checkbox', { name: 'Takeout' }).click();
	await page.getByLabel('Minimum rating').selectOption('4.5');
	await page.getByLabel('Sort').selectOption('rating');
	expect(searchRequests).toBe(1);
	await page.getByRole('button', { name: 'Search' }).click();
	await expect(page.getByRole('heading', { name: 'Browser Test Cafe' })).toBeVisible();
	expect(searchRequests).toBe(2);
	expect(searchBodies[1]).toMatchObject({
		filters: {
			place_types: ['restaurant', 'cafe', 'bakery'],
			cuisines: ['thai'],
			common_foods: ['pizza'],
			open_now: true,
			minimum_rating: 4.5,
			dine_in: true,
			takeout: true
		},
		sort: 'rating'
	});
	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(2);
});

test('applies smart-search criteria once and keeps review edits local', async ({ page }) => {
	let interpretationRequests = 0;
	let searchRequests = 0;
	const searchBodies: unknown[] = [];

	await page.route('**/api/search/interpret', async (route) => {
		interpretationRequests += 1;
		const body = route.request().postDataJSON();
		await route.fulfill({
			contentType: 'application/json',
			body: JSON.stringify({
				search_criteria: {
					...body.search_criteria,
					radius_meters: 2000,
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
						source_text: 'near me',
						interpretation: `Using the selected location: ${body.search_criteria.location.label}`
					}
				],
				unsupported_criteria: [],
				timezone: body.timezone
			})
		});
	});
	await page.route('**/api/places/search', async (route) => {
		searchRequests += 1;
		searchBodies.push(route.request().postDataJSON());
		await route.fulfill({ contentType: 'application/json', body: '[]' });
	});

	await page.goto('/');
	expect(interpretationRequests).toBe(0);
	expect(searchRequests).toBe(0);

	await page
		.getByRole('textbox', { name: 'Smart search' })
		.fill('good rated Persian restaurant serving kebab near me tonight');
	expect(interpretationRequests).toBe(0);
	await page.getByRole('button', { name: 'Apply request' }).click();

	await expect(page.getByText('Review what FoodFind understood')).toBeVisible();
	await expect(page.getByRole('checkbox', { name: 'Persian' })).toBeChecked();
	await expect(page.getByRole('checkbox', { name: 'Kebab' })).toBeChecked();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(0);

	await page.getByRole('checkbox', { name: 'Bakery' }).click();
	await page.getByLabel('Available from').fill('2026-07-23T19:00');
	await expect(page.getByText('You edited the interpreted criteria.')).toBeVisible();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(0);

	await page.getByRole('button', { name: 'Search' }).click();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(1);
	expect(searchBodies[0]).toMatchObject({
		filters: {
			place_types: ['restaurant', 'bakery'],
			cuisines: ['persian'],
			common_foods: ['kebab'],
			open_now: false,
			minimum_rating: 4,
			dine_in: true,
			takeout: false
		},
		descriptive_requirements: [{ text: 'serves kebab', kind: 'dish' }],
		availability_window: {
			starts_at: expect.stringContaining('2026-07-23T19:00:00'),
			ends_at: '2026-07-24T00:00:00-04:00'
		}
	});

	await page.reload();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(1);
});

test('does not retry failed interpretation or empty place search automatically', async ({ page }) => {
	let interpretationRequests = 0;
	let searchRequests = 0;

	await page.route('**/api/search/interpret', async (route) => {
		interpretationRequests += 1;
		await route.fulfill({
			status: 502,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Smart search is temporarily unavailable' })
		});
	});
	await page.route('**/api/places/search', async (route) => {
		searchRequests += 1;
		await route.fulfill({ contentType: 'application/json', body: '[]' });
	});

	await page.goto('/');
	await page
		.getByRole('textbox', { name: 'Smart search' })
		.fill('a request the interpreter cannot safely apply');
	await page.getByRole('button', { name: 'Apply request' }).click();

	await expect(
		page.getByText(
			'Smart search could not apply that request safely. Your current criteria were not changed.'
		)
	).toBeVisible();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(0);

	await page.getByRole('button', { name: 'Search' }).click();
	await expect(
		page.getByText(
			'No places matched the current criteria. Try removing a filter, choosing a larger radius, or selecting another location.'
		)
	).toBeVisible();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(1);

	await page.reload();
	expect(interpretationRequests).toBe(1);
	expect(searchRequests).toBe(1);
});
