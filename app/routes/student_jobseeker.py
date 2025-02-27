from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, StudentJobseekerSavedJobs, EmployerJobPosting, StudentJobseekerApplyJobs
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
    uid = 2  # Replace with actual user ID from authentication later
    try:
        # Parse JSON data from the request
        data = request.get_json()
        employer_jobpost_id = data.get('employer_jobpost_id')
        status = data.get('status', 'pending')

        # Validate required fields
        if not uid or not employer_jobpost_id:
            return jsonify({"error": "Missing required field: 'employer_jobpost_id'"}), 400

        # Check if the saved job already exists for the user
        existing_saved_job = StudentJobseekerSavedJobs.query.filter_by(
            user_id=uid,
            employer_jobpost_id=employer_jobpost_id
        ).first()

        if existing_saved_job:
            # If the job already exists, remove it
            db.session.delete(existing_saved_job)
            db.session.commit()
            return jsonify({
                "message": "Saved job removed successfully",
            }), 200
        else:
            # If the job does not exist, create a new saved job entry
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
    

# ==================================
# Apply Jobs
# ==================================

@student_jobseeker.route('/apply-jobs', methods=['POST'])
# @auth.login_required
def apply_jobs():
    """
    Route for students to apply for a job
    Requires authentication
    """
    uid = 1 # for testing
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    if 'employer_jobpost_id' not in data:
        return jsonify({"error": "Job posting ID is required"}), 400
    
    # Check if job posting exists
    job_posting = EmployerJobPosting.query.get(data['employer_jobpost_id'])
    if not job_posting:
        return jsonify({"error": "Job posting not found"}), 404
    
    # Check if user already applied for this job
    existing_application = StudentJobseekerApplyJobs.query.filter_by(
        user_id=uid,
        employer_jobpost_id=data['employer_jobpost_id']
    ).first()
    
    if existing_application:
        return jsonify({"error": "You have already applied for this job"}), 400
    
    # Create new job application
    new_application = StudentJobseekerApplyJobs(
        user_id=uid,
        employer_jobpost_id=data['employer_jobpost_id']
    )
    
    try:
        db.session.add(new_application)
        db.session.commit()
        
        return jsonify({
            "message": "Application submitted successfully",
            "application_id": new_application.apply_job_id
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
        
@student_jobseeker.route('/get-applied-jobs', methods=['GET'])
# @auth.login_required
def get_applied_jobs():
    """
    Route for students to retrieve all jobs they have applied for.
    Requires authentication.
    """
    # Replace this with the actual user ID from authentication
    uid = 1  # For testing purposes

    try:
        # Query the database for all job applications by the current user
        applied_jobs = (
            db.session.query(
                StudentJobseekerApplyJobs,
                EmployerJobPosting
            )
            .join(
                EmployerJobPosting,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(
                StudentJobseekerApplyJobs.user_id == uid
            )
            .order_by(StudentJobseekerApplyJobs.created_at.desc())  # Order by most recent applications
            .all()
        )

        if not applied_jobs:
            return jsonify({"message": "No job applications found"}), 200

        # Serialize the results
        result = []
        for application, job_posting in applied_jobs:
            result.append({
                "user_id": uid,
                "job_posting_id": application.employer_jobpost_id,
                "job_title": job_posting.job_title if job_posting else None,  # Safely access job title
                "job_type": job_posting.job_type if job_posting else None,  # Safely access job type
                "experience_level": job_posting.experience_level if job_posting else None,  # Safely access experience level
                "job_description": job_posting.job_description if job_posting else None,  # Safely access job description
                "estimated_salary_from": job_posting.estimated_salary_from if job_posting else None,  # Safely access salary range
                "estimated_salary_to": job_posting.estimated_salary_to if job_posting else None,  # Safely access salary range
                "country": job_posting.country if job_posting else None,  # Safely access country
                "city_municipality": job_posting.city_municipality if job_posting else None,  # Safely access city/municipality
                "status": application.status,  # Application status
                "applied_at": application.created_at.strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp of application
                "updated_at": application.updated_at.strftime("%Y-%m-%d %H:%M:%S")  # Last updated timestamp
            })

        return jsonify({
            "message": "Job applications retrieved successfully",
            "applications": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
