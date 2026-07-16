from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.domain.location import SelectedLocation
from app.domain.place import Coordinates


EARTH_RADIUS_METERS = 6_371_000


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchCriteria:
    location: SelectedLocation
    radius_meters: float


def straight_line_distance_meters(
    origin: Coordinates,
    destination: Coordinates,
) -> int:
    latitude_delta = radians(destination.latitude - origin.latitude)
    longitude_delta = radians(destination.longitude - origin.longitude)
    origin_latitude = radians(origin.latitude)
    destination_latitude = radians(destination.latitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(origin_latitude)
        * cos(destination_latitude)
        * sin(longitude_delta / 2) ** 2
    )
    arc = 2 * asin(sqrt(min(1, haversine)))
    return round(EARTH_RADIUS_METERS * arc)
