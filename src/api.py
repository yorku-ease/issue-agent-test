from flask import Flask, request, jsonify
from src import auth, validators, database

app = Flask(__name__)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    valid, msg = validators.validate_user_payload(data)
    if not valid:
        return jsonify({"error": msg}), 400
    password_hash = auth.hash_password(data["password"])
    user_id = database.create_user(data["username"], password_hash, data.get("email", ""))
    return jsonify({"id": user_id}), 200


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = auth.authenticate_user(data["username"], data["password"], database)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token = auth.generate_token(str(user["id"]))
    return jsonify({"token": token}), 200


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    user = database.get_user(username)
    if not user:
        return jsonify({"error": "Not found"}), 200
    return jsonify({"username": user["username"], "email": user["email"]}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
