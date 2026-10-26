from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as ReportImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "CourtVision_A4_Report.pdf"


def fit_image(path, max_width, max_height):
    image = ReportImage(str(path))
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    return image


def build_report():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#101b2d"),
            leading=26,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallNote",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#415272"),
        )
    )
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="CourtVision IT401 Assignment 4 Report Draft",
        author="Jesus Mariano",
    )
    story = [
        Paragraph("CourtVision — Jesus Mariano — IT401 — Assignment 4", styles["ReportTitle"]),
        Spacer(1, 0.12 * inch),
        Paragraph(
            "<b>DRAFT — screenshots show the isolated SQLite test app; MySQL integration is unverified.</b>",
            styles["Heading2"],
        ),
        Paragraph(
            "This report summarizes the A4 implementation. Screenshots, telemetry rows, and "
            "evaluation results shown are from isolated in-memory SQLite tests, not MySQL.",
            styles["BodyText"],
        ),
        Spacer(1, 0.18 * inch),
        Paragraph("Project overview and progression", styles["Heading1"]),
        Paragraph(
            "CourtVision is a Flask/Jinja2 basketball evaluation prototype for students, "
            "scouts, and analysts. A1 explored local JSON players; A2 added team intelligence "
            "from BALDONTLIE and Basketball-Reference; A3 persisted saved player notes; A4 "
            "adds database-backed search, ranking, filters, pagination, and limited telemetry.",
            styles["BodyText"],
        ),
        Paragraph("Architecture and search workflow", styles["Heading1"]),
        Paragraph(
            "A GET request is normalized and validated, matched against persisted record "
            "name OR description, restricted by selected team AND source, ranked in SQL, "
            "counted and paginated in the database, rendered in Jinja, and then recorded "
            "through a short-lived isolated telemetry session. Search does not fetch external APIs.",
            styles["BodyText"],
        ),
        Paragraph(
            "Search uses a lowercased contiguous substring phrase, not stemming, tokenization, "
            "semantic search, or synonym expansion. Bound SQLAlchemy values and escaped LIKE "
            "wildcards keep %, _, and backslash literal. Search input is limited to 200 characters.",
            styles["BodyText"],
        ),
        Paragraph("Fields, filters, and explainable ranking", styles["Heading1"]),
        Paragraph(
            "Searchable fields are player name and scouting description. Team abbreviation "
            "and source are structured filters; provenance URL, physical measurements, and "
            "timestamps remain metadata. Boolean behavior is (name match OR description match) "
            "AND selected team AND selected source.",
            styles["BodyText"],
        ),
        Paragraph(
            "The relevance score adds 10 for an exact normalized name, otherwise 5 for a "
            "partial normalized name, and 2 when the description contains the phrase. Name "
            "bonuses are exclusive; the description bonus can stack. Stable ties use normalized "
            "name and ID. Newest and alphabetical sorts have stable ID tie-breakers. Scores are "
            "ordering rules, not probabilities. Page size is 10 and SQL LIMIT/OFFSET is used.",
            styles["BodyText"],
        ),
        Paragraph("Schema and telemetry", styles["Heading1"]),
        Paragraph(
            "The existing saved_player_records table and CRUD remain. The additive "
            "search_events table records bounded original/normalized query, UTC timestamp, "
            "total and returned counts, page number/size, sort, optional team/source, and "
            "no-results status. It has no user/session/IP data, foreign key, or result snapshot. "
            "A telemetry failure rolls back in a separate session and does not hide query results.",
            styles["BodyText"],
        ),
        Paragraph(
            "The application has no authentication. Search telemetry may contain user-entered "
            "text, so users should not search sensitive personal information. Events represent "
            "executed result-page requests, not unique people or intentions.",
            styles["BodyText"],
        ),
        Paragraph("Database upgrade and verification", styles["Heading1"]),
        Paragraph(
            "Run <font name='Courier'>flask --app app init-db</font> against an authorized "
            "development/test MySQL database to create missing tables. This is additive "
            "create_all setup, not a migration system, and must not be run against live "
            "CI-Keys without authorization. Startup does not connect to the database, preserving "
            "A1/A2 pages during an outage.",
            styles["BodyText"],
        ),
        Paragraph(
            "Automated tests use an isolated in-memory SQLite fixture. This verifies application "
            "behavior but does not certify MySQL collation or connection behavior. MySQL "
            "integration was not attempted for this report. The full project test suite passed "
            "45 tests with two existing SQLAlchemy Query.get deprecation warnings.",
            styles["BodyText"],
        ),
        Paragraph("Error handling and design decisions", styles["Heading1"]),
        Paragraph(
            "Blank/overlong queries, unknown team/source filters, invalid sorts, and invalid "
            "pages receive validation messages without successful telemetry. Out-of-range "
            "pages redirect before recording an event. Database failures show a generic "
            "unavailable state and are logged; credentials and raw SQL are not presented. "
            "A genuine empty result is distinct from retrieval failure.",
            styles["BodyText"],
        ),
        Paragraph(
            "The dedicated search page complements the CRUD list. Name and description are "
            "searched because they support player lookup and user-written scouting notes; "
            "team/source remain structured filters. Ranking is transparent and deterministic. "
            "The additive create_all step is not represented as a migration.",
            styles["BodyText"],
        ),
        Paragraph("Known limitations and future A5 work", styles["Heading1"]),
        Paragraph(
            "Phrase matching has no semantics, synonyms, stemming, personalization, or "
            "authentication; punctuation, phrase order, accents, Unicode, and collation "
            "remain limitations. Leading-wildcard LIKE can be slow and conventional indexes "
            "do not eliminate that issue. Future work could explore grounded summaries, "
            "explainable recommendations, query suggestions, or optional semantic retrieval "
            "with appropriate privacy safeguards. None is implemented in A4.",
            styles["BodyText"],
        ),
        Paragraph("Search evaluation status", styles["Heading1"]),
        Paragraph(
            "The evaluation plan defines 18 synthetic/manual records and six expected relevance "
            "cases (exact name, partial name, concept search, team/source filters, no-match, "
            "and a synonym limitation). The evaluation ran in the automated suite against an "
            "isolated in-memory SQLite fixture. Those alternate-engine results are documented "
            "in docs/search-evaluation.md; they do not verify MySQL collation or connections. "
            "No MySQL evaluation was run.",
            styles["BodyText"],
        ),
        Paragraph("Evaluation metrics — isolated SQLite test fixture", styles["Heading2"]),
        Table(
            [
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Case", "Expected", "Actual", "Precision", "Recall")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Exact name", "Atlas", "Atlas", "1.00", "1.00")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Partial name", "Atlas", "Atlas", "1.00", "1.00")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Concept", "Atlas, Harbor, Ion, Prairie", "Atlas, Harbor, Ion, Prairie", "1.00", "1.00")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Keyword + filters", "Fable, Lumen", "Fable, Lumen", "1.00", "1.00")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("No match", "None", "None", "N/A", "N/A")],
                [Paragraph(cell, styles["SmallNote"]) for cell in ("Synonym limitation", "Nova", "None", "N/A", "0.00")],
            ],
            repeatRows=1,
            colWidths=[1.25 * inch, 1.55 * inch, 1.8 * inch, 0.9 * inch, 0.9 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#101b2d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dfea")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4f6fb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            ),
        ),
        Paragraph(
            "Ranking observations: exact and partial-name queries place Atlas first. "
            "Description-only concept matches use the normalized-name tie-break. The filtered "
            "playmaking results are Fable then Lumen. The intentional synonym miss is Nova; "
            "there are no false positives in the executed synthetic cases.",
            styles["SmallNote"],
        ),
        PageBreak(),
        Paragraph("Real screenshot evidence", styles["Heading1"]),
        Paragraph(
            "These are real browser screenshots from the isolated in-memory SQLite test app. "
            "They demonstrate the A4 UI states, but do not verify MySQL. The existing repository "
            "images are from A3.",
            styles["SmallNote"],
        ),
    ]
    screenshot_dir = ROOT / "docs" / "screenshots"
    screenshot_sections = (
        ("Initial search form", ("search-initial-sqlite.png",)),
        ("Search results and exact-name ranking", ("search-ranked-sqlite.png",)),
        ("Team/source-filtered results", ("search-filtered-sqlite.png",)),
        ("Alphabetical sort and pagination", ("search-pagination-page1-sqlite.png", "search-pagination-page2-sqlite.png")),
        ("No-results state", ("search-no-results-sqlite.png",)),
        ("Search telemetry CLI output", ("search-stats-sqlite.png",)),
    )
    for index, (caption, filenames) in enumerate(screenshot_sections):
        story.append(Spacer(1, 0.14 * inch))
        story.append(Paragraph(caption, styles["Heading2"]))
        images = [
            fit_image(screenshot_dir / filename, 6.6 * inch, 5.9 * inch)
            for filename in filenames
        ]
        if len(images) == 1:
            story.append(images[0])
        else:
            for image in images:
                image.drawWidth = min(image.drawWidth, 3.15 * inch)
                image.drawHeight = image.imageHeight * image.drawWidth / image.imageWidth
            story.append(
                Table(
                    [[images[0], images[1]]],
                    colWidths=[3.3 * inch, 3.3 * inch],
                    style=TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ]
                    ),
                )
            )
        if index < len(screenshot_sections) - 1:
            story.append(PageBreak())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)


if __name__ == "__main__":
    build_report()
