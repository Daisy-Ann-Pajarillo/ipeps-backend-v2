from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User
from app.constants import USER_TYPES
from datetime import timedelta


auth = HTTPBasicAuth()

main_bp = Blueprint('main', __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = User.query.filter_by(username=username_or_token).first()
        hash_password = user.password
        if not user or not user.verify_password(password, hash_password):
            return False
    g.user = user
    return True

@main_bp.route('/token', methods=['GET'])
@auth.login_required
def login():
    expiration = timedelta(hours=6)  # 6 hours expiration

    token = g.user.generate_auth_token(expires_delta=expiration)
    token = str(token)
    
    expires_in_seconds = int(expiration.total_seconds())
    return jsonify(
        {
            "token": token,
            "expires_in": expires_in_seconds,
        }
    )

@main_bp.route('/create-user', methods=['POST'])
def create_user():
    try:
        data = request.form

        required_fields = {"username", "email", "password", "user_type"}
        if not required_fields.issubset(data):
            return jsonify({"error": "Missing required fields"}), 400

        if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Username or email already taken"}), 409
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=User.hash_password(data['password']),
            user_type=data['user_type']
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "User created successfully",
            "user": {
                "user_id": new_user.user_id,
                "username": new_user.username,
                "email": new_user.email,
                "user_type": new_user.user_type
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500