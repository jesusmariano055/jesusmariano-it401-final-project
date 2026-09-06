import re

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
