from services import balldontlie_service
from services import player_sync_service, team_intelligence_service


def test_api_skips_request_without_key(monkeypatch):
    monkeypatch.delenv("BALDONTLIE_API_KEY", raising=False)

    def fail_request(*args, **kwargs):
        raise AssertionError("request should not be made without a key")

    monkeypatch.setattr(balldontlie_service.requests, "get", fail_request)
    result = balldontlie_service.get_team_players({"id": 21, "name": "Oklahoma City Thunder", "abbreviation": "OKC"})
    assert result["status"] == "not_configured"
    assert result["players"] == []


def test_api_normalizes_successful_response(monkeypatch):
    monkeypatch.setenv("BALDONTLIE_API_KEY", "test-key")

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": 1, "first_name": "Test", "last_name": "Player", "position": "G", "team": {"full_name": "Test Team", "abbreviation": "TST"}}]}

    monkeypatch.setattr(balldontlie_service.requests, "get", lambda *args, **kwargs: Response())
    result = balldontlie_service.get_team_players({"id": 1, "name": "Test Team", "abbreviation": "TST"})
    assert result["status"] == "success"
    assert result["players"][0]["player_name"] == "Test Player"
    assert result["players"][0]["team_abbreviation"] == "TST"


def test_api_timeout_is_source_specific(monkeypatch):
    monkeypatch.setenv("BALDONTLIE_API_KEY", "test-key")
    monkeypatch.setattr(balldontlie_service.requests, "get", lambda *args, **kwargs: (_ for _ in ()).throw(balldontlie_service.requests.Timeout()))
    result = balldontlie_service.get_team_players({"id": 1, "name": "Test Team", "abbreviation": "TST"})
    assert result["status"] == "timeout"
    assert "timed out" in result["message"]


def test_active_players_normalizes_page_and_cursor(monkeypatch):
    monkeypatch.setenv("BALDONTLIE_API_KEY", "test-key")

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": 10, "first_name": "Active", "last_name": "Player", "position": "F", "team": {"full_name": "Test Team", "abbreviation": "TST"}}], "meta": {"next_cursor": 55}}

    monkeypatch.setattr(balldontlie_service.requests, "get", lambda *args, **kwargs: Response())
    result = balldontlie_service.get_active_players()
    assert result["status"] == "success"
    assert result["next_cursor"] == 55
    assert result["roster_season"] == "2026-27"
    assert result["players"][0]["player_name"] == "Active Player"


def test_player_sync_writes_normalized_cache(tmp_path, monkeypatch):
    pages = iter([
        {"status": "success", "players": [{"player_name": "First Player"}], "next_cursor": 2},
        {"status": "success", "players": [{"player_name": "Second Player"}], "next_cursor": None},
    ])
    monkeypatch.setattr(player_sync_service, "get_active_players", lambda cursor=None: next(pages))
    result = player_sync_service.sync_active_players(tmp_path)
    assert result["status"] == "success"
    payload = (tmp_path / "api_players.json").read_text(encoding="utf-8")
    assert "First Player" in payload
    assert "Second Player" in payload


def test_combined_report_keeps_scraper_data_when_api_fails(monkeypatch):
    monkeypatch.setattr(team_intelligence_service, "get_team_players", lambda team: {"status": "request_failed", "players": [], "message": "API unavailable", "source_url": "https://api.example"})
    monkeypatch.setattr(team_intelligence_service, "scrape_team_context", lambda team: {"status": "success", "roster": [{"player_name": "Public Player", "position": "G"}], "team_context": {}, "message": "", "source_url": "https://www.basketball-reference.com/teams/TST/"})
    report = team_intelligence_service.build_report({"name": "Test Team", "abbreviation": "TST", "conference": "West", "division": "Pacific"})
    assert report["analysis"]["scraped_roster_count"] == 1
    assert report["analysis"]["api_player_count"] == 0
    assert report["errors"][0]["source"] == "API"


def test_combined_report_keeps_api_data_when_scraper_fails(monkeypatch):
    monkeypatch.setattr(team_intelligence_service, "get_team_players", lambda team: {"status": "success", "players": [{"position": "G"}], "message": "", "source_url": "https://api.example"})
    monkeypatch.setattr(team_intelligence_service, "scrape_team_context", lambda team: {"status": "timeout", "roster": [], "team_context": {}, "message": "Scraper unavailable", "source_url": "https://www.basketball-reference.com/teams/TST/"})
    report = team_intelligence_service.build_report({"name": "Test Team", "abbreviation": "TST", "conference": "West", "division": "Pacific"})
    assert report["analysis"]["api_player_count"] == 1
    assert report["errors"][0]["source"] == "Scraper"