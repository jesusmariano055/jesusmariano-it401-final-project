from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from extensions import db
from models.saved_player_record import SavedPlayerRecord
from models.search_event import SearchEvent
from services.search_service import (
    SearchInputError,
    escape_like,
    normalize_query,
    search_saved_players,
)
from services.search_evaluation import evaluate_search_cases, seed_evaluation_records


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
    with app.test_client() as test_client:
        yield test_client


def save_record(name, description, team="LAL", source="Manual", created_at=None):
    record = SavedPlayerRecord(
        name=name,
        description=description,
        source=source,
        team_abbreviation=team,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.session.add(record)
    db.session.commit()
    return record


def test_query_normalization_preserves_original_and_collapses_whitespace():
    original, normalized = normalize_query("  Point \t  GUARD  ")
    assert original == "  Point \t  GUARD  "
    assert normalized == "point guard"


@pytest.mark.parametrize("query", ["", " \t\n "])
def test_empty_query_is_rejected(query):
    with pytest.raises(SearchInputError, match="Enter a keyword"):
        normalize_query(query)


def test_overlong_query_is_rejected():
    with pytest.raises(SearchInputError, match="200 characters"):
        normalize_query("x" * 201)


def test_search_matches_name_or_description_case_insensitively_and_literal_like_chars(client):
    with client.application.app_context():
        save_record("Percent % Player", "Scouting note mentions 100% effort.")
        save_record("Underscore_Player", "Literal underscore record.")
        save_record("Exclamation!Player", "A literal backslash \\ is also searchable.")
        save_record("Quoted Player", "A note with ' OR 1=1 -- as ordinary text.")
        assert [r.name for r in search_saved_players("100%", sort="alphabetical").records] == [
            "Percent % Player"
        ]
        assert [r.name for r in search_saved_players("underscore_", sort="alphabetical").records] == [
            "Underscore_Player"
        ]
        assert [r.name for r in search_saved_players("exclamation!").records] == [
            "Exclamation!Player"
        ]
        assert [r.name for r in search_saved_players("\\").records] == [
            "Exclamation!Player"
        ]
        assert [r.name for r in search_saved_players("' or 1=1 --").records] == [
            "Quoted Player"
        ]


def test_escape_like_escapes_sql_wildcards_and_backslashes():
    assert escape_like(r"100\%_!") == r"100!\!%!_!!"


def test_relevance_weights_and_stable_ties(client):
    with client.application.app_context():
        save_record("guard", "guard creator")
        save_record("A guard", "guard note")
        save_record("B guard", "guard note")
        save_record("Forward", "guard notes")
        assert [r.name for r in search_saved_players("guard").records] == [
            "guard",
            "A guard",
            "B guard",
            "Forward",
        ]


def test_team_source_and_keyword_filters_compose_with_and(client):
    with client.application.app_context():
        save_record("Lakers Guard", "creative guard", "LAL", "Manual")
        save_record("Knicks Guard", "creative guard", "NYK", "Manual")
        save_record("Lakers API Guard", "creative guard", "LAL", "BALDONTLIE")
        assert [r.name for r in search_saved_players("guard", team="LAL", source="Manual").records] == [
            "Lakers Guard"
        ]
        assert len(search_saved_players("guard", team="LAL").records) == 2
        assert len(search_saved_players("guard").records) == 3


def test_search_source_filter_includes_persisted_source_labels(client):
    with client.application.app_context():
        save_record("Custom Source Guard", "A scouting note.", source="Local Scout")

    response = client.get(
        "/search",
        query_string={"q": "scouting", "source": "Local Scout"},
    )
    assert response.status_code == 200
    assert "Custom Source Guard" in response.get_data(as_text=True)
    event = SearchEvent.query.one()
    assert event.source_filter == "Local Scout"


def test_sorting_and_database_pagination(client):
    with client.application.app_context():
        base = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for index in range(12):
            save_record(
                f"Player {index:02}",
                "guard",
                created_at=base + timedelta(days=index),
            )
        newest = search_saved_players("guard", sort="newest")
        alphabetical = search_saved_players("guard", sort="alphabetical")
        next_page = search_saved_players("guard", sort="alphabetical", page=2)
        assert newest.records[0].name == "Player 11"
        assert alphabetical.total_results == 12
        assert len(alphabetical.records) == 10
        assert len(next_page.records) == 2
        assert {r.id for r in alphabetical.records}.isdisjoint({r.id for r in next_page.records})


def test_search_route_initial_empty_invalid_no_results_and_telemetry(client):
    assert client.get("/search").status_code == 200
    assert SearchEvent.query.count() == 0

    empty_response = client.get("/search?q=%20%20")
    assert empty_response.status_code == 400
    assert SearchEvent.query.count() == 0

    found = client.get("/search?q=unmatched")
    assert found.status_code == 200
    assert "No matching records were found" in found.get_data(as_text=True)
    event = SearchEvent.query.one()
    assert event.total_results == 0
    assert event.returned_count == 0
    assert event.no_results is True


def test_search_route_preserves_filters_and_records_pagination(client):
    with client.application.app_context():
        for index in range(12):
            save_record(f"Guard {index:02}", "point guard", "NYK", "Manual")

    page_one = client.get("/search?q=guard&team=NYK&source=Manual&sort=alphabetical")
    assert page_one.status_code == 200
    content = page_one.get_data(as_text=True)
    assert "Page 1 of 2" in content
    assert "team=NYK" in content
    assert "source=Manual" in content
    event_one = SearchEvent.query.order_by(SearchEvent.id.desc()).first()
    assert event_one.page_number == 1
    assert event_one.total_results == 12
    assert event_one.returned_count == 10

    page_two = client.get("/search?q=guard&team=NYK&source=Manual&sort=alphabetical&page=2")
    assert page_two.status_code == 200
    event_two = SearchEvent.query.order_by(SearchEvent.id.desc()).first()
    assert event_two.page_number == 2
    assert event_two.returned_count == 2


def test_out_of_range_page_redirects_without_duplicate_telemetry(client):
    with client.application.app_context():
        save_record("Only Guard", "A guard.")

    response = client.get("/search?q=guard&page=99")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("page=1")
    assert SearchEvent.query.count() == 0

    final_response = client.get(response.headers["Location"])
    assert final_response.status_code == 200
    assert SearchEvent.query.count() == 1
    assert SearchEvent.query.one().page_number == 1


@pytest.mark.parametrize(
    "query",
    [
        "/search?q=guard&team=ZZZ",
        "/search?q=guard&source=Unknown",
        "/search?q=guard&sort=invalid",
        "/search?q=guard&page=0",
        "/search?q=guard&page=abc",
        "/search?q=guard&page=10001",
        f"/search?q=guard&page={'9' * 5000}",
        f"/search?q={'x' * 201}",
    ],
)
def test_invalid_search_parameters_do_not_record_telemetry(client, query):
    response = client.get(query)
    assert response.status_code == 400
    assert SearchEvent.query.count() == 0


def test_search_does_not_call_external_services_and_survives_telemetry_failure(
    client, monkeypatch
):
    with client.application.app_context():
        save_record("No External Call Guard", "A point guard.")

    def fail_external(*args, **kwargs):
        if args or kwargs:
            raise AssertionError("search called an external service")
        raise AssertionError("search must not call external services")

    def telemetry_failed(**kwargs):
        return len(kwargs) == 0

    monkeypatch.setattr("routes.main.get_active_players", fail_external)
    monkeypatch.setattr("routes.search.record_search_event", telemetry_failed)
    response = client.get("/search?q=guard")
    assert response.status_code == 200
    assert "No External Call Guard" in response.get_data(as_text=True)
    assert "could not be recorded" in response.get_data(as_text=True)


def test_search_telemetry_database_write_rolls_back_on_sqlalchemy_error(client, monkeypatch):
    from services import search_telemetry_service

    class BrokenSession:
        rolled_back = False

        def add(self, event):
            assert event is not None

        def commit(self):
            raise SQLAlchemyError("private database detail")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            return None

    session = BrokenSession()
    def fake_sessionmaker(**kwargs):
        assert kwargs["bind"] is not None
        return lambda: session

    monkeypatch.setattr(search_telemetry_service, "sessionmaker", fake_sessionmaker)
    with client.application.app_context():
        recorded = search_telemetry_service.record_search_event(
            query_original="guard",
            query_normalized="guard",
            total_results=1,
            returned_count=1,
            page_number=1,
            page_size=10,
            sort_option="relevance",
        )
    assert recorded is False
    assert session.rolled_back is True


def test_synthetic_evaluation_is_opt_in_idempotent_and_uses_declared_judgments(client):
    with client.application.app_context():
        assert seed_evaluation_records() == {"added": 18, "skipped": 0}
        assert seed_evaluation_records() == {"added": 0, "skipped": 18}
        evaluations = evaluate_search_cases()
        assert SearchEvent.query.count() == 0

    by_label = {evaluation["case"].label: evaluation for evaluation in evaluations}
    assert by_label["Exact name"]["actual_names"] == ["Synthetic Player Atlas"]
    assert by_label["Partial name"]["actual_names"] == ["Synthetic Player Atlas"]
    assert by_label["Scouting concept"]["actual_names"] == [
        "Synthetic Player Atlas",
        "Synthetic Player Harbor",
        "Synthetic Player Ion",
        "Synthetic Player Prairie",
    ]
    assert by_label["Keyword and filters"]["actual_names"] == [
        "Synthetic Player Fable",
        "Synthetic Player Lumen",
    ]
    assert by_label["No match"]["actual_names"] == []
    assert by_label["Synonym limitation"]["actual_names"] == []
    assert by_label["Exact name"]["precision"] == 1
    assert by_label["Exact name"]["recall"] == 1
    assert by_label["Synonym limitation"]["precision"] is None
    assert by_label["Synonym limitation"]["recall"] == 0
