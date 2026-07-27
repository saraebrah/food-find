import type { Coordinates } from '$lib/types';

export interface MapPlace {
	key: string;
	title: string;
	coordinates: Coordinates;
}

export interface MapSnapshot {
	center: Coordinates;
	radiusMeters: number;
	places: MapPlace[];
	selectedPlaceKey: string | null;
	locationSelectionEnabled: boolean;
	searchAreaSelected: boolean;
}

export interface MapMount {
	render(snapshot: MapSnapshot): void;
	destroy(): void;
}

export interface MapMountOptions {
	center: Coordinates;
	onPlaceSelect(placeKey: string): void;
	onLocationSelect(coordinates: Coordinates): void;
}

export interface MapRenderer {
	mount(element: HTMLElement, options: MapMountOptions): Promise<MapMount>;
}
