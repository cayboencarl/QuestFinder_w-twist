from database import db
from models import Task, User
from sqlalchemy import or_
from models import Task, Transaction
from sqlalchemy import func


def create_task(data, user):
    errors = []

    if not user.is_client:
        return None, ["only clients can post tasks"]

    for field in ["title", "description", "budget", "skills_required", "location", "duration_minutes"]:
        if not data.get(field):
            errors.append(f"{field} is required")

    if data.get("budget") and data["budget"] <= 0:
            errors.append("budget must be greater than 0")
    
    if data.get("duration_minutes") and data["duration_minutes"] <= 0:
        errors.append("duration_minutes must be greater than 0")

    if errors: 
        return None, errors
    
    task = Task(
        title = data["title"],
        description = data["description"],
        budget = data["budget"],
        skills_required = data["skills_required"],
        location = data["location"],
        photo_url = data.get("photo_url"),
        duration_minutes = data["duration_minutes"],
        latitude = data.get("latitude"),
        longitude = data.get("longitude"),
        created_by = user.id,
    )
    db.session.add(task)
    db.session.commit()
    return task, None

def get_all_tasks(search=None):
    query = Task.query.filter_by(status="open")
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Task.title.ilike(pattern),
                                Task.skills_required.ilike(pattern)))
    return query.order_by(Task.created_at.desc()).all()

def get_task(task_id):
    return db.session.get(Task, task_id)

def accept_task(task_id, user):
    task = db.session.get(Task, task_id)
    if task is None:
        return None, ["task not found"]
    if not user.is_worker:
        return None, ["only workers can accept tasks"]
    if task.created_by == user.id:
        return None, ["you cannot accept your own task"]
    if task.status != "open":
        return None, ["this task is no longer open"]

    task.worker_id = user.id
    task.status = "in_progress"
    db.session.commit()
    return task, None
    
def complete_task(task_id, user):
    task = db.session.get(Task, task_id)
    if task is None:
        return None, ["task not found"]
    if task.created_by != user.id:
        return None, ["only the client who posted this task can complete it"]
    if task.status != "in_progress":
        return None, ["only tasks in progress can be completed"]

    commission = round(task.budget * 0.10, 2)
    task.status = "completed"
    transaction = Transaction(
        task_id=task.id,
        client_id=task.created_by,
        worker_id=task.worker_id,
        amount=task.budget,
        commission=commission,
    )
    db.session.add(transaction)
    db.session.commit()
    return transaction, None

def get_wallet(user):
    earned = db.session.query(func.coalesce(func.sum(Transaction.amount - Transaction.commission), 0)) \
        .filter(Transaction.worker_id == user.id).scalar()
    return {"user_id": user.id, "balance": float(earned)}

def get_wallet(user):
    earned = db.session.query(
        func.coalesce(func.sum(Transaction.amount - Transaction.commission), 0)
    ).filter(Transaction.worker_id == user.id).scalar()
    return {"user_id": user.id, "balance": float(earned)}

def get_transactions(user):
    rows = Transaction.query.filter(
        or_(Transaction.worker_id == user.id, Transaction.client_id == user.id)
    ).order_by(Transaction.created_at.desc()).all()
    return [
        {
            "transaction_id": t.id,
            "task_id": t.task_id,
            "amount": t.amount,
            "commission": t.commission,
            "role": "worker" if t.worker_id == user.id else "client",
            "created_at": t.created_at.isoformat(),
        }
        for t in rows
    ]