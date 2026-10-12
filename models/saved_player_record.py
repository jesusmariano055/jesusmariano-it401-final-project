from datetime import datetime, timezone

from extensions import db


class SavedPlayerRecord(db.Model):
    __tablename__ = "saved_player_records"
    __table_args__ = (
        db.UniqueConstraint("source", "external_player_id", name="uq_saved_player_source_external_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(60), nullable=False, default="Manual")
    source_url = db.Column(db.String(500), nullable=True)
    retrieved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    external_player_id = db.Column(db.Integer, nullable=True)
    team_name = db.Column(db.String(120), nullable=True)
    team_abbreviation = db.Column(db.String(20), nullable=True)
    position = db.Column(db.String(60), nullable=True)
    height = db.Column(db.String(40), nullable=True)
    weight = db.Column(db.String(40), nullable=True)
    jersey_number = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "external_player_id": self.external_player_id,
            "team_name": self.team_name,
            "team_abbreviation": self.team_abbreviation,
            "position": self.position,
            "height": self.height,
            "weight": self.weight,
            "jersey_number": self.jersey_number,
        }
