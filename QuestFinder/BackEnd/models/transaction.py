from database import db
from datetime import datetime, timezone

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, nullable = False, primary_key = True)
    
    task_id = db.Column(
        db.Integer, 
        db.ForeignKey('tasks.id'), 
        nullable = False)

    client_id = db.Column(db.Integer, 
                db.ForeignKey('users.id'), 
                nullable = False)

    worker_id = db.Column(
                db.Integer, 
                db.ForeignKey('users.id'), 
                nullable = False)

    amount = db.Column(db.Float, nullable = False)

    commission = db.Column(db.Float, 
                nullable = False)

    created_at = db.Column(
                db.DateTime, 
                nullable = False, 
                default = lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return{
            "id": self.id,
            "task_id": self.task_id,
            "client_id": self.client_id,
            "worker_id": self.worker_id,
            "amount": self.amount,
            "commision": self.commision,
            "created_at": self.created_at
        }
