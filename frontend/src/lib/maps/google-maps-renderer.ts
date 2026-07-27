import { importLibrary, setOptions } from '@googlemaps/js-api-loader';

import type {
	MapMount,
	MapMountOptions,
	MapRenderer,
	MapSnapshot
} from './map-renderer';

export const DEVELOPMENT_MAP_ID = 'DEMO_MAP_ID';

let configuredApiKey: string | null = null;
let mapsLibraryPromise: Promise<google.maps.MapsLibrary> | null = null;
let markerLibraryPromise: Promise<google.maps.MarkerLibrary> | null = null;

function loadLibraries(
	apiKey: string
): Promise<[google.maps.MapsLibrary, google.maps.MarkerLibrary]> {
	if (configuredApiKey === null) {
		setOptions({
			authReferrerPolicy: 'origin',
			key: apiKey,
			mapIds: [DEVELOPMENT_MAP_ID],
			v: 'weekly'
		});
		configuredApiKey = apiKey;
	} else if (configuredApiKey !== apiKey) {
		throw new Error('Google Maps has already been configured with a different API key.');
	}

	mapsLibraryPromise ??= importLibrary('maps') as Promise<google.maps.MapsLibrary>;
	markerLibraryPromise ??= importLibrary('marker') as Promise<google.maps.MarkerLibrary>;
	return Promise.all([mapsLibraryPromise, markerLibraryPromise]);
}

export class GoogleMapsRenderer implements MapRenderer {
	private readonly apiKey: string;

	constructor(apiKey: string) {
		this.apiKey = apiKey.trim();
		if (!this.apiKey) {
			throw new Error('Google Maps API key is missing.');
		}
	}

	async mount(element: HTMLElement, options: MapMountOptions): Promise<MapMount> {
		const [{ Circle, Map }, { AdvancedMarkerElement, PinElement }] =
			await loadLibraries(this.apiKey);
		const map = new Map(element, {
			center: {
				lat: options.center.latitude,
				lng: options.center.longitude
			},
			mapId: DEVELOPMENT_MAP_ID,
			zoom: 13
		});
		const radiusCircle = new Circle({
			center: {
				lat: options.center.latitude,
				lng: options.center.longitude
			},
			clickable: false,
			fillColor: '#596b3d',
			fillOpacity: 0.1,
			map: null,
			radius: 0,
			strokeColor: '#3f562b',
			strokeOpacity: 0.8,
			strokeWeight: 2
		});
		let centerMarker: google.maps.marker.AdvancedMarkerElement | null = null;
		let placeMarkers: google.maps.marker.AdvancedMarkerElement[] = [];
		let geometrySignature: string | null = null;
		let destroyed = false;
		const mapClickListener = map.addListener(
			'click',
			(event: google.maps.MapMouseEvent) => {
				if (!event.latLng) return;
				options.onLocationSelect({
					latitude: event.latLng.lat(),
					longitude: event.latLng.lng()
				});
			}
		);

		function render(snapshot: MapSnapshot) {
			if (destroyed) return;
			map.setOptions({
				draggableCursor: snapshot.locationSelectionEnabled
					? 'crosshair'
					: null
			});

			const nextGeometrySignature = JSON.stringify({
				center: snapshot.center,
				radiusMeters: snapshot.radiusMeters,
				searchAreaSelected: snapshot.searchAreaSelected,
				places: snapshot.places.map(({ key, coordinates }) => ({
					key,
					coordinates
				}))
			});
			const geometryChanged = nextGeometrySignature !== geometrySignature;
			const mapCenter = {
				lat: snapshot.center.latitude,
				lng: snapshot.center.longitude
			};
			if (snapshot.searchAreaSelected) {
				radiusCircle.setCenter(mapCenter);
				radiusCircle.setRadius(snapshot.radiusMeters);
				radiusCircle.setMap(map);

				if (centerMarker === null) {
					centerMarker = new AdvancedMarkerElement({
						gmpClickable: false,
						map,
						position: mapCenter,
						title: 'Search centre',
						zIndex: 1_000
					});
				} else {
					centerMarker.map = map;
					centerMarker.position = mapCenter;
				}
			} else {
				radiusCircle.setMap(null);
				if (centerMarker) centerMarker.map = null;
			}

			for (const marker of placeMarkers) marker.map = null;
			placeMarkers = snapshot.places.map(
				(place) => {
					const selected = place.key === snapshot.selectedPlaceKey;
					const marker = new AdvancedMarkerElement({
						content: new PinElement({
							background: selected ? '#2f421f' : '#596b3d',
							borderColor: selected ? '#17220f' : '#30451f',
							glyphColor: '#ffffff',
							scale: selected ? 1.25 : 1
						}),
						gmpClickable: true,
						map,
						position: {
							lat: place.coordinates.latitude,
							lng: place.coordinates.longitude
						},
						title: place.title,
						zIndex: selected ? 2_000 : undefined
					});
					marker.addEventListener('gmp-click', () =>
						options.onPlaceSelect(place.key)
					);
					return marker;
				}
			);

			const bounds = snapshot.searchAreaSelected
				? radiusCircle.getBounds()
				: null;
			if (geometryChanged && snapshot.searchAreaSelected && bounds) {
				for (const place of snapshot.places) {
					bounds.extend({
						lat: place.coordinates.latitude,
						lng: place.coordinates.longitude
					});
				}
				map.fitBounds(bounds, 48);
			} else if (geometryChanged) {
				map.setCenter(mapCenter);
				map.setZoom(13);
			}
			geometrySignature = nextGeometrySignature;
		}

		return {
			render,
			destroy() {
				destroyed = true;
				mapClickListener.remove();
				if (centerMarker) centerMarker.map = null;
				for (const marker of placeMarkers) marker.map = null;
				placeMarkers = [];
				radiusCircle.setMap(null);
				map.unbindAll();
				element.replaceChildren();
			}
		};
	}
}

export function createGoogleMapsRenderer(apiKey: string): MapRenderer {
	return new GoogleMapsRenderer(apiKey);
}
