from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, EmployerJobPosting, EmployerTrainingPosting, EmployerScholarshipPosting, EmployerPersonalInformation
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings, update_expired_scholarship_postings
from datetime import datetime, timedelta

auth = HTTPBasicAuth()

admin = Blueprint("admin", __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True

@admin.route('/update-posting-status', methods=['PUT'])
@auth.login_required
def update_posting_status():
    """
    Route to update the status of job, scholarship, or training postings.
    Expected JSON format:
    {
        "posting_type": "job|scholarship|training",
        "posting_id": 123,
        "status": "active|inactive|expired"
    }
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['posting_type', 'posting_id', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
                
        # Validate posting type
        valid_posting_types = ['job', 'scholarship', 'training']
        if data['posting_type'] not in valid_posting_types:
            return jsonify({"error": f"Invalid posting type. Must be one of: {', '.join(valid_posting_types)}"}), 400
        
        # Validate status
        valid_statuses = ['active', 'inactive', 'expired']
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}), 400
            
        # Get the posting based on type
        posting = None
        if data['posting_type'] == 'job':
            posting = EmployerJobPosting.query.get(data['posting_id'])
        elif data['posting_type'] == 'scholarship':
            posting = EmployerScholarshipPosting.query.get(data['posting_id'])
        elif data['posting_type'] == 'training':
            posting = EmployerTrainingPosting.query.get(data['posting_id'])
            
        if not posting:
            return jsonify({"error": f"{data['posting_type'].capitalize()} posting with ID {data['posting_id']} not found"}), 404
            
        # Update the status
        posting.status = data['status']
        
        # If status is being set to active, check if the posting has expired
        if data['status'] == 'active' and posting.expiration_date and posting.expiration_date < datetime.utcnow():
            return jsonify({
                "success": False,
                "error": "Cannot set to active as the posting has already expired. Please update the expiration date first."
            }), 400
            
        # Commit the changes
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"{data['posting_type'].capitalize()} posting status updated successfully to '{data['status']}'"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500