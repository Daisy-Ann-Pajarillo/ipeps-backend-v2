from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, EmployerJobPosting


auth = HTTPBasicAuth()

employer = Blueprint("employer", __name__)

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

@employer.route('/job-postings', methods=['POST'])
# @auth.login_required
def create_job_posting():
    """
    Route to create a new job posting.
    Expects JSON input with the required fields.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()

        uid = 8 # for testing

        # Validate required fields
        required_fields = [
            'job_title', 'job_type', 'job_description',
            'no_of_vacancies', 'country', 'city_municipality'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        job_posting = EmployerJobPosting.query.filter_by(user)
        # Create a new EmployerJobPosting instance
        new_job_posting = EmployerJobPosting(
            user_id= uid,
            job_title=data['job_title'],
            job_type=data['job_type'],
            experience_level=data.get('experience_level'),
            job_description=data['job_description'],
            estimated_salary_from=data.get('estimated_salary_from'),
            estimated_salary_to=data.get('estimated_salary_to'),
            no_of_vacancies=data['no_of_vacancies'],
            country=data['country'],
            city_municipality=data['city_municipality'],
            other_skills=data.get('other_skills'),
            course_name=data.get('course_name'),
            training_institution=data.get('training_institution'),
            certificate_received=data.get('certificate_received'),
            status=data.get('status', 'pending')  # Default status is 'pending'
        )

        # Add and commit to the database
        db.session.add(new_job_posting)
        db.session.commit()

        # Return success response
        return jsonify({
            "message": "Job posting created successfully",
            "job_posting_id": new_job_posting.id
        }), 201

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

