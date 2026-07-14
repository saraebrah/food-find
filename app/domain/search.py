from dataclasses import dataclass

from app.domain.location import SelectedLocation


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchCriteria:
    location: SelectedLocation
    radius_meters: float
