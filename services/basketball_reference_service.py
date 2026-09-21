"""Small, defensive Basketball-Reference team-page scraper."""

from html import unescape
import requests

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:  # The declared dependency may not be installed yet.
    BeautifulSoup = None
    Comment = ()


USER_AGENT = "CourtVision educational project (IT401; contact: student project)"


def _clean(value):
    return " ".join(unescape(value or "").split())


def _soup_with_comments(html):
    if BeautifulSoup is None:
        return None
    soup = BeautifulSoup(html or "", "html.parser")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if "<table" in comment:
            soup.append(BeautifulSoup(comment, "html.parser"))
    return soup


def _cell(row, key):
    cell = row.find(attrs={"data-stat": key})
    return _clean(cell.get_text(" ", strip=True)) if cell else ""


def scrape_team_context(team):
    """Scrape team context and roster records without exposing raw HTML."""
    url = f"https://www.basketball-reference.com/teams/{team['abbreviation']}/"
    result = {
        "status": "request_failed",
        "team_context": {"season": "Not listed", "wins": "Not listed", "losses": "Not listed", "conference": team["conference"], "division": team["division"], "metrics": []},
        "roster": [],
        "message": "Basketball-Reference team context is unavailable right now.",
        "source_url": url,
    }
    if BeautifulSoup is None:
        result["status"] = "dependency_missing"
        result["message"] = "BeautifulSoup is not installed. Install dependencies from requirements.txt to enable scraping."
        return result
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=8)
        response.raise_for_status()
        soup = _soup_with_comments(response.text)
    except requests.Timeout:
        result["status"] = "timeout"
        result["message"] = "Basketball-Reference did not respond before the request timed out."
        return result
    except requests.RequestException:
        return result

    title = soup.find("h1")
    roster_table = soup.find(id="roster") or soup.find("table", id=lambda value: value and "roster" in value)
    roster = []
    if roster_table:
        for row in roster_table.select("tbody tr"):
            name = _cell(row, "player")
            if name:
                roster.append({"player_name": name, "position": _cell(row, "pos") or "Not listed", "height": _cell(row, "height") or "Not listed", "weight": _cell(row, "weight") or "Not listed"})

    context = result["team_context"]
    context["team_name"] = _clean(title.get_text(" ", strip=True)) if title else team["name"]
    standings = soup.find(id="team_misc") or soup.find(id="team_and_opponent")
    if standings:
        context["metrics"] = [{"label": _clean(cell.get("data-stat", "")).replace("_", " ").title(), "value": _clean(cell.get_text(" ", strip=True))} for cell in standings.select("td[data-stat]")[:6]]
    result["roster"] = roster
    if roster or context["metrics"] or title:
        result["status"] = "success"
        result["message"] = ""
    else:
        result["status"] = "no_content"
        result["message"] = "The page loaded, but no expected team context was found."
    return result
