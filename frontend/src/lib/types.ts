export type BusinessStatus = 'operational' | 'temporarily_closed' | 'permanently_closed';

export interface Coordinates {
	latitude: number;
	longitude: number;
}

export interface SelectedLocation extends Coordinates {
	label: string;
	provider?: string | null;
	provider_place_id?: string | null;
}

export interface LocationSuggestion {
	provider: string;
	provider_place_id: string;
	label: string;
}

export interface SearchCriteria {
	location: SelectedLocation;
	radius_meters: number;
}

export interface Place {
	provider: string;
	provider_place_id: string;
	name: string;
	category: string | null;
	category_code: string | null;
	address: string | null;
	coordinates: Coordinates;
	business_status: BusinessStatus | null;
	distance_meters: number | null;
}

export interface PlaceDetails {
	provider: string;
	provider_place_id: string;
	rating: number | null;
	user_rating_count: number | null;
	open_now: boolean | null;
	opening_hours: string[];
	phone_number: string | null;
	website_uri: string | null;
}
