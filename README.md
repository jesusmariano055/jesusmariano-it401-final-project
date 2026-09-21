# CourtVision - Jesus Mariano - IT401 - Assignment 2

## Project Overview

CourtVision is a Flask and Jinja2 basketball intelligence prototype for NBA player evaluation and game-strategy analysis. Its target users are analysts, aspiring scouts, coaches, advanced NBA fans, and students who need a structured and explainable way to compare player production, team roles, and public team context.

Assignment 1 established a local JSON player explorer. Assignment 2 extends that prototype with a user-selected Team Intelligence workflow that combines structured information from the BALDONTLIE API with public team context scraped from Basketball-Reference. The application remains server-rendered Flask; there is no SPA, relational database, LLM, or paid AI service.

## External Information Sources

### BALDONTLIE API

CourtVision calls `GET https://api.balldontlie.io/v1/players` with the selected team's numeric `team_ids[]` value and `per_page=100`. The request uses a bearer-style `Authorization` header populated from `BALDONTLIE_API_KEY`. The service normalizes player ID, name, position, team name, team abbreviation, height, weight, and jersey number.

BALDONTLIE provides structured player records under an API contract. Team Intelligence and Explore use `GET https://api.balldontlie.io/v1/players/active` with `team_ids[]` for current active-roster context. Source attribution is shown when a source URL is available. The active-player endpoint provides identity and roster fields, not the A1 season averages, so those remain separate.

### Basketball-Reference

CourtVision requests `https://www.basketball-reference.com/teams/{TEAM_ABBREVIATION}/` using Python `requests`, a descriptive User-Agent, and BeautifulSoup. The scraper safely supports tables that are embedded in HTML comments. It extracts page/team context, roster names, positions, heights, weights, and available metric cells without displaying raw HTML. Basketball-Reference contributes public team-page context and a second roster view for comparison.

Source access depends on the public page being reachable and its HTML structure remaining compatible with the parser. The source URL is linked in the dashboard.

## API vs. Web Scraping

An API provides structured JSON through a documented endpoint and query parameters. Web scraping extracts useful structured values from webpage HTML, so it requires defensive selectors and fallback behavior when page markup changes. CourtVision uses the API for structured basketball/player information and scraping for public team context. Both are normalized and presented together in one Team Intelligence report.

## Application Workflow

```text
User Team Selection
    -> Flask Route Validation
    -> BALDONTLIE API Service + Basketball-Reference Scraper
    -> Data Cleaning and Normalization
    -> Partial-Data/Error Handling
    -> CourtVision Takeaway Generation
    -> Team Intelligence Dashboard
```

The route validates the selected abbreviation against `data/nba_teams.json`. Each external source runs independently. Either source can render when the other fails; if both fail, the page remains navigable and points users to the local Explore page.

## Information Model

- **Player:** local or external player identity, team, position, production, and physical fields.
- **Team:** name, abbreviation, conference, division, and roster context.
- **Game/Matchup:** future entity for dates, opponents, scores, and matchup context.
- **ScoutingReport:** future explainable report containing observations and source status.
- **Watchlist:** future user-saved player collection.
- **ExternalDataSource:** source name, URL, status, and normalized records.
- **TeamIntelligenceReport:** selected team, API data, scraped data, analysis, and errors.

The A1 `data/players.json` file is local prototype information with 2024-25 production fields. BALDONTLIE records are externally acquired current-roster information. Basketball-Reference records are externally scraped team-context information. Assignment 3 is expected to add MySQL persistence for these concepts and historical data.

## Environment Variables

The application reads:

```text
BALDONTLIE_API_KEY=your_api_key_here
```

Copy `.env.example` to `.env`, then add the actual key if one is available. On Windows PowerShell use `Copy-Item .env.example .env`, or create `.env` manually. `.env` is ignored by Git and must never be committed.

The application works in partial-data mode without a key. In that mode it skips the API request, keeps the homepage and A1 Explore page fully available, attempts the Basketball-Reference request, and displays a non-blocking configuration warning.

## Installation Instructions

```bash
git clone <repository-url>
cd project
python3 -m venv .venv
```

