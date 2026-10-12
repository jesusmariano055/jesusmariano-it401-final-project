import re

import pytest

from app import create_app
from models.saved_player_record import SavedPlayerRecord


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_default_development_app_initializes_saved_player_table():
    app = create_app("development")
    with app.app_context():
        assert SavedPlayerRecord.query.count() == 0


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "CourtVision" in page
    assert "Jesus Mariano" in page
    assert "/explore" in page


def test_explore(client):
    response = client.get("/explore")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Shai Gilgeous-Alexander" in page
    assert "Explore NBA players" in page


def test_explore_team_filter(client):
    response = client.get("/explore?team=OKC")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Shai Gilgeous-Alexander" in page
    assert "OKC" in page
    assert "Nikola Jokic" not in page


def test_explore_min_ppg_filter(client):
    response = client.get("/explore?min_ppg=28")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    values = [float(value) for value in re.findall(r"(\d+\.\d+)\s+PPG", page)]
    assert values
    assert all(value >= 28 for value in values)


def test_team_intelligence_empty_state(client):
    response = client.get("/team-intelligence")
    assert response.status_code == 200
    assert "Start with a team" in response.get_data(as_text=True)


def test_team_intelligence_missing_selection_is_controlled(client):
    response = client.get("/team-intelligence?team=")
    assert response.status_code == 200
    assert "Start with a team" in response.get_data(as_text=True)


def test_team_intelligence_invalid_team_is_controlled(client):
    response = client.get("/team-intelligence?team=NOT_A_TEAM")
    assert response.status_code == 200
    assert "Please choose an NBA team" in response.get_data(as_text=True)


def test_team_intelligence_valid_team_uses_unified_report(client, monkeypatch):
    monkeypatch.setattr(
        "routes.main.build_report",
        lambda team: {
            "team": team,
            "api_data": {"status": "not_configured", "players": [], "message": "API unavailable", "source_url": None},
            "scraped_data": {"status": "success", "team_context": {"season": "2025", "wins": "10", "losses": "5", "conference": "West", "division": "Northwest"}, "roster": [], "message": "", "source_url": "https://www.basketball-reference.com/teams/OKC/"},
            "analysis": {"summary": "Partial report", "api_player_count": 0, "scraped_roster_count": 0, "position_distribution": {}},
            "errors": [],
        },
    )
    response = client.get("/team-intelligence?team=OKC")
    assert response.status_code == 200
    assert "Partial report" in response.get_data(as_text=True)
