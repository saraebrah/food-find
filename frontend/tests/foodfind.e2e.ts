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
					distance_meters: 80
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

	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('button', { name: 'Hide details' }).click();
	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('checkbox', { name: 'Bakery' }).click();
	await page.getByRole('checkbox', { name: 'Thai' }).click();
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
			common_foods: [],
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
