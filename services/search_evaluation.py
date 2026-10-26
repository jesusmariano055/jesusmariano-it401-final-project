from dataclasses import dataclass

from extensions import db
from models.saved_player_record import SavedPlayerRecord
from services.search_service import search_saved_players


EVALUATION_RECORDS = (
    ("Synthetic Player Atlas", "LAL", "Wing defender with strong perimeter defense and switchable coverage."),
    ("Synthetic Player Archer", "LAL", "Point-of-attack defender who contests shots and disrupts passing lanes."),
    ("Synthetic Player Beacon", "LAL", "Lead guard focused on pick-and-roll playmaking and ball control."),
    ("Synthetic Player Comet", "LAL", "Forward who creates second chances through defensive rebounding."),
    ("Synthetic Player Drift", "LAL", "Shooter who spaces the floor with catch-and-shoot attempts."),
    ("Synthetic Player Ember", "LAL", "Center who protects the paint and challenges shots at the rim."),
    ("Synthetic Player Fable", "NYK", "Guard with patient pick-and-roll playmaking and reliable passing."),
    ("Synthetic Player Grove", "NYK", "Forward who drives to the rim and finishes through contact."),
    ("Synthetic Player Harbor", "NYK", "Wing defender with disciplined perimeter defense."),
    ("Synthetic Player Ion", "BOS", "Defender with perimeter defense and quick closeouts."),
    ("Synthetic Player Juniper", "BOS", "Guard who creates advantages through playmaking."),
    ("Synthetic Player Kestrel", "GSW", "Shooter who relocates for open three-point attempts."),
    ("Synthetic Player Lumen", "NYK", "Playmaking guard who organizes half-court possessions."),
    ("Synthetic Player Mosaic", "MIA", "Forward with strong rebounding and transition effort."),
    ("Synthetic Player Nova", "PHX", "Explosive guard who attacks the basket and finishes at the rim."),
    ("Synthetic Player Orbit", "DAL", "Center who provides paint protection and defensive rebounding."),
    ("Synthetic Player Prairie", "CHI", "Wing who contributes through perimeter defense."),
    ("Synthetic Player Quartz", "TOR", "Guard with careful passing and pick-and-roll reads."),
)
FIXTURE_DESCRIPTION_PREFIX = "Synthetic/manual evaluation data."


@dataclass(frozen=True)
class EvaluationCase:
    label: str
    query: str
    intent: str
    expected_names: tuple
    team: str | None = None
    source: str | None = None


EVALUATION_CASES = (
    EvaluationCase(
        "Exact name",
        "synthetic player atlas",
        "Find the named synthetic record.",
        ("Synthetic Player Atlas",),
    ),
    EvaluationCase(
        "Partial name",
        "player at",
        "Find the record whose name contains this partial phrase.",
        ("Synthetic Player Atlas",),
    ),
    EvaluationCase(
        "Scouting concept",
        "perimeter defense",
        "Retrieve records whose notes mention perimeter defense.",
        (
            "Synthetic Player Atlas",
            "Synthetic Player Harbor",
            "Synthetic Player Ion",
            "Synthetic Player Prairie",
        ),
    ),
    EvaluationCase(
        "Keyword and filters",
        "playmaking",
        "Find manually evaluated NYK records whose notes mention playmaking.",
        ("Synthetic Player Fable", "Synthetic Player Lumen"),
        team="NYK",
        source="Manual",
    ),
    EvaluationCase(
        "No match",
        "unicorn defense system",
        "Verify a deliberately unmatched phrase returns no records.",
        (),
    ),
    EvaluationCase(
        "Synonym limitation",
        "rim pressure",
        "Test that phrase matching does not infer rim attacks from a synonym.",
        ("Synthetic Player Nova",),
    ),
)


def seed_evaluation_records():
    added = 0
    skipped = 0
    for name, team, description in EVALUATION_RECORDS:
        exists = SavedPlayerRecord.query.filter(
            SavedPlayerRecord.source == "Manual",
            SavedPlayerRecord.name == name,
            SavedPlayerRecord.description.startswith(FIXTURE_DESCRIPTION_PREFIX),
        ).first()
        if exists:
            skipped += 1
            continue
        db.session.add(
            SavedPlayerRecord(
                name=name,
                description=f"{FIXTURE_DESCRIPTION_PREFIX} {description}",
                source="Manual",
                team_abbreviation=team,
            )
        )
        added += 1
    db.session.commit()
    return {"added": added, "skipped": skipped}


def evaluate_search_cases():
    evaluations = []
    for case in EVALUATION_CASES:
        first_page = search_saved_players(
            case.query.lower(),
            team=case.team,
            source=case.source,
            sort="relevance",
            page=1,
        )
        actual = [record.name for record in first_page.records]
        for page_number in range(2, first_page.total_pages + 1):
            page = search_saved_players(
                case.query.lower(),
                team=case.team,
                source=case.source,
                sort="relevance",
                page=page_number,
            )
            actual.extend(record.name for record in page.records)

        expected = set(case.expected_names)
        actual_set = set(actual)
        relevant_retrieved = len(expected.intersection(actual_set))
        precision = relevant_retrieved / len(actual) if actual else None
        recall = relevant_retrieved / len(expected) if expected else None
        evaluations.append(
            {
                "case": case,
                "actual_names": actual,
                "total_results": first_page.total_results,
                "precision": precision,
                "recall": recall,
            }
        )
    return evaluations
