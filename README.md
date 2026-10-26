# CourtVision — Jesus Mariano — IT401 — Assignment 4

## Project overview

CourtVision is a server-rendered Flask/Jinja2 prototype for NBA player evaluation and team-strategy research. It is intended for students, scouts, and basketball analysts who need to explore a local player dataset, review team context, and retrieve previously saved player notes.

The project progression is:

- **A1:** local JSON player exploration and filters.
- **A2:** team intelligence combining BALDONTLIE and Basketball-Reference data.
- **A3:** MySQL-backed saved player records and CRUD.
- **A4:** database-backed search, explainable ranking, pagination, and limited search telemetry.

The A4 search page complements, rather than replaces, the saved-player CRUD list. It searches the persisted records without making a request to an external API for each query.

## Search and retrieval

Visit `/search` or choose **Search** in the shared navigation. Submit the GET form to search saved records by a normalized phrase. Searchable fields are `SavedPlayerRecord.name` and `SavedPlayerRecord.description`. Optional AND filters are the canonical team abbreviation and a provenance label (`Manual`, `BALDONTLIE`, or a source label already stored in the database). Available sorts are relevance, newest saved, and alphabetical.

The retrieval path is:

```text
GET request
→ trim/collapse whitespace and validate input
→ SQLAlchemy phrase match on name OR description
→ AND selected team/source filters
→ rule-based score and stable sort
→ database count and LIMIT/OFFSET pagination
→ render results and matching reasons
→ write an isolated search-event transaction
```

An empty `/search` page does not query the record table or write telemetry. Search never calls BALDONTLIE or Basketball-Reference.

### Search behavior and ranking

- Matching is a case-normalized contiguous substring phrase; it is not tokenized linguistic, stemmed, semantic, or synonym-expanded search.
- The original submitted query (up to 200 characters) remains in the form. Internal whitespace is collapsed and the matching form is lowercased. Queries over 200 characters and blank queries are rejected.
- SQLAlchemy bound expressions carry query values. `%`, `_`, and backslash are escaped so they are literal input, not user-controlled LIKE wildcards.
- The database applies `LOWER(COALESCE(...))` to both searchable fields. This provides case-insensitive matching independent of the default column collation for ordinary text. Accent equivalence, all Unicode case-folding behavior, and locale-specific ordering still depend on database behavior and are not promised.
- Boolean eligibility is `(name contains phrase OR description contains phrase) AND team (if selected) AND source (if selected)`.
- Relevance score: exact normalized name `+10`; otherwise partial normalized name `+5`; description phrase `+2`. Name bonuses are mutually exclusive; the description bonus can accompany either. Description-only matches remain eligible.
- Relevance ties sort by lowercased name then record ID. Newest sorts by creation timestamp then ID descending. Alphabetical sorts by lowercased name then ID ascending.
- Scores are ordering rules, not probabilities or confidence estimates. The UI shows a short match reason based on the same phrase rules.
- The page size is 10. The match count and page records are queried separately, and ordering/filtering happen in SQL before LIMIT/OFFSET.
- LIKE-style matching with a leading wildcard can be slow on large datasets; a conventional index does not make these searches fully index-efficient.

Team and source are structured filters, not keyword fields. Provenance URLs, measurements, and timestamps are metadata and are not searched.

## Search telemetry and privacy

`search_events` records one row for each successfully executed valid results-page request, including pagination and zero-result searches. Initial, invalid, and failed retrieval requests do not create successful events. A refresh can create another event; rows do not represent unique users or unique intentions.

Stored fields include the bounded original and normalized query, UTC timestamp, total matches, returned count, page number/size, sort option, optional team/source filters, and a no-results flag. No user IDs, session IDs, IP addresses, user agents, API keys, result snapshots, or credentials are stored. Search queries are user-entered text; do not enter sensitive personal information. Telemetry is for educational evaluation, not production analytics. Retention controls could be added later.

Telemetry writes use a short-lived SQLAlchemy session and are isolated from the result query. A telemetry failure is logged safely and does not discard usable search results. Inspect bounded aggregate/recent event information with:

```powershell
flask --app app search-stats
```

The CLI prints recent normalized query strings, so run it only in an appropriate local environment.

## Database schema

### `saved_player_records`

The A3 table is retained without destructive changes. It stores player name and scouting description, provenance, external player ID, team identity, position, measurements, jersey string, and creation/update/retrieval timestamps. A unique `(source, external_player_id)` constraint protects imported BALDONTLIE identities. It has no relationship tables.

### `search_events`

The A4 table has an integer primary key and the telemetry fields described above. Indexes support time-ordered inspection and query-text aggregation. It has no foreign key to a saved player and stores no result snapshot.

`flask --app app init-db` calls SQLAlchemy `create_all()` to create missing tables, including the new telemetry table. This is a non-destructive additive setup step; it does not alter existing columns or constitute a migration system. Do not run it against a live CI-Keys database without authorization. Future changes to existing columns require a real migration process.

## Installation and database setup

Use the A4 branch:

