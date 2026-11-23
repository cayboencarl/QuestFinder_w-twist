"QuestFinder Task Model"
# Imports SqlAlchemy from database.py
from database import db
#Imports current Date and provide timestamp
from datetime import datetime, timezone


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Float, nullable=False)
    skills_required = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    photo_url = db.Column(db.String(500))
    duration_minutes = db.Column(db.Integer, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='open')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "budget": self.budget,
            "skills_required": self.skills_required,
            "location": self.location,
            "photo_url": self.photo_url,
            "duration_minutes": self.duration_minutes,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_by": self.created_by,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "worker_id": self.worker_id,
        }
