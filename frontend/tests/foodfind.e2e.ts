import { expect, test } from '@playwright/test';

test('searches explicitly and caches an opened place detail response', async ({ page }) => {
	let searchRequests = 0;
	let detailRequests = 0;

	await page.route('**/api/places/search', async (route) => {
		searchRequests += 1;
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
	expect(detailRequests).toBe(0);

	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('button', { name: 'Hide details' }).click();
	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(1);

	await page.getByRole('button', { name: 'Search' }).click();
	await expect(page.getByRole('heading', { name: 'Browser Test Cafe' })).toBeVisible();
	expect(searchRequests).toBe(2);
	await page.getByRole('button', { name: 'View details' }).click();
	await expect(page.getByText('Google Maps rating: 4.5/5 from 42 ratings')).toBeVisible();
	expect(detailRequests).toBe(2);
});
