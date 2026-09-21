import pytest

bs4 = pytest.importorskip("bs4")

from services import basketball_reference_service


TEAM = {"name": "Test Team", "abbreviation": "TST", "conference": "West", "division": "Pacific"}


class Response:
    status_code = 200
    text = """
    <html><h1>Test Team</h1>
      <table id="roster"><tbody><tr><td data-stat="player">Example Guard</td><td data-stat="pos">G</td><td data-stat="height">6-3</td><td data-stat="weight">190</td></tr></tbody></table>
      <table id="team_misc"><tbody><tr><td data-stat="wins">42</td><td data-stat="losses">20</td></tr></tbody></table>
    </html>
    """

    def raise_for_status(self):
        return None

    def __init__(self, text=None):
        if text is not None:
            self.text = text


def test_scraper_normalizes_roster_and_context(monkeypatch):
    monkeypatch.setattr(basketball_reference_service.requests, "get", lambda *args, **kwargs: Response())
    result = basketball_reference_service.scrape_team_context(TEAM)
    assert result["status"] == "success"
    assert result["roster"][0]["player_name"] == "Example Guard"
    assert result["roster"][0]["position"] == "G"
    assert result["team_context"]["conference"] == "West"


def test_scraper_missing_expected_elements_is_safe(monkeypatch):
    monkeypatch.setattr(basketball_reference_service.requests, "get", lambda *args, **kwargs: Response("<html><body>No tables</body></html>"))
    result = basketball_reference_service.scrape_team_context(TEAM)
    assert result["status"] == "no_content"
    assert result["roster"] == []
    assert result["team_context"]["team_name"] == "Test Team"
