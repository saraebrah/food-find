from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.domain.search import SearchCriteria


def _normalized_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


class DescriptiveRequirementKind(str, Enum):
    """Kinds of text-relevance criteria that are not verified facts."""

    DISH = "dish"
    DIETARY = "dietary"
    ATMOSPHERE = "atmosphere"
    OTHER = "other"


@dataclass(frozen=True, slots=True, kw_only=True)
class DescriptiveRequirement:
    """A useful search requirement without a dedicated structured filter."""

    text: str
    kind: DescriptiveRequirementKind

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            _normalized_text(self.text, field_name="Requirement text"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedAssumption:
    """A phrase and the interpretation FoodFind must show to the user."""

    source_text: str
    interpretation: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_text",
            _normalized_text(self.source_text, field_name="Assumption source"),
        )
        object.__setattr__(
            self,
            "interpretation",
            _normalized_text(
                self.interpretation,
                field_name="Assumption interpretation",
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class UnsupportedCriterion:
    """A requested criterion FoodFind cannot apply safely."""

    text: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            _normalized_text(self.text, field_name="Unsupported criterion"),
        )
        object.__setattr__(
            self,
            "reason",
            _normalized_text(self.reason, field_name="Unsupported reason"),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class AvailabilityWindow:
    """A concrete local time window resolved from language such as tonight."""

    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if self.starts_at.utcoffset() is None or self.ends_at.utcoffset() is None:
            raise ValueError("Availability window datetimes must be timezone-aware")
        if self.ends_at <= self.starts_at:
            raise ValueError("Availability window must end after it starts")


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchIntent:
    """Validated user meaning plus the currently executable search criteria."""

    search_criteria: SearchCriteria
    descriptive_requirements: tuple[DescriptiveRequirement, ...] = ()
    availability_window: AvailabilityWindow | None = None
    assumptions: tuple[ResolvedAssumption, ...] = ()
    unsupported_criteria: tuple[UnsupportedCriterion, ...] = ()
