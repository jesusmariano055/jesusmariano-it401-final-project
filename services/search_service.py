from dataclasses import dataclass

from sqlalchemy import case, func, or_

from models.saved_player_record import SavedPlayerRecord


PAGE_SIZE = 10
MAX_PAGE_NUMBER = 10_000
MAX_QUERY_LENGTH = 200
SORT_OPTIONS = {"relevance", "newest", "alphabetical"}
SUPPORTED_SOURCES = ("BALDONTLIE", "Manual")


class SearchInputError(ValueError):
    pass


@dataclass
class SearchPage:
    records: list
    total_results: int
    page_number: int
    page_size: int = PAGE_SIZE

    @property
    def total_pages(self):
        return max(1, (self.total_results + self.page_size - 1) // self.page_size)


def normalize_query(query):
    original = query[:MAX_QUERY_LENGTH]
    if len(query) > MAX_QUERY_LENGTH:
        raise SearchInputError(
            f"Search terms must be {MAX_QUERY_LENGTH} characters or fewer."
        )
    normalized = " ".join(query.split()).lower()
    if not normalized:
        raise SearchInputError("Enter a keyword to search saved players.")
    return original, normalized


def escape_like(value):
    return (
        value.replace("!", "!!")
        .replace("\\", "!\\")
        .replace("%", "!%")
        .replace("_", "!_")
    )


def _contains(expression, escaped_pattern):
    return expression.like(escaped_pattern, escape="!")


def supported_source_values():
    stored_sources = (
        SavedPlayerRecord.query.with_entities(SavedPlayerRecord.source)
        .distinct()
        .order_by(SavedPlayerRecord.source.asc())
        .all()
    )
    return tuple(
        sorted(
            set(SUPPORTED_SOURCES).union(
                source for (source,) in stored_sources if source
            ),
            key=str.casefold,
        )
    )


def search_saved_players(query, team=None, source=None, sort="relevance", page=1):
    escaped_phrase = escape_like(query)
    phrase_pattern = f"%{escaped_phrase}%"
    normalized_name = func.lower(func.coalesce(SavedPlayerRecord.name, ""))
    normalized_description = func.lower(func.coalesce(SavedPlayerRecord.description, ""))

    name_match = _contains(normalized_name, phrase_pattern)
    description_match = _contains(normalized_description, phrase_pattern)
    statement = SavedPlayerRecord.query.filter(or_(name_match, description_match))

    if team:
        statement = statement.filter(SavedPlayerRecord.team_abbreviation == team)
    if source:
        statement = statement.filter(SavedPlayerRecord.source == source)

    if sort == "relevance":
        score = case(
            (normalized_name == query, 10),
            (name_match, 5),
            else_=0,
        ) + case((description_match, 2), else_=0)
        statement = statement.order_by(
            score.desc(),
            normalized_name.asc(),
            SavedPlayerRecord.id.asc(),
        )
    elif sort == "newest":
        statement = statement.order_by(
            SavedPlayerRecord.created_at.desc(),
            SavedPlayerRecord.id.desc(),
        )
    else:
        statement = statement.order_by(
            normalized_name.asc(),
            SavedPlayerRecord.id.asc(),
        )

    total_results = statement.order_by(None).count()
    total_pages = max(1, (total_results + PAGE_SIZE - 1) // PAGE_SIZE)
    actual_page = min(page, total_pages)
    records = (
        statement.offset((actual_page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )
    return SearchPage(
        records=records,
        total_results=total_results,
        page_number=actual_page,
    )


def match_reason(record, query):
    name = (record.name or "").lower()
    description = (record.description or "").lower()
    if name == query:
        return "Exact name match"
    if query in name:
        return "Name contains query"
    if query in description:
        return "Scouting note contains query"
    return "Matching record"
