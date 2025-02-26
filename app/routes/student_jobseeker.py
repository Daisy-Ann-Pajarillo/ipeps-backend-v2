from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, StudentJobseekerSavedJobs, EmployerJobPosting
from sqlalchemy.exc import IntegrityError

auth = HTTPBasicAuth()

student_jobseeker = Blueprint("student_jobseeker", __name__)

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

@student_jobseeker.route('/saved-jobs', methods=['POST'])
# @auth.login_required
def add_saved_job():
    uid = 2
    try:
        # Parse JSON data from the request
        data = request.get_json()
        employer_jobpost_id = data.get('employer_jobpost_id')
        status = data.get('status', 'null')  # Default status is 'null'

        # Validate required fields
        if not uid or not employer_jobpost_id:
            return jsonify({"error": "Missing required field: 'employer_jobpost_id'"}), 400

        # Create a new saved job entry
        new_saved_job = StudentJobseekerSavedJobs(
            user_id=uid,
            employer_jobpost_id=employer_jobpost_id,
            status=status
        )

        # Add to the database
        db.session.add(new_saved_job)
        db.session.commit()

        # Return success response
        return jsonify({
            "message": "Saved job added successfully",
            "saved_job_id": new_saved_job.saved_job_id
        }), 201

    except IntegrityError as e:
        # Handle database integrity errors (e.g., foreign key violations)
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 400
    except Exception as e:
        # Handle other exceptions
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@student_jobseeker.route('/get-saved-jobs', methods=['GET'])
# @auth.login_required
def get_saved_jobs():
    """
    Route to retrieve all saved jobs for a specific user, including details from EmployerJobPosting.
    """
    uid = 2  # For testing purposes; replace with actual user ID from authentication later
    try:
        # Query the database for saved jobs associated with the given user_id
        saved_jobs = db.session.query(
            StudentJobseekerSavedJobs,
            EmployerJobPosting
        ).join(
            EmployerJobPosting,
            StudentJobseekerSavedJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        ).filter(
            StudentJobseekerSavedJobs.user_id == uid
        ).all()

        # Format the results
        result = []
        for saved_job, job_post in saved_jobs:
            result.append({
                "saved_job_id": saved_job.saved_job_id,
                "user_id": saved_job.user_id,
                "employer_jobpost_id": saved_job.employer_jobpost_id,
                "job_title": job_post.job_title,
                "job_type": job_post.job_type,
                "experience_level": job_post.experience_level,
                "job_description": job_post.job_description,
                "estimated_salary_from": job_post.estimated_salary_from,
                "estimated_salary_to": job_post.estimated_salary_to,
                "no_of_vacancies": job_post.no_of_vacancies,
                "country": job_post.country,
                "city_municipality": job_post.city_municipality,
                "other_skills": job_post.other_skills,
                "course_name": job_post.course_name,
                "training_institution": job_post.training_institution,
                "certificate_received": job_post.certificate_received,
                "status": saved_job.status,
            })

        # Return the list of saved jobs
        return jsonify(result), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500