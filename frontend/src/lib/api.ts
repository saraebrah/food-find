import type {
	LocationSuggestion,
	Place,
	PlaceDetails,
	SearchCriteria,
	SelectedLocation
} from './types';

export class ApiError extends Error {
	constructor(public readonly status: number) {
		super(`FoodFind API request failed with status ${status}`);
		this.name = 'ApiError';
	}
}

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
	const response = await fetch(path, {
		method: 'POST',
		headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
		signal
	});
	if (!response.ok) throw new ApiError(response.status);
	return (await response.json()) as T;
}

export function searchPlaces(criteria: SearchCriteria, signal?: AbortSignal): Promise<Place[]> {
	return postJson<Place[]>('/api/places/search', criteria, signal);
}

export function autocompleteLocations(
	query: string,
	sessionToken: string,
	signal?: AbortSignal
): Promise<LocationSuggestion[]> {
	return postJson<LocationSuggestion[]>(
		'/api/locations/autocomplete',
		{ query, session_token: sessionToken },
		signal
	);
}

export function resolveLocation(
	suggestion: LocationSuggestion,
	sessionToken: string,
	signal?: AbortSignal
): Promise<SelectedLocation> {
	return postJson<SelectedLocation>(
		'/api/locations/resolve',
		{
			provider_place_id: suggestion.provider_place_id,
			label: suggestion.label,
			session_token: sessionToken
		},
		signal
	);
}

export function getPlaceDetails(
	provider: string,
	providerPlaceId: string,
	signal?: AbortSignal
): Promise<PlaceDetails> {
	return postJson<PlaceDetails>(
		'/api/places/details',
		{ provider, provider_place_id: providerPlaceId },
		signal
	);
}
