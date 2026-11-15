"Managed by Carl & Marc"
from database import db
from datetime import datetime, timezone

class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, nullable = False, primary_key = True)

    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id'))
    
    task_id = db.Column(
        db.Integer, 
        db.ForeignKey('tasks.id'))

    status = db.Column(
        db.String(30),
        nullable = False, 
        default = 'pending')

    message = db.Column(
        db.Text, 
        nullable = True)

    created_at = db.Column(
        db.DateTime, 
        nullable = False, 
        default = lambda: datetime.now(timezone.utc))
    def to_dict(self):
        return{
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at
        }





