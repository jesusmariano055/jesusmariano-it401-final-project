import pytest

from app import create_app


@pytest.fixture
def test_client():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        from extensions import db

        db.drop_all()
        db.create_all()

    with app.test_client() as client:
        yield client


def test_saved_players_page_renders(test_client):
    response = test_client.get("/saved-players")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Saved Players" in page


def test_manual_record_create_and_detail(test_client):
    response = test_client.post(
        "/saved-players/new",
        data={
            "name": "Jalen Brunson",
            "description": "High-level creator with dependable late-game decision making.",
            "source": "Manual",
            "source_url": "",
            "team_abbreviation": "NYK",
            "position": "Guard",
            "height": "6-2",
            "weight": "190",
            "jersey_number": "11",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    assert "Jalen Brunson" in content
    assert "record created" in content.lower()

    response = test_client.get("/saved-players")
    assert response.status_code == 200
    assert "Jalen Brunson" in response.get_data(as_text=True)


def test_duplicate_manual_record_is_rejected(test_client):
    test_client.post(
        "/saved-players/new",
        data={
            "name": "Tyrese Maxey",
            "description": "Off-ball creator and perimeter scorer.",
            "source": "Manual",
            "team_abbreviation": "PHI",
            "position": "Guard",
            "height": "6-2",
            "weight": "200",
            "jersey_number": "0",
        },
    )

    response = test_client.post(
        "/saved-players/new",
        data={
            "name": "Tyrese Maxey",
            "description": "Off-ball creator and perimeter scorer.",
            "source": "Manual",
            "team_abbreviation": "PHI",
            "position": "Guard",
            "height": "6-2",
            "weight": "200",
            "jersey_number": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "already saved" in response.get_data(as_text=True).lower()


def test_invalid_team_abbreviation_is_rejected(test_client):
    response = test_client.post(
        "/saved-players/new",
        data={
            "name": "Test Player",
            "description": "A valid scouting note.",
            "source": "Manual",
            "team_abbreviation": "ZZZ",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "not a valid nba team" in response.get_data(as_text=True).lower()