Activate on macOS/Linux:

```bash
source .venv/bin/activate
```

Activate on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy environment configuration:

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Add a BALDONTLIE key to `.env` if available, then run:

```bash
python app.py
```

Open `http://127.0.0.1:5000` and run tests with:

```bash
pytest
```

## Current Features

- A1 local JSON player exploration.
- Player filtering by name, team, position, and minimum points per game.
- Team Intelligence page with user-selected NBA team input.
- BALDONTLIE API integration using `requests`.
- Basketball-Reference scraping using `requests` and BeautifulSoup.
- Cleaning and normalization into a unified report.
- Deterministic, rules-based CourtVision Takeaway.
- Partial-data mode without an API key.
- Independent source statuses and friendly errors.
- Automated tests with mocked external requests.

## Error Handling

Missing or blank API keys produce a controlled `not_configured` status and no API request. Empty or invalid team input is handled before any network call. API timeouts, request failures, authorization failures, rate limits, malformed JSON, and empty results receive source-specific statuses. Scraper timeouts, request failures, missing dependencies, changed selectors, and missing content are handled independently. Available data still renders when one source fails. When both sources fail, the dashboard shows a friendly fallback and links to Explore Players; it never displays credentials, raw JSON, HTML, stack traces, or Flask debug output to the user.

## Ethical Considerations

CourtVision attributes its public sources, keeps API keys in environment variables, respects rate limits, makes a small number of requests with short timeouts, and does not scrape authenticated or restricted content. This is an educational integration. External data may be delayed or incomplete and the rules-based Takeaway is not authoritative scouting advice, medical information, a betting recommendation, or a prediction.

## Known Limitations

- Freshness depends on external API and webpage availability.
- BALDONTLIE capabilities can depend on account tier and credentials.
- Basketball-Reference HTML structures can change.
- Page content and season context can vary.
- Roster differences may reflect transaction or update timing.
- The Takeaway is rules-based, not predictive.
- Assignment 2 has no database persistence, authentication, saved accounts, or live game tracking.
- The local A1 player dataset remains intentionally small and static.
- The active roster endpoint does not guarantee a completed 2026-27 season-statistics dataset; it provides current roster identity fields as available.

## Refreshing API Players

The project does not currently use a relational database. To fill a normalized local API cache for the Explore workflow, configure `BALDONTLIE_API_KEY` and run:

```powershell
python -m services.player_sync_service
```

The command follows API pagination and writes `data/api_players.json` with current active roster records, a retrieval timestamp, and `2026-27` roster context. It never overwrites `data/players.json`, so the A1 filters and production metrics remain available. The live Explore team selector also requests the selected team's current roster directly, so the sync command is a repeatable local snapshot rather than a requirement for viewing a selected team.

## Screenshots


- Team Intelligence initial state: ![alt text](image-5.png)
- API results: ![alt text](image-6.png)

## Future Work

Assignment 3 can add MySQL persistence for players, teams, games, reports, and watchlists; historical data and caching; refresh jobs and source adapters; player comparison and similarity; trend detection across games and seasons; matchup analysis; explainable scouting recommendations; user accounts; and saved watchlists.

## Project Structure

- `app.py` - Flask factory and entry point.
- `config.py` - application configuration and data directory.
- `routes/main.py` - homepage, A1 Explore, and Team Intelligence routes.
- `services/balldontlie_service.py` - API request and normalization logic.
- `services/basketball_reference_service.py` - defensive public-page scraper.
- `services/team_intelligence_service.py` - source combination and rules-based analysis.
- `data/players.json` and `data/nba_teams.json` - local A1 data and team fallback catalog.
- `templates/` and `static/` - shared Jinja layout and CourtVision styling.
- `tests/` - local route and service tests with no live external requests.

## Git Workflow

The Assignment 2 branch is `jesus-mariano-it401-a2`. Review changes with:

```bash
git status
git diff --stat
git diff
```

When ready to save the work:

```bash
git add .
git commit -m "Extend CourtVision with team intelligence"
git push -u origin jesus-mariano-it401-a2
```

Do not commit `.env` or a real API key.
