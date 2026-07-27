import { page } from 'vitest/browser';
import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';

import type { MapMount, MapRenderer } from '$lib/maps/map-renderer';
import type { Place } from '$lib/types';
import MapPanel from './MapPanel.svelte';

const center = { latitude: 43.6532, longitude: -79.3832 };
const place: Place = {
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
	match_reasons: []
};

describe('MapPanel', () => {
	it('reports a missing browser key without invoking the renderer', async () => {
		const renderer: MapRenderer = { mount: vi.fn() };

		render(MapPanel, {
			apiKey: '',
			center,
			radiusMeters: 1_000,
			places: [],
			searchAreaSelected: false,
			selectedPlaceKey: null,
			onPlaceSelect: vi.fn(),
			onLocationSelect: vi.fn(),
			disabled: false,
			renderer
		});

		await expect
			.element(page.getByText('Google Maps is not configured for this browser.'))
			.toBeVisible();
		expect(renderer.mount).not.toHaveBeenCalled();
	});

	it('shows loading and ready states around one map mount', async () => {
		let finishMount: ((mount: MapMount) => void) | undefined;
		const destroy = vi.fn();
		const renderSnapshot = vi.fn();
		const onPlaceSelect = vi.fn();
		const onLocationSelect = vi.fn();
		const renderer: MapRenderer = {
			mount: vi.fn(
				() =>
					new Promise<MapMount>((resolve) => {
						finishMount = resolve;
					})
			)
		};

		const rendered = render(MapPanel, {
			apiKey: 'browser-key',
			center,
			radiusMeters: 1_000,
			places: [],
			searchAreaSelected: false,
			selectedPlaceKey: null,
			onPlaceSelect,
			onLocationSelect,
			disabled: false,
			renderer
		});

		await expect.element(page.getByText('Loading map…')).toBeVisible();
		expect(renderer.mount).toHaveBeenCalledTimes(1);
		expect(renderer.mount).toHaveBeenCalledWith(
			expect.any(HTMLElement),
			expect.objectContaining({
				center,
				onPlaceSelect
			})
		);
		const mountOptions = vi.mocked(renderer.mount).mock.calls[0][1];
		expect(mountOptions.onLocationSelect).toEqual(expect.any(Function));

		finishMount?.({ destroy, render: renderSnapshot });
		await expect.element(page.getByText('Interactive map ready.')).toBeVisible();
		await expect
			.element(page.getByRole('region', { name: 'FoodFind map' }))
			.toBeInTheDocument();
		expect(renderer.mount).toHaveBeenCalledTimes(1);
		expect(renderSnapshot).toHaveBeenLastCalledWith({
			center,
			radiusMeters: 1_000,
			places: [],
			selectedPlaceKey: null,
			locationSelectionEnabled: false,
			searchAreaSelected: false
		});
		await expect
			.element(page.getByText('Choose a location above or select one on the map.'))
			.toBeVisible();

		mountOptions.onLocationSelect({
			latitude: 43.65012349,
			longitude: -79.39098751
		});
		expect(onLocationSelect).not.toHaveBeenCalled();

		await page.getByRole('button', { name: 'Choose location on map' }).click();
		await expect
			.element(page.getByText('Select a point on the map, or cancel.'))
			.toBeVisible();
		expect(renderSnapshot).toHaveBeenLastCalledWith(
			expect.objectContaining({ locationSelectionEnabled: true })
		);

		mountOptions.onLocationSelect({
			latitude: 43.65012349,
			longitude: -79.39098751
		});
		expect(onLocationSelect).toHaveBeenCalledWith({
			latitude: 43.65012349,
			longitude: -79.39098751
		});
		await expect
			.element(page.getByRole('button', { name: 'Choose location on map' }))
			.toHaveAttribute('aria-pressed', 'false');
		expect(renderSnapshot).toHaveBeenLastCalledWith(
			expect.objectContaining({ locationSelectionEnabled: false })
		);

		await rendered.rerender({
			apiKey: 'browser-key',
			center: { latitude: 43.7, longitude: -79.4 },
			radiusMeters: 2_000,
			places: [place],
			searchAreaSelected: true,
			selectedPlaceKey: 'google:place-1',
			onPlaceSelect,
			onLocationSelect,
			disabled: false,
			renderer
		});
		expect(renderer.mount).toHaveBeenCalledTimes(1);
		expect(renderSnapshot).toHaveBeenLastCalledWith({
			center: { latitude: 43.7, longitude: -79.4 },
			radiusMeters: 2_000,
			places: [
				{
					key: 'google:place-1',
					title: 'Test Kitchen',
					coordinates: { latitude: 43.6525, longitude: -79.3817 }
				}
			],
			selectedPlaceKey: 'google:place-1',
			locationSelectionEnabled: false,
			searchAreaSelected: true
		});

		await rendered.unmount();
		expect(destroy).toHaveBeenCalledTimes(1);
	});

	it('shows a safe error when Google Maps cannot load', async () => {
		const renderer: MapRenderer = {
			mount: vi.fn().mockRejectedValue(new Error('provider details'))
		};

		render(MapPanel, {
			apiKey: 'browser-key',
			center,
			radiusMeters: 1_000,
			places: [],
			searchAreaSelected: false,
			selectedPlaceKey: null,
			onPlaceSelect: vi.fn(),
			onLocationSelect: vi.fn(),
			disabled: false,
			renderer
		});

		await expect
			.element(
				page.getByText(
					'The map could not load. Check the Maps JavaScript API key and website restrictions.'
				)
			)
			.toBeVisible();
		expect(renderer.mount).toHaveBeenCalledTimes(1);
	});
});
