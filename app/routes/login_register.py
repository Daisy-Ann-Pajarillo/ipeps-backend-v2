from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User
from datetime import timedelta

auth = HTTPBasicAuth()

main_bp = Blueprint('main', __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token first
    user = User.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = User.query.filter_by(username=username_or_token).first()
        # hash_password = user.password
        if not user or not user.verify_password(password=password):
            return False
    print(user)
    g.user = user
    return True

@main_bp.route('/token', methods=['GET'])
@auth.login_required
def login():
    try:

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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route('/create-user', methods=['POST'])
def create_user():
    """
    Route to create a new user.
    Accepts both JSON and form-data formats.
    Required fields: username, email, password, user_type
    """
    try:
        # Get data from either JSON or form-data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # Log received data for debugging
        print("Received data for user creation:", {k: v for k, v in data.items() if k != 'password'})

        # Check required fields
        required_fields = {"username", "email", "password", "user_type"}
        if not all(data.get(field) for field in required_fields):
            missing = [f for f in required_fields if not data.get(f)]
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        # Check for existing username/email
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already exists"}), 409
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Email already exists"}), 409

        # Normalize user_type to lowercase
        user_type = str(data['user_type']).upper()

        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=User.hash_password(data['password']),
            user_type=user_type
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "User created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        print("Error in /create-user:", str(e))
        return jsonify({"error": str(e)}), 500