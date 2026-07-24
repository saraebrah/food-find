from datetime import date, datetime, timedelta
from math import asin, cos, degrees, pi, radians, sin
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.domain.place import Coordinates, OpeningPeriod, Place, PlaceDetails
from app.domain.search import (
    EARTH_RADIUS_METERS,
    CommonFood,
    Cuisine,
    PlaceType,
    SearchFilters,
    SearchSort,
)
from app.domain.search_intent import (
    AvailabilityWindow,
    DescriptiveRequirement,
)
from app.ports.place_provider import PlaceProvider, PlaceProviderError


GOOGLE_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_FIELD_MASK = ",".join(
    (
        "places.id",
        "places.displayName",
        "places.primaryType",
        "places.types",
        "places.primaryTypeDisplayName",
        "places.formattedAddress",
        "places.location",
        "places.businessStatus",
    )
)
GOOGLE_CURRENT_OPENING_HOURS_FIELD = "places.currentOpeningHours"
GOOGLE_TIME_ZONE_FIELD = "places.timeZone"
GOOGLE_RATING_FIELD = "places.rating"
GOOGLE_DINE_IN_FIELD = "places.dineIn"
GOOGLE_TAKEOUT_FIELD = "places.takeout"
GOOGLE_PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
GOOGLE_DETAILS_FIELD_MASK = ",".join(
    (
        "id",
        "rating",
        "userRatingCount",
        "currentOpeningHours",
        "regularOpeningHours",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "websiteUri",
    )
)


class GoogleLocalizedText(BaseModel):
    text: str


class GoogleLocation(BaseModel):
    latitude: float
    longitude: float


class GoogleDate(BaseModel):
    year: int
    month: int
    day: int


class GoogleOpeningPoint(BaseModel):
    date: GoogleDate | None = None
    day: int | None = Field(default=None, ge=0, le=6)
    hour: int = Field(default=0, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)


class GoogleOpeningPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    opens_at: GoogleOpeningPoint = Field(alias="open")
    closes_at: GoogleOpeningPoint | None = Field(default=None, alias="close")


class GoogleOpeningHours(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    open_now: bool | None = Field(default=None, alias="openNow")
    weekday_descriptions: list[str] = Field(
        default_factory=list,
        alias="weekdayDescriptions",
    )
    periods: list[GoogleOpeningPeriod] = Field(default_factory=list)


class GoogleTimeZone(BaseModel):
    id: str


class GooglePlaceRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    display_name: GoogleLocalizedText = Field(alias="displayName")
    primary_type: str | None = Field(default=None, alias="primaryType")
    types: list[str] = Field(default_factory=list)
    primary_type_display_name: GoogleLocalizedText | None = Field(
        default=None, alias="primaryTypeDisplayName"
    )
    formatted_address: str | None = Field(default=None, alias="formattedAddress")
    location: GoogleLocation
    business_status: str | None = Field(default=None, alias="businessStatus")
    current_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="currentOpeningHours",
    )
    rating: float | None = None
    dine_in: bool | None = Field(default=None, alias="dineIn")
    takeout: bool | None = None
    time_zone: GoogleTimeZone | None = Field(default=None, alias="timeZone")


class GoogleTextSearchResponse(BaseModel):
    places: list[GooglePlaceRecord] = Field(default_factory=list)


class GooglePlaceDetailsRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    rating: float | None = None
    user_rating_count: int | None = Field(default=None, alias="userRatingCount")
    current_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="currentOpeningHours",
    )
    regular_opening_hours: GoogleOpeningHours | None = Field(
        default=None,
        alias="regularOpeningHours",
    )
    national_phone_number: str | None = Field(
        default=None,
        alias="nationalPhoneNumber",
    )
    international_phone_number: str | None = Field(
        default=None,
        alias="internationalPhoneNumber",
    )
    website_uri: str | None = Field(default=None, alias="websiteUri")


GOOGLE_BUSINESS_STATUSES = {
    "OPERATIONAL": "operational",
    "CLOSED_TEMPORARILY": "temporarily_closed",
    "CLOSED_PERMANENTLY": "permanently_closed",
}
GOOGLE_PLACE_TYPES = {
    PlaceType.RESTAURANT: "restaurant",
    PlaceType.CAFE: "cafe",
    PlaceType.BAR: "bar",
    PlaceType.BAKERY: "bakery",
}
GOOGLE_PLACE_TYPE_QUERY_TEXT = {
    PlaceType.RESTAURANT: "restaurants",
    PlaceType.CAFE: "cafes",
    PlaceType.BAR: "bars",
    PlaceType.BAKERY: "bakeries",
}
GOOGLE_CUISINE_QUERY_TEXT = {
    Cuisine.CHINESE: "Chinese",
    Cuisine.ITALIAN: "Italian",
    Cuisine.PERSIAN: "Persian",
    Cuisine.THAI: "Thai",
    Cuisine.INDIAN: "Indian",
}
GOOGLE_COMMON_FOOD_QUERY_TEXT = {
    CommonFood.PIZZA: "pizza",
    CommonFood.BURGER: "burgers",
    CommonFood.STEAK: "steak",
    CommonFood.RAMEN: "ramen",
    CommonFood.KEBAB: "kebab",
}


class GooglePlacesGateway(PlaceProvider):
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        if not api_key.strip():
            raise ValueError("Google Places API key must not be empty")

        self._api_key = api_key
        self._http_client = http_client

    @property
    def provider_name(self) -> str:
        return "google"

    @staticmethod
    def _search_field_mask(
        *,
        filters: SearchFilters,
        sort: SearchSort,
        availability_window: AvailabilityWindow | None = None,
    ) -> str:
        conditional_fields: list[str] = []
        if filters.open_now or availability_window is not None:
            conditional_fields.append(GOOGLE_CURRENT_OPENING_HOURS_FIELD)
        if availability_window is not None:
            conditional_fields.append(GOOGLE_TIME_ZONE_FIELD)
        if filters.minimum_rating is not None or sort is SearchSort.RATING:
            conditional_fields.append(GOOGLE_RATING_FIELD)
        if filters.dine_in:
            conditional_fields.append(GOOGLE_DINE_IN_FIELD)
        if filters.takeout:
            conditional_fields.append(GOOGLE_TAKEOUT_FIELD)
        return ",".join((GOOGLE_FIELD_MASK, *conditional_fields))

    @staticmethod
    def _build_text_query(
        *,
        filters: SearchFilters,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
    ) -> str:
        place_types = " or ".join(
            GOOGLE_PLACE_TYPE_QUERY_TEXT[place_type]
            for place_type in filters.place_types
        )
        parts = [place_types]
        if filters.cuisines:
            cuisines = " or ".join(
                GOOGLE_CUISINE_QUERY_TEXT[cuisine]
                for cuisine in filters.cuisines
            )
            parts.append(f"with {cuisines} cuisine")
        if filters.common_foods:
            foods = " or ".join(
                GOOGLE_COMMON_FOOD_QUERY_TEXT[food]
                for food in filters.common_foods
            )
            parts.append(f"serving {foods}")
        parts.extend(
            requirement.text for requirement in descriptive_requirements
        )
        return " ".join(parts)

    @staticmethod
    def _location_parameter(
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
    ) -> dict[str, object]:
        angular_radius = radius_meters / EARTH_RADIUS_METERS
        latitude_radians = radians(latitude)
        longitude_radians = radians(longitude)
        minimum_latitude = max(-pi / 2, latitude_radians - angular_radius)
        maximum_latitude = min(pi / 2, latitude_radians + angular_radius)

        if minimum_latitude <= -pi / 2 or maximum_latitude >= pi / 2:
            return {
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": float(radius_meters),
                    }
                }
            }

        longitude_delta = asin(
            min(1.0, sin(angular_radius) / cos(latitude_radians))
        )
        minimum_longitude = longitude_radians - longitude_delta
        maximum_longitude = longitude_radians + longitude_delta
        if minimum_longitude < -pi or maximum_longitude > pi:
            return {
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": float(radius_meters),
                    }
                }
            }

        return {
            "locationRestriction": {
                "rectangle": {
                    "low": {
                        "latitude": degrees(minimum_latitude),
                        "longitude": degrees(minimum_longitude),
                    },
                    "high": {
                        "latitude": degrees(maximum_latitude),
                        "longitude": degrees(maximum_longitude),
                    },
                }
            }
        }

    async def search_nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_meters: float,
        filters: SearchFilters,
        sort: SearchSort,
        descriptive_requirements: tuple[DescriptiveRequirement, ...] = (),
        availability_window: AvailabilityWindow | None = None,
    ) -> list[Place]:
        if not filters.place_types:
            raise ValueError("At least one place type is required")
        if not 0 < radius_meters <= 50_000:
            raise ValueError("Radius must be greater than zero and at most 50,000 metres")

        request_body: dict[str, object] = {
            "textQuery": self._build_text_query(
                filters=filters,
                descriptive_requirements=descriptive_requirements,
            ),
            "pageSize": 20,
            **self._location_parameter(
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
            ),
        }
        if len(filters.place_types) == 1:
            request_body["includedType"] = GOOGLE_PLACE_TYPES[
                filters.place_types[0]
            ]
            request_body["strictTypeFiltering"] = True
        if filters.open_now:
            request_body["openNow"] = True
        if filters.minimum_rating is not None:
            request_body["minRating"] = filters.minimum_rating.value
        if sort is SearchSort.DISTANCE:
            request_body["rankPreference"] = "DISTANCE"

        selected_google_types = frozenset(
            GOOGLE_PLACE_TYPES[place_type] for place_type in filters.place_types
        )

        try:
            response = await self._http_client.post(
                GOOGLE_TEXT_SEARCH_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": self._search_field_mask(
                        filters=filters,
                        sort=sort,
                        availability_window=availability_window,
                    ),
                },
                json=request_body,
            )
            response.raise_for_status()
            google_response = GoogleTextSearchResponse.model_validate(
                response.json()
            )
        except (httpx.HTTPError, ValueError) as error:
            raise PlaceProviderError("Google Places search failed") from error

        return [
            self._to_place(
                place,
                availability_window=availability_window,
            )
            for place in google_response.places
            if not place.types or selected_google_types.intersection(place.types)
        ]

    async def get_details(self, *, provider_place_id: str) -> PlaceDetails:
        if not provider_place_id.strip():
            raise ValueError("Google place ID must not be empty")

        place_id = quote(provider_place_id, safe="")
        try:
            response = await self._http_client.get(
                GOOGLE_PLACE_DETAILS_URL.format(place_id=place_id),
                headers={
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": GOOGLE_DETAILS_FIELD_MASK,
                },
            )
            response.raise_for_status()
            google_details = GooglePlaceDetailsRecord.model_validate(response.json())
            if google_details.id != provider_place_id:
                raise ValueError("Google Places returned a different place ID")
        except (httpx.HTTPError, ValueError) as error:
            raise PlaceProviderError("Google Place Details request failed") from error

        current_hours = google_details.current_opening_hours
        regular_hours = google_details.regular_opening_hours
        opening_hours = (
            current_hours.weekday_descriptions
            if current_hours and current_hours.weekday_descriptions
            else regular_hours.weekday_descriptions
            if regular_hours
            else []
        )
        open_now = (
            current_hours.open_now
            if current_hours and current_hours.open_now is not None
            else regular_hours.open_now
            if regular_hours
            else None
        )

        return PlaceDetails(
            provider=self.provider_name,
            provider_place_id=google_details.id,
            rating=google_details.rating,
            user_rating_count=google_details.user_rating_count,
            open_now=open_now,
            opening_hours=tuple(opening_hours),
            phone_number=(
                google_details.national_phone_number
                or google_details.international_phone_number
            ),
            website_uri=google_details.website_uri,
        )

    @classmethod
    def _to_place(
        cls,
        place: GooglePlaceRecord,
        *,
        availability_window: AvailabilityWindow | None = None,
    ) -> Place:
        return Place(
            provider="google",
            provider_place_id=place.id,
            name=place.display_name.text,
            category=(
                place.primary_type_display_name.text
                if place.primary_type_display_name
                else None
            ),
            category_code=place.primary_type,
            address=place.formatted_address,
            coordinates=Coordinates(
                latitude=place.location.latitude,
                longitude=place.location.longitude,
            ),
            business_status=GOOGLE_BUSINESS_STATUSES.get(place.business_status),
            open_now=(
                place.current_opening_hours.open_now
                if place.current_opening_hours
                else None
            ),
            rating=place.rating,
            dine_in=place.dine_in,
            takeout=place.takeout,
            opening_periods=cls._to_opening_periods(
                place=place,
                availability_window=availability_window,
            ),
        )

    @classmethod
    def _to_opening_periods(
        cls,
        *,
        place: GooglePlaceRecord,
        availability_window: AvailabilityWindow | None,
    ) -> tuple[OpeningPeriod, ...] | None:
        if availability_window is None:
            return None
        if place.current_opening_hours is None or place.time_zone is None:
            return None
        try:
            time_zone = ZoneInfo(place.time_zone.id)
        except (ValueError, ZoneInfoNotFoundError):
            return None

        periods: list[OpeningPeriod] = []
        for google_period in place.current_opening_hours.periods:
            periods.extend(
                cls._to_opening_period_occurrences(
                    google_period=google_period,
                    time_zone=time_zone,
                    availability_window=availability_window,
                )
            )
        return tuple(periods)

    @classmethod
    def _to_opening_period_occurrences(
        cls,
        *,
        google_period: GoogleOpeningPeriod,
        time_zone: ZoneInfo,
        availability_window: AvailabilityWindow,
    ) -> list[OpeningPeriod]:
        dated_start = cls._dated_opening_point(
            point=google_period.opens_at,
            time_zone=time_zone,
        )
        dated_end = (
            cls._dated_opening_point(
                point=google_period.closes_at,
                time_zone=time_zone,
            )
            if google_period.closes_at is not None
            else None
        )
        if dated_start is not None:
            if dated_end is not None and dated_end <= dated_start:
                return []
            return [
                OpeningPeriod(
                    starts_at=dated_start,
                    ends_at=dated_end,
                )
            ]

        if google_period.opens_at.day is None:
            return []

        local_reference = availability_window.starts_at.astimezone(time_zone)
        sunday = local_reference.date() - timedelta(
            days=(local_reference.weekday() + 1) % 7
        )
        occurrences: list[OpeningPeriod] = []
        for week_offset in (-7, 0, 7):
            starts_at = cls._weekly_opening_point(
                point=google_period.opens_at,
                sunday=sunday + timedelta(days=week_offset),
                time_zone=time_zone,
            )
            if starts_at is None:
                continue
            ends_at = (
                cls._weekly_opening_point(
                    point=google_period.closes_at,
                    sunday=sunday + timedelta(days=week_offset),
                    time_zone=time_zone,
                )
                if google_period.closes_at is not None
                else None
            )
            if ends_at is not None and ends_at <= starts_at:
                ends_at += timedelta(days=7)
            occurrences.append(
                OpeningPeriod(starts_at=starts_at, ends_at=ends_at)
            )
        return occurrences

    @staticmethod
    def _dated_opening_point(
        *,
        point: GoogleOpeningPoint | None,
        time_zone: ZoneInfo,
    ) -> datetime | None:
        if point is None or point.date is None:
            return None
        try:
            return datetime(
                point.date.year,
                point.date.month,
                point.date.day,
                point.hour,
                point.minute,
                tzinfo=time_zone,
            )
        except ValueError:
            return None

    @staticmethod
    def _weekly_opening_point(
        *,
        point: GoogleOpeningPoint | None,
        sunday: date,
        time_zone: ZoneInfo,
    ) -> datetime | None:
        if point is None or point.day is None:
            return None
        point_date = sunday + timedelta(days=point.day)
        return datetime(
            point_date.year,
            point_date.month,
            point_date.day,
            point.hour,
            point.minute,
            tzinfo=time_zone,
        )
