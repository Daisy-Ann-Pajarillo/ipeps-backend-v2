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

        job_posting = EmployerJobPosting.query.filter_by(user_id = uid).first()
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

@employer.route('/get-job-postings', methods=['GET'])
# @auth.login_required  # Uncomment if authentication is required
def get_job_postings():
    uid = 8  # For testing purposes
    try:
        # Query the database for all job postings associated with the given user_id
        job_postings = EmployerJobPosting.query.filter_by(user_id=uid).all()

        if not job_postings:
            return jsonify({"error": "No job postings found for this user"}), 404

        # Serialize the job postings into a list of dictionaries
        job_postings_data = [
            {
                "job_title": job.job_title,
                "job_type": job.job_type,
                "experience_level": job.experience_level,
                "job_description": job.job_description,
                "estimated_salary_from": job.estimated_salary_from,
                "estimated_salary_to": job.estimated_salary_to,
                "no_of_vacancies": job.no_of_vacancies,
                "country": job.country,
                "city_municipality": job.city_municipality,
                "other_skills": job.other_skills,
                "course_name": job.course_name,
                "training_institution": job.training_institution,
                "certificate_received": job.certificate_received,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
            for job in job_postings
        ]

        return jsonify({
            "success": True,
            "job_postings": job_postings_data
            }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500