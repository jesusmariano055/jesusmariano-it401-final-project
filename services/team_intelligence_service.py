"""Combine external sources into a deterministic CourtVision report."""

from collections import Counter

from services.balldontlie_service import get_team_players
from services.basketball_reference_service import scrape_team_context


def build_report(team):
    """Fetch both sources independently and create a safe unified report."""
    api_data = get_team_players(team)
    scraped_data = scrape_team_context(team)
    api_count = len(api_data.get("players", []))
    scraped_count = len(scraped_data.get("roster", []))
    positions = Counter(player.get("position", "Not listed") for player in api_data.get("players", []))
    errors = []
    if api_data.get("status") not in ("success", "empty"):
        errors.append({"source": "API", "message": api_data.get("message", "API data is unavailable.")})
    elif api_data.get("status") == "empty":
        errors.append({"source": "API", "message": api_data["message"]})
    if scraped_data.get("status") != "success":
        errors.append({"source": "Scraper", "message": scraped_data.get("message", "Scraped data is unavailable.")})

    if api_count and scraped_count:
        summary = f"CourtVision combined {api_count} API roster records with {scraped_count} public team-page roster records."
        if api_count != scraped_count:
            summary += " Differences may reflect update timing between sources."
    elif api_count:
        summary = "API-powered roster information is available; public team context could not be fully retrieved."
    elif scraped_count or scraped_data.get("status") == "success":
        summary = "CourtVision is displaying public team context from Basketball-Reference. Configure BALDONTLIE_API_KEY to enable API-powered player information."
    else:
        summary = "External team data is temporarily unavailable. Use Explore Players for the local CourtVision dataset."

    if positions:
        leading_position, leading_count = positions.most_common(1)[0]
        if leading_position != "Not listed":
            summary += f" The API roster has a {leading_position.lower()}-heavy listed-position distribution ({leading_count} records)."

    return {
        "team": team,
        "api_data": api_data,
        "scraped_data": scraped_data,
        "analysis": {"summary": summary, "api_player_count": api_count, "scraped_roster_count": scraped_count, "position_distribution": dict(positions)},
        "errors": errors,
    }
