"""BALDONTLIE API access and response normalization."""

import os

import requests

BASE_URL = "https://api.balldontlie.io/v1/players"
ACTIVE_PLAYERS_URL = "https://api.balldontlie.io/v1/players/active"
CURRENT_ROSTER_SEASON = "2026-27"


def get_team_players(team):
    """Return normalized players for a team with a controlled source status."""
    api_key = os.environ.get("BALDONTLIE_API_KEY", "").strip()
    result = {
        "status": "not_configured",
        "players": [],
        "message": "",
        "source_url": None,
        "roster_season": CURRENT_ROSTER_SEASON,
    }
    if not api_key:
        result["message"] = (
            "BALDONTLIE API data is unavailable because BALDONTLIE_API_KEY has not been configured."
        )
        return result

    source_url = f"{ACTIVE_PLAYERS_URL}?team_ids[]={team['id']}"
    result["source_url"] = source_url
    try:
        response = requests.get(
            ACTIVE_PLAYERS_URL,
            headers={"Authorization": api_key, "Accept": "application/json"},
            params={"team_ids[]": team["id"], "per_page": 100},
            timeout=8,
        )
        if response.status_code in (401, 403):
            response = requests.get(
                BASE_URL,
                headers={"Authorization": api_key, "Accept": "application/json"},
                params={"team_ids[]": team["id"], "per_page": 100},
                timeout=8,
            )
            result["source_url"] = f"{BASE_URL}?team_ids[]={team['id']}"
        if response.status_code == 429:
            result.update(status="rate_limited", message="BALDONTLIE temporarily limited this request.")
            return result
        if response.status_code in (401, 403):
            result.update(status="invalid_credentials", message="BALDONTLIE API credentials were not accepted.")
            return result
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout:
        result.update(status="timeout", message="BALDONTLIE did not respond before the request timed out.")
        return result
    except (ValueError, TypeError):
        result.update(status="malformed_response", message="BALDONTLIE returned an unreadable response.")
        return result
    except requests.RequestException:
        result.update(status="request_failed", message="BALDONTLIE could not be reached right now.")
        return result

    records = payload.get("data", []) if isinstance(payload, dict) else []
    players = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        record_team = record.get("team") or {}
        players.append(
            {
                "player_id": record.get("id"),
                "player_name": " ".join(
                    value for value in (record.get("first_name"), record.get("last_name")) if value
                ).strip(),
                "position": record.get("position") or "Not listed",
                "team_name": record_team.get("full_name") or team["name"],
                "team_abbreviation": record_team.get("abbreviation") or team["abbreviation"],
                "height": record.get("height") or "Not listed",
                "weight": record.get("weight") or "Not listed",
                "jersey_number": record.get("jersey_number") or "Not listed",
            }
        )
    result["status"] = "success" if players else "empty"
    result["players"] = players
    result["message"] = "" if players else "BALDONTLIE returned no player records for this team."
    return result


def get_active_players(cursor=None):
    """Return one normalized page of current active NBA players."""
    api_key = os.environ.get("BALDONTLIE_API_KEY", "").strip()
    result = {
        "status": "not_configured",
        "players": [],
        "message": "",
        "source_url": ACTIVE_PLAYERS_URL,
        "next_cursor": None,
        "roster_season": CURRENT_ROSTER_SEASON,
    }
    if not api_key:
        result["message"] = (
            "BALDONTLIE API data is unavailable because BALDONTLIE_API_KEY has not been configured."
        )
        return result

    params = {"per_page": 100}
    if cursor:
        params["cursor"] = cursor
    try:
        response = requests.get(
            ACTIVE_PLAYERS_URL,
            headers={"Authorization": api_key, "Accept": "application/json"},
            params=params,
            timeout=8,
        )
        if response.status_code in (401, 403):
            response = requests.get(
                BASE_URL,
                headers={"Authorization": api_key, "Accept": "application/json"},
                params={"per_page": 100, **({"cursor": cursor} if cursor else {})},
                timeout=8,
            )
            result["source_url"] = BASE_URL
        if response.status_code == 429:
            result.update(status="rate_limited", message="BALDONTLIE temporarily limited this request.")
            return result
        if response.status_code in (401, 403):
            result.update(status="invalid_credentials", message="BALDONTLIE API credentials were not accepted.")
            return result
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout:
        result.update(status="timeout", message="BALDONTLIE did not respond before the request timed out.")
        return result
    except (ValueError, TypeError):
        result.update(status="malformed_response", message="BALDONTLIE returned an unreadable response.")
        return result
    except requests.RequestException:
        result.update(status="request_failed", message="BALDONTLIE could not be reached right now.")
        return result

    records = payload.get("data", []) if isinstance(payload, dict) else []
    players = []
    for record in records if isinstance(records, list) else []:
        if isinstance(record, dict):
            players.append(_normalize_player(record))
    result["status"] = "success" if players else "empty"
    result["players"] = players
    result["next_cursor"] = (payload.get("meta") or {}).get("next_cursor") if isinstance(payload, dict) else None
    result["message"] = "" if players else "BALDONTLIE returned no active player records."
    return result


def _normalize_player(record, team_fallback=None):
    """Normalize the common BALDONTLIE player shape for UI and cache use."""
    record_team = record.get("team") or team_fallback or {}
    return {
        "player_id": record.get("id"),
        "player_name": " ".join(
            value for value in (record.get("first_name"), record.get("last_name")) if value
        ).strip(),
        "position": record.get("position") or "Not listed",
        "team_name": record_team.get("full_name") or "Not listed",
        "team_abbreviation": record_team.get("abbreviation") or "Not listed",
        "height": record.get("height") or "Not listed",
        "weight": record.get("weight") or "Not listed",
        "jersey_number": record.get("jersey_number") or "Not listed",
    }
