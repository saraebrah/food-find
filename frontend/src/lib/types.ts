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

export type DescriptiveRequirementKind = 'dish' | 'dietary' | 'atmosphere' | 'other';

export interface DescriptiveRequirement {
	text: string;
	kind: DescriptiveRequirementKind;
}

export interface AvailabilityWindow {
	starts_at: string;
	ends_at: string;
}

export interface PlaceSearchRequest extends SearchCriteria {
	descriptive_requirements: DescriptiveRequirement[];
	availability_window: AvailabilityWindow | null;
}

export interface ResolvedAssumption {
	source_text: string;
	interpretation: string;
}

export interface UnsupportedCriterion {
	text: string;
	reason: string;
}

export interface SearchInterpretation {
	search_criteria: SearchCriteria;
	descriptive_requirements: DescriptiveRequirement[];
	availability_window: AvailabilityWindow | null;
	assumptions: ResolvedAssumption[];
	unsupported_criteria: UnsupportedCriterion[];
	timezone: string;
}

export type MatchReasonKind = 'confirmed' | 'relevance';

export interface MatchReason {
	kind: MatchReasonKind;
	text: string;
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
	match_reasons: MatchReason[];
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
