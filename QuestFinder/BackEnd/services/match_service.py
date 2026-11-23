from sentence_transformers import SentenceTransformer, util
from models import User

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def location_match(task, worker):
    if not worker.service_area:
        return False
    return worker.service_area.lower() in task.location.lower()

def recommend_workers(task):
    candidates = [w for w in User.query.filter_by(is_worker=True).all()
                if location_match(task, w)]
    if not candidates:
        return []

    model = get_model()
    task_text = f"{task.skills_required}. {task.title}. {task.description}"
    task_vec = model.encode(task_text, convert_to_tensor=True)
    worker_vecs = model.encode([w.skills or "" for w in candidates], convert_to_tensor=True)
    scores = util.cos_sim(task_vec, worker_vecs)[0].tolist()

    results = [
        {"user_id": w.id, "name": w.name, "skills": w.skills,
        "service_area": w.service_area, "match_score": round(float(s), 2)}
        for w, s in zip(candidates, scores)
    ]
    return sorted(results, key=lambda r: r["match_score"], reverse=True)