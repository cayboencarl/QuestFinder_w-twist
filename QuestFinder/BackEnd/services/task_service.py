from database import db
from models import Task, User

def create_task(data, user):
    errors = []

    if not user.is_client:
        return None, ["only clients can post tasks"]

    for field in ["title", "description", "budget", "skills_required", "location", "duration_minutes"]:
        if not data.get(field):
            errors.append(f"{field} is required")

    if data.get("budget") and data["budget"] <= 0:
            errors.append("budget must be greater than 0")
    
    if data.get("duration_minutes") and data["duaration_minutes"] <= 0:
        errors.append("duration should be greater than 0")

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

    

