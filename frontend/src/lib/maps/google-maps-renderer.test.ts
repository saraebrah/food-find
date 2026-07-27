import { beforeEach, describe, expect, it, vi } from 'vitest';

const loader = vi.hoisted(() => ({
	importLibrary: vi.fn(),
	setOptions: vi.fn()
}));

vi.mock('@googlemaps/js-api-loader', () => loader);

import { GoogleMapsRenderer } from './google-maps-renderer';

describe('GoogleMapsRenderer', () => {
	beforeEach(() => {
		loader.importLibrary.mockReset();
		loader.setOptions.mockReset();
	});

	it('rejects an empty browser API key', () => {
		expect(() => new GoogleMapsRenderer('  ')).toThrow('Google Maps API key is missing.');
	});

	it('loads Maps once and creates independent map mounts', async () => {
		const fitBounds = vi.fn();
		const constructedMaps: Array<{
			element: HTMLElement;
			options: google.maps.MapOptions;
			addListener: ReturnType<typeof vi.fn>;
			setOptions: ReturnType<typeof vi.fn>;
			unbindAll: ReturnType<typeof vi.fn>;
		}> = [];
		class FakeMap {
			unbindAll = vi.fn();
			fitBounds = fitBounds;
			setCenter = vi.fn();
			setOptions = vi.fn();
			setZoom = vi.fn();
			listeners = new Map<string, (event: google.maps.MapMouseEvent) => void>();
			listenerRemovals: ReturnType<typeof vi.fn>[] = [];
			addListener = vi.fn(
				(eventName: string, handler: (event: google.maps.MapMouseEvent) => void) => {
					this.listeners.set(eventName, handler);
					const remove = vi.fn(() => this.listeners.delete(eventName));
					this.listenerRemovals.push(remove);
					return { remove };
				}
			);

			constructor(
				public element: HTMLElement,
				public options: google.maps.MapOptions
			) {
				constructedMaps.push(this);
			}

			dispatch(eventName: string, event: google.maps.MapMouseEvent) {
				this.listeners.get(eventName)?.(event);
			}
		}
		const bounds = { extend: vi.fn() };
		const circles: FakeCircle[] = [];
		class FakeCircle {
			setCenter = vi.fn();
			setMap = vi.fn();
			setRadius = vi.fn();
			getBounds = vi.fn(() => bounds);

			constructor(public options: google.maps.CircleOptions) {
				circles.push(this);
			}
		}
		const markers: FakeAdvancedMarker[] = [];
		class FakeAdvancedMarker {
			map: google.maps.Map | null | undefined;
			listeners = new Map<string, EventListener>();

			constructor(public options: google.maps.marker.AdvancedMarkerElementOptions) {
				this.map = options.map;
				markers.push(this);
			}

			addEventListener(type: string, listener: EventListener) {
				this.listeners.set(type, listener);
			}

			dispatch(type: string) {
				this.listeners.get(type)?.(new Event(type));
			}
		}
		const pins: FakePinElement[] = [];
		class FakePinElement {
			constructor(public options: google.maps.marker.PinElementOptions) {
				pins.push(this);
			}
		}
		loader.importLibrary.mockImplementation((library: string) =>
			Promise.resolve(
				library === 'maps'
					? { Circle: FakeCircle, Map: FakeMap }
					: {
							AdvancedMarkerElement: FakeAdvancedMarker,
							PinElement: FakePinElement
						}
			)
		);

		const renderer = new GoogleMapsRenderer('browser-key');
		const onPlaceSelect = vi.fn();
		const onLocationSelect = vi.fn();
		const firstElement = {
			replaceChildren: vi.fn()
		} as unknown as HTMLElement;
		const secondElement = {
			replaceChildren: vi.fn()
		} as unknown as HTMLElement;
		const firstMount = await renderer.mount(firstElement, {
			center: { latitude: 43.6532, longitude: -79.3832 },
			onPlaceSelect,
			onLocationSelect
		});
		await renderer.mount(secondElement, {
			center: { latitude: 43.6454, longitude: -79.3805 },
			onPlaceSelect: vi.fn(),
			onLocationSelect: vi.fn()
		});

		expect(loader.setOptions).toHaveBeenCalledTimes(1);
		expect(loader.setOptions).toHaveBeenCalledWith({
			authReferrerPolicy: 'origin',
			key: 'browser-key',
			mapIds: ['DEMO_MAP_ID'],
			v: 'weekly'
		});
		expect(loader.importLibrary).toHaveBeenCalledTimes(2);
		expect(loader.importLibrary).toHaveBeenCalledWith('maps');
		expect(loader.importLibrary).toHaveBeenCalledWith('marker');
		expect(constructedMaps).toHaveLength(2);
		expect(constructedMaps[0].options).toEqual({
			center: { lat: 43.6532, lng: -79.3832 },
			mapId: 'DEMO_MAP_ID',
			zoom: 13
		});

		firstMount.render({
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
			locationSelectionEnabled: false,
			searchAreaSelected: true
		});

		expect(circles).toHaveLength(2);
		expect(circles[0].setCenter).toHaveBeenCalledWith({
			lat: 43.6532,
			lng: -79.3832
		});
		expect(circles[0].setRadius).toHaveBeenCalledWith(1_000);
		expect(markers).toHaveLength(2);
		expect(markers[0].options.title).toBe('Search centre');
		expect(markers[1].options.title).toBe('Test Kitchen');
		expect(markers[1].options.gmpClickable).toBe(true);
		markers[1].dispatch('gmp-click');
		expect(onPlaceSelect).toHaveBeenCalledWith('google:place-1');
		expect(bounds.extend).toHaveBeenCalledWith({
			lat: 43.6525,
			lng: -79.3817
		});
		expect(fitBounds).toHaveBeenCalledWith(bounds, 48);
		expect(pins.at(-1)?.options.scale).toBe(1);
		(constructedMaps[0] as FakeMap).dispatch('click', {
			latLng: {
				lat: () => 43.65012349,
				lng: () => -79.39098751
			}
		} as google.maps.MapMouseEvent);
		expect(onLocationSelect).toHaveBeenCalledWith({
			latitude: 43.65012349,
			longitude: -79.39098751
		});
		(constructedMaps[0] as FakeMap).dispatch(
			'center_changed',
			{} as google.maps.MapMouseEvent
		);
		(constructedMaps[0] as FakeMap).dispatch(
			'zoom_changed',
			{} as google.maps.MapMouseEvent
		);
		expect(onLocationSelect).toHaveBeenCalledTimes(1);
		expect(constructedMaps[0].addListener).toHaveBeenCalledTimes(1);
		expect(constructedMaps[0].addListener).toHaveBeenCalledWith(
			'click',
			expect.any(Function)
		);

		firstMount.render({
			center: { latitude: 43.6532, longitude: -79.3832 },
			radiusMeters: 1_000,
			places: [
				{
					key: 'google:place-1',
					title: 'Test Kitchen',
					coordinates: { latitude: 43.6525, longitude: -79.3817 }
				}
			],
			selectedPlaceKey: 'google:place-1',
			locationSelectionEnabled: true,
			searchAreaSelected: true
		});
		expect(markers.at(-1)?.options.title).toBe('Test Kitchen');
		expect(pins.at(-1)?.options.scale).toBe(1.25);
		expect(fitBounds).toHaveBeenCalledTimes(1);
		expect(constructedMaps[0].setOptions).toHaveBeenLastCalledWith({
			draggableCursor: 'crosshair'
		});

		firstMount.render({
			center: { latitude: 43.6532, longitude: -79.3832 },
			radiusMeters: 1_000,
			places: [],
			selectedPlaceKey: null,
			locationSelectionEnabled: false,
			searchAreaSelected: false
		});
		expect(circles[0].setMap).toHaveBeenLastCalledWith(null);
		expect(markers[0].map).toBeNull();

		firstMount.destroy();
		expect(circles[0].setMap).toHaveBeenCalledWith(null);
		expect(markers.every((marker) => marker.map === null)).toBe(true);
		expect(constructedMaps[0].unbindAll).toHaveBeenCalledTimes(1);
		expect((constructedMaps[0] as FakeMap).listenerRemovals[0]).toHaveBeenCalledTimes(1);
		expect(firstElement.replaceChildren).toHaveBeenCalledTimes(1);
	});
});
