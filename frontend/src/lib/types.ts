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

export type PlaceType = 'restaurant' | 'cafe' | 'bar' | 'bakery';
export type Cuisine = 'chinese' | 'italian' | 'persian' | 'thai' | 'indian';
export type CommonFood = 'pizza' | 'burger' | 'steak' | 'ramen' | 'kebab';
export type MinimumRating = 3 | 3.5 | 4 | 4.5;

export interface SearchFilters {
	place_types: PlaceType[];
	cuisines: Cuisine[];
	common_foods: CommonFood[];
	open_now: boolean;
	minimum_rating: MinimumRating | null;
	dine_in: boolean;
	takeout: boolean;
}
export type SearchSort = 'provider_default' | 'distance' | 'rating';

export interface SearchCriteria {
	location: SelectedLocation;
	radius_meters: number;
	filters: SearchFilters;
	sort: SearchSort;
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
	open_now: boolean | null;
	rating: number | null;
	dine_in: boolean | null;
	takeout: boolean | null;
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
