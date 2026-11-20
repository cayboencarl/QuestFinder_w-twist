from flask import Blueprint, request, jsonify
from services.task_service import create_task
from models import User

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

@tasks_bp.route("", methods=["POST"])
def post_task():
    # 1. Get the user from the X-User-Id header.
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    # 2. If there's no user, return 401.
    user = user.query.get(int(user_id))
    if user is None:
        return jsonify({"error":"user not found"}), 401
        
    data = request.get_json(silent = True) or {}


        
    
    # 3. Read the JSON body with request.get_json().
    # 4. Call create_task(data, user).
    # 5. If errors came back, return them with 400.
    # 6. Otherwise return task.to_dict() with 201.
    pass

"""
user_id = request.headers.get("X-User-Id")
if not user_id:
    return jsonify({"error": "X-User-Id header is required"}), 401

user = User.query.get(int(user_id))
if user is None:
    return jsonify({"error": "user not found"}), 401
"""