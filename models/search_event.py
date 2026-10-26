from datetime import datetime, timezone

from extensions import db


class SearchEvent(db.Model):
    __tablename__ = "search_events"
    __table_args__ = (
        db.Index("ix_search_events_searched_at", "searched_at"),
        db.Index("ix_search_events_query_normalized", "query_normalized"),
    )

    id = db.Column(db.Integer, primary_key=True)
    query_original = db.Column(db.String(200), nullable=False)
    query_normalized = db.Column(db.String(200), nullable=False)
    searched_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    total_results = db.Column(db.Integer, nullable=False)
    returned_count = db.Column(db.Integer, nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    page_size = db.Column(db.Integer, nullable=False)
    sort_option = db.Column(db.String(20), nullable=False)
    team_filter = db.Column(db.String(20), nullable=True)
    source_filter = db.Column(db.String(60), nullable=True)
    no_results = db.Column(db.Boolean, nullable=False)