```powershell
git checkout jesus-mariano-it401-a4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the existing environment variables in `.env`:

```text
BALDONTLIE_API_KEY=
SECRET_KEY=
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_SSL_CA=
```

Create the MySQL schema in the approved environment, then initialize missing tables and run:

```powershell
flask --app app init-db
python app.py
```

Do not put credentials in source control. Without MySQL configuration, the application starts in non-persistent mode; it does not use a local SQLite file as a substitute. Explore and Team Intelligence remain available. Database-backed pages explain that persistence is not configured. Startup does not connect to or initialize the database, so an unavailable database does not prevent A1/A2 pages from loading.

For automated tests:

```powershell
python -m pytest -q
```

Tests use an isolated in-memory SQLite fixture. This checks application behavior but does **not** certify MySQL collation, connection settings, or MySQL-specific behavior.

## Search evaluation

The deterministic fixture and six predeclared relevance judgments are documented in [docs/search-evaluation.md](./docs/search-evaluation.md). Every fixture row is explicitly marked as synthetic/manual evaluation data; fixture insertion is opt-in and never deletes existing records.

Only use the fixture commands after confirming the configured database is a dedicated development/test database:

```powershell
flask --app app seed-search-evaluation --confirm
flask --app app evaluate-search
```

The automated evaluation ran against its isolated in-memory SQLite fixture; the actual results and precision/recall are in [docs/search-evaluation.md](./docs/search-evaluation.md). The Flask CLI commands were also exercised with Flask's CLI test runner on an in-memory test app. Browser screenshots and captured command output are in [docs/screenshots/](./docs/screenshots/). These are alternate-engine results and UI evidence, not MySQL certification. No dedicated MySQL test database was available, no `.env` settings were changed, and no live schema operation was run.

## Current features

- Homepage and shared navigation.
- Local JSON Explore workflow and filters.
- BALDONTLIE retrieval and Basketball-Reference team context.
- MySQL-backed saved-player record CRUD.
- Search over saved database records by name and scouting description.
- Team and source Boolean filters.
- Rule-based relevance, newest, and alphabetical sorts.
- Stable database-level pagination.
- Isolated educational search telemetry and CLI inspection.
- Existing validation, CSRF protection, and source-specific external-service error handling.

## Project structure

```text
app.py                              Flask factory and CLI commands
config.py                           MySQL/environment configuration
extensions.py                       shared SQLAlchemy extension
models/saved_player_record.py       persisted player/scouting record
models/search_event.py              search telemetry schema
routes/main.py                      existing A1/A2/A3 routes and CRUD
routes/search.py                    GET search validation and rendering
services/search_service.py          normalization, matching, scoring, pagination
services/search_telemetry_service.py isolated event writes and statistics
services/search_evaluation.py       opt-in synthetic fixture and evaluation runner
services/balldontlie_service.py     BALDONTLIE integration
services/basketball_reference_service.py team-context scraper
services/team_intelligence_service.py combined A2 report
templates/search/index.html         search form, states, results, pagination
templates/                           shared server-rendered pages
static/style.css                     responsive CourtVision styling
data/                                 local players and NBA team catalog
docs/search-evaluation.md            relevance judgments and execution status
scripts/generate_a4_report.py         standalone PDF report generator
tests/test_search.py                  A4 search, telemetry, and evaluation coverage
```

## Error handling and known limitations

Blank/overlong queries, unknown team/source values, invalid sorts, and invalid pages receive helpful validation responses without successful telemetry. Pages above the final page redirect to a canonical valid page before an event is written. Database query errors show a generic unavailable message and are logged without exposing SQL or credentials. Telemetry failures are rolled back independently; result rendering continues with a warning. A genuinely empty result is distinct from a database error.

Search is phrase-substring matching with rule-based ranking. It has no semantic understanding, synonyms, stemming, personalization, or authentication. Phrase order and punctuation matter; singular/plural variations may not match. MySQL collation affects database sorting and language-specific details. Leading-wildcard LIKE may not scale. Saved records can become stale, and this prototype does not provide multi-user ownership.

## Future work — A5

Possible later work includes summaries grounded in retrieved records, explainable recommendations, query suggestions, and (if justified) optional semantic retrieval. Personalization would require an appropriate privacy and access-control design. None of those capabilities, LLMs, embeddings, or recommendation systems is implemented in A4.

## Evaluation and PDF evidence status

The 18-record evaluation corpus is synthetic and opt-in. Expected relevant records are declared before running the queries. See [docs/search-evaluation.md](./docs/search-evaluation.md) for query intent, filters, judgments, formulas, and the unexecuted-results template.

Generate the report draft from the repository root:

```powershell
python scripts\generate_a4_report.py
```

The generated `docs/CourtVision_A4_Report.pdf` is labeled a **draft** and embeds real browser screenshots from the isolated SQLite test app. It is not a claim of MySQL integration verification. To complete MySQL evidence, run the database steps against a dedicated authorized MySQL test database and replace or augment the SQLite evidence. Existing root-level images are A3 screenshots, not A4 search evidence.

## Git workflow

Current task branch: `jesus-mariano-it401-a4`, based on the available A3 branch. Review and commit manually:

```powershell
git status
git diff --check
git diff
git add README.md app.py config.py models routes services templates static tests docs scripts
git commit -m "Add A4 saved-player search and evaluation"
git push -u origin jesus-mariano-it401-a4
```
