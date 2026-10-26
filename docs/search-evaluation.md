# CourtVision A4 search evaluation

## Corpus and method

The evaluation corpus contains 18 fictional, **synthetic/manual evaluation data** records defined in `services/search_evaluation.py`. All use `source=Manual`; none impersonates an external API result. Team abbreviations follow the local NBA catalog. Fixture insertion is opt-in, additive, duplicate-safe by source/name, and does not delete or modify existing records.

Run only after confirming that the configured database is a dedicated development/test database and initializing its schema:

```powershell
flask --app app init-db
flask --app app seed-search-evaluation --confirm
flask --app app evaluate-search
```

Search evaluation reads records across all database pages but does not emit search telemetry because it calls the retrieval service directly. The test suite's in-memory SQLite database is an alternate-engine test environment, not MySQL integration evidence.

Metrics use all retrieved records across pages, not only the current UI page:

- Precision = relevant retrieved records / all retrieved records.
- Recall = relevant retrieved records / all expected relevant records.
- If there are no retrieved records, precision is N/A.
- If there are no expected relevant records, recall is N/A.

Expected relevant names are declared independently of execution output in the evaluation cases. The runner reports actual returned names and calculates metrics when explicitly run.

## Predeclared evaluation cases

The exact expected record names are the ground-truth relevance judgments. All records in this corpus are synthetic/manual.

| Case | Query | Intent and filters | Expected relevant records |
|---|---|---|---|
| Exact name | `synthetic player atlas` | Find the named record; no filters | Synthetic Player Atlas |
| Partial name | `player at` | Find a record by a partial name; no filters | Synthetic Player Atlas |
| Scouting concept | `perimeter defense` | Find scouting notes mentioning the phrase; no filters | Synthetic Player Atlas; Synthetic Player Harbor; Synthetic Player Ion; Synthetic Player Prairie |
| Keyword + filters | `playmaking` | Team `NYK`, source `Manual`; relevance is judged within this eligible filtered corpus | Synthetic Player Fable; Synthetic Player Lumen |
| No match | `unicorn defense system` | Verify unmatched phrase; no filters | None |
| Synonym limitation | `rim pressure` | Demonstrate that `attacks the basket` is not inferred as a synonym; no filters | Synthetic Player Nova |

## Executed alternate-engine evaluation

The evaluation was run by `test_synthetic_evaluation_is_opt_in_idempotent_and_uses_declared_judgments` against its isolated in-memory SQLite test database. The fixture was seeded in the test only and did not touch the configured application database. Metrics below are actual test results for SQLite, **not MySQL integration evidence**.

| Case | Expected relevant records | Actual results (all pages) | Precision | Recall | Ranking, false positives, misses, improvement |
|---|---|---|---:|---:|---|
| Exact name | Atlas | Atlas | 1.00 | 1.00 | Atlas is the exact name result. No false positives/misses. Improvement: run the same case on the deployment MySQL collation. |
| Partial name | Atlas | Atlas | 1.00 | 1.00 | Atlas matched the partial name phrase. No false positives/misses. Improvement: add judged partial queries with overlapping names. |
| Scouting concept | Atlas, Harbor, Ion, Prairie | Atlas, Harbor, Ion, Prairie | 1.00 | 1.00 | Four description phrase matches; alphabetical tie-break is stable. No false positives/misses. Improvement: collect relevance judgments for broader scouting language. |
| Keyword + filters | Fable, Lumen | Fable, Lumen | 1.00 | 1.00 | Both records match `playmaking` within NYK + Manual. No false positives/misses. Improvement: add filter-combination cases for teams with no eligible records. |
| No match | None | None | N/A | N/A | No false positives. Precision is undefined with zero retrieved; recall is undefined with zero expected relevant. Improvement: repeat with near-miss phrases to examine substring boundaries. |
| Synonym limitation | Nova | None | N/A | 0.00 | Nova is a meaningful miss because “attacks the basket” is not a synonym-expanded match for `rim pressure`. Precision is undefined with zero retrieved. Improvement: assess whether an explicit reviewed synonym list is justified. |

**MySQL status:** the `.env` file had no MySQL connection settings, and the user confirmed no dedicated MySQL test database was available. No live database credentials were inspected, no `.env` values were changed, and no live schema operation was run. MySQL-specific collation, connection behavior, and these evaluation metrics remain unverified.

The Flask commands `init-db`, `seed-search-evaluation --confirm`, `evaluate-search`, and `search-stats` were invoked through Flask's CLI test runner against an isolated in-memory SQLite app. The commands created only temporary in-memory tables and records. The actual command output and search-event counts are saved in `docs/screenshots/sqlite-cli-evidence.txt`. They are not persistent DB evidence.

Improvement ideas to consider after seeing real results: add carefully curated synonyms as a separate, explicit feature; evaluate ranking against more user-authored judgments; and measure index/query performance at realistic scale. None is part of A4.

## Screenshot evidence

Real browser screenshots were captured from the running synthetic/manual in-memory SQLite app:

- `search-initial-sqlite.png` — initial `/search` form.
- `search-ranked-sqlite.png` — exact-name result and match reason.
- `search-filtered-sqlite.png` — NYK + Manual filtered playmaking results.
- `search-pagination-page1-sqlite.png` and `search-pagination-page2-sqlite.png` — alphabetical results with page navigation.
- `search-no-results-sqlite.png` — no-results state.
- `search-stats-sqlite.png` — CLI telemetry output rendered for screenshot capture.

These images are A4 UI evidence but not MySQL integration evidence. The CLI screenshot visualizes output captured by the Flask CLI test runner in the same isolated testing app.
