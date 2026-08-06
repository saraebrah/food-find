import { page } from 'vitest/browser';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import { getPlaceDetails } from '$lib/api';
import { copyText } from '$lib/clipboard';
import type { Place } from '$lib/types';
import PlaceCard from './PlaceCard.svelte';

vi.mock('$lib/api', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/api')>()),
	getPlaceDetails: vi.fn()
}));

vi.mock('$lib/clipboard', () => ({
	copyText: vi.fn()
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
	distance_meters: 421,
	match_reasons: [
		{ kind: 'confirmed', text: 'Inside your selected 1 km radius.' },
		{
			kind: 'relevance',
			text: 'Kebab availability is not verified—check the menu or call.'
		}
	]
};

const origin = {
	label: 'Toronto City Hall',
	latitude: 43.6532,
	longitude: -79.3832,
	provider: 'google',
	provider_place_id: 'origin-place-1'
};

describe('PlaceCard', () => {
	beforeEach(() => {
		vi.mocked(copyText).mockReset().mockResolvedValue();
		vi.mocked(getPlaceDetails).mockReset().mockResolvedValue({
			provider: 'google',
			provider_place_id: 'google-place-1',
			rating: 4.6,
			user_rating_count: 321,
			open_now: true,
			opening_hours: ['Monday: 9:00 AM – 9:00 PM'],
			phone_number: '(416) 555-0100',
			website_uri: 'https://example.com/',
			menu_uri: 'https://example.com/menu'
		});
	});

	it('renders summary actions without fetching details', async () => {
		render(PlaceCard, { place, origin });

		await expect.element(page.getByRole('heading', { name: 'Example Restaurant' })).toBeVisible();
		await expect.element(page.getByText('421 m away')).toBeVisible();
		await expect.element(page.getByText('Open now')).toBeVisible();
		await expect.element(page.getByText('Google Maps rating: 4.6/5')).toBeVisible();
		const directionsLink = page.getByRole('link', { name: 'Get directions' });
		await expect.element(directionsLink).toBeVisible();
		const directionsUrl = new URL(
			(await directionsLink.element() as HTMLAnchorElement).href
		);
		expect(directionsUrl.searchParams.get('origin')).toBe('43.6532,-79.3832');
		expect(directionsUrl.searchParams.get('origin_place_id')).toBe('origin-place-1');
		expect(getPlaceDetails).not.toHaveBeenCalled();
	});

	it('selects the card for the map without fetching details', async () => {
		const onSelect = vi.fn();
		const rendered = render(PlaceCard, { place, origin, selected: false, onSelect });

		await page.getByRole('button', { name: 'Show Example Restaurant on map' }).click();
		expect(onSelect).toHaveBeenCalledTimes(1);
		expect(getPlaceDetails).not.toHaveBeenCalled();

		await rendered.rerender({ place, origin, selected: true, onSelect });
		await expect
			.element(page.getByRole('button', { name: 'Example Restaurant selected on map' }))
			.toHaveAttribute('aria-pressed', 'true');
		expect(getPlaceDetails).not.toHaveBeenCalled();
	});

	it('reveals deterministic match reasons without fetching details', async () => {
		render(PlaceCard, { place, origin });

		await page.getByText('Why this matched').click();
		await expect
			.element(page.getByText('Inside your selected 1 km radius.'))
			.toBeVisible();
		await expect
			.element(
				page.getByText(
					'Kebab availability is not verified—check the menu or call.'
				)
			)
			.toBeVisible();
		await expect.element(page.getByText('Confirmed')).toBeVisible();
		await expect.element(page.getByText('Relevance only')).toBeVisible();
		expect(getPlaceDetails).not.toHaveBeenCalled();
	});

	it('labels missing optional place data without guessing', async () => {
		render(PlaceCard, {
			origin,
			place: {
				...place,
				category: null,
				category_code: null,
				address: null,
				business_status: null,
				open_now: null,
				rating: null
			}
		});

		await expect.element(page.getByText('Category unavailable')).toBeVisible();
		await expect.element(page.getByText('Address unavailable')).toBeVisible();
		await expect
			.element(
				page.getByText(
					'Operational status unconfirmed. Call to confirm before visiting.'
				)
			)
			.toBeVisible();
		expect(getPlaceDetails).not.toHaveBeenCalled();
	});

	it('fetches details once and reuses them when reopened', async () => {
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('Google Maps rating: 4.6 (321)')).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'Call' })).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'example.com', exact: true })).toBeVisible();
		await expect
			.element(page.getByRole('link', { name: 'View menu' }))
			.toHaveAttribute('href', 'https://example.com/menu');
		expect(getPlaceDetails).toHaveBeenCalledTimes(1);

		await page.getByRole('button', { name: 'Hide details' }).click();
		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('Google Maps rating: 4.6 (321)')).toBeVisible();
		expect(getPlaceDetails).toHaveBeenCalledTimes(1);
	});

	it('labels every missing detail field without rendering unusable actions', async () => {
		vi.mocked(getPlaceDetails).mockResolvedValueOnce({
			provider: 'google',
			provider_place_id: 'google-place-1',
			rating: null,
			user_rating_count: null,
			open_now: null,
			opening_hours: [],
			phone_number: null,
			website_uri: null,
			menu_uri: null
		});
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();

		await expect.element(page.getByText('Rating unavailable')).toBeVisible();
		await expect.element(page.getByText('Current open status unavailable')).toBeVisible();
		await expect.element(page.getByText('Hours unavailable')).toBeVisible();
		await expect.element(page.getByText('Phone unavailable')).toBeVisible();
		await expect.element(page.getByText('Website unavailable')).toBeVisible();
		await expect.element(page.getByRole('link', { name: 'View menu' })).not.toBeInTheDocument();
		await expect.element(page.getByRole('link', { name: /^Call/ })).not.toBeInTheDocument();
		await expect.element(page.getByRole('link', { name: /^Open / })).not.toBeInTheDocument();
	});

	it('shows a copyable phone number with separate copy and call actions', async () => {
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();
		await expect.element(page.getByText('(416) 555-0100', { exact: true })).toBeVisible();
		const callLink = page.getByRole('link', { name: 'Call (416) 555-0100' });
		await expect.element(callLink).toHaveAttribute('href', 'tel:4165550100');
		const callElement = (await callLink.element()) as HTMLAnchorElement;
		const phoneActionLabels = Array.from(callElement.parentElement?.children ?? []).map(
			(element) => element.getAttribute('aria-label')
		);
		expect(phoneActionLabels).toEqual(['Call (416) 555-0100', 'Copy (416) 555-0100']);

		await page.getByRole('button', { name: 'Copy (416) 555-0100' }).click();
		expect(copyText).toHaveBeenCalledExactlyOnceWith('(416) 555-0100');
		await expect.element(page.getByText('Phone number copied')).toBeVisible();
	});

	it('keeps the number selectable when automatic copying is unavailable', async () => {
		vi.mocked(copyText).mockRejectedValueOnce(new Error('Clipboard unavailable'));
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();
		await page.getByRole('button', { name: 'Copy (416) 555-0100' }).click();

		await expect.element(page.getByText('(416) 555-0100', { exact: true })).toBeVisible();
		await expect
			.element(page.getByText('Could not copy automatically. Select the number to copy it.'))
			.toBeVisible();
	});

	it('shows a concise website with separate open and copy actions', async () => {
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();
		await expect
			.element(page.getByRole('link', { name: 'example.com', exact: true }))
			.toHaveAttribute('href', 'https://example.com/');
		await expect
			.element(page.getByRole('link', { name: 'Open example.com' }))
			.toHaveAttribute('href', 'https://example.com/');

		await page.getByRole('button', { name: 'Copy example.com' }).click();
		expect(copyText).toHaveBeenCalledExactlyOnceWith('https://example.com/');
		await expect.element(page.getByText('Website link copied')).toBeVisible();
	});

	it('hides an unsafe discovered menu URI', async () => {
		vi.mocked(getPlaceDetails).mockResolvedValueOnce({
			provider: 'google',
			provider_place_id: 'google-place-1',
			rating: null,
			user_rating_count: null,
			open_now: null,
			opening_hours: [],
			phone_number: null,
			website_uri: 'https://example.com/',
			menu_uri: 'javascript:alert(1)'
		});
		render(PlaceCard, { place, origin });

		await page.getByRole('button', { name: 'View details' }).click();

		await expect.element(page.getByRole('link', { name: 'View menu' })).not.toBeInTheDocument();
	});
});
