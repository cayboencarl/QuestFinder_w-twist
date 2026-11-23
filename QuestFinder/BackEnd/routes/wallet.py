from flask import Blueprint, request, jsonify
from database import db
from models import User
from services.task_service import get_wallet, get_transactions

wallet_bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")

@wallet_bp.route("", methods=["GET"])
def wallet():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "user not found"}), 401

    return jsonify(get_wallet(user)), 200

from services.task_service import get_wallet, get_transactions

@wallet_bp.route("/transactions", methods=["GET"])
def transactions():
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return jsonify({"error": "X-User-Id header is required"}), 401

    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "user not found"}), 401

    return jsonify(get_transactions(user)), 200