from flask import Blueprint, request, jsonify
from services.task_service import create_task
from models import User
from services.task_service import get_all_tasks, get_task, accept_task
from database import db
from services.task_service import complete_task

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

@tasks_bp.route("", methods=["POST"])
def post_task():
    # 1. Get the user from the X-User-Id header.
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    user = User.query.get(int(user_id))
    if user is None:
        return jsonify({"error": "user not found"}), 401

    data = request.get_json(silent=True) or {}

    if not user.is_client:
        return jsonify({"errors": "only clients can post tasks"}), 403

    task, errors = create_task(data, user)
    if errors is not None:
        return jsonify({"errors": errors}), 400

    return jsonify(task.to_dict()), 201

@tasks_bp.route("", methods=["GET"])
def list_tasks():
    search = request.args.get("search")
    tasks = get_all_tasks(search)
    return jsonify([t.to_dict() for t in tasks]), 200

@tasks_bp.route("/<int:task_id>", methods=["GET"])
def task_detail(task_id):
    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task.to_dict()), 200

@tasks_bp.route("/<int:task_id>/accept", methods=["POST"])
def accept(task_id):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "user not found"}), 401

    task, errors = accept_task(task_id, user)
    if errors is not None:
        return jsonify({"errors": errors}), 400

    return jsonify(task.to_dict()), 200

@tasks_bp.route("/<int:task_id>/complete", methods=["POST"])
def complete(task_id):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "user not found"}), 401

    transaction, errors = complete_task(task_id, user)
    if errors is not None:
        return jsonify({"errors": errors}), 400

    return jsonify({
        "transaction_id": transaction.id,
        "task_id": transaction.task_id,
        "amount": transaction.amount,
        "commission": transaction.commission,
        "worker_receives": transaction.amount - transaction.commission,
    }), 201

