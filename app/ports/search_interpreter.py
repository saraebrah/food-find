from typing import Protocol

from app.domain.search import SearchCriteria
from app.domain.search_interpretation import SearchInterpretationContext
from app.domain.search_intent import SearchIntent


class SearchInterpreterError(RuntimeError):
    """A search interpreter could not return a valid intent."""


class SearchInterpreter(Protocol):
    async def interpret(
        self,
        *,
        query: str,
        search_criteria: SearchCriteria,
        context: SearchInterpretationContext,
    ) -> SearchIntent: ...
