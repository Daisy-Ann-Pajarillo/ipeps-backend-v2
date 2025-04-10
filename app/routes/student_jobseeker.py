from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, StudentJobseekerSavedJobs, EmployerJobPosting, EmployerTrainingPosting, StudentJobseekerApplyJobs, EmployerScholarshipPosting, StudentJobseekerSavedScholarships, StudentJobseekerApplyScholarships, StudentJobseekerApplyTrainings, StudentJobseekerSavedTrainings, EmployerPersonalInformation
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.utils import get_user_data, exclude_fields, convert_dates

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

# ========================================================================================================================================
#   SAVED JOBS
# ========================================================================================================================================
@student_jobseeker.route('/saved-jobs', methods=['POST'])
@auth.login_required
def add_saved_job():
    uid = g.user.user_id  # Replace with actual user ID from authentication later
    try:
        # Parse JSON data from the request
        data = request.get_json()
        employer_jobpost_id = data.get('employer_jobpost_id')
        status = data.get('status', 'pending')

        if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
            return jsonify({"error": "Unauthorized user type"}), 403

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
                "is_saved": False,
                "message": "Unsave job successfully",
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
                "is_saved": True,
                "message": "Saved job successfully",
            }), 201

    except IntegrityError as e:
        # Handle database integrity errors (e.g., foreign key violations)
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 400
    except Exception as e:
        # Handle other exceptions
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@student_jobseeker.route('/get-saved-jobs', methods=['GET'])
@auth.login_required
def get_saved_jobs():
    """
    Route to retrieve all saved jobs for a specific user, including details from EmployerJobPosting.
    """
    uid = g.user.user_id  # For testing purposes; replace with actual user ID from authentication later
    try:

        # Query the database for saved jobs associated with the given user_id
        saved_jobs = db.session.query(
            StudentJobseekerSavedJobs,
            EmployerJobPosting,
            EmployerPersonalInformation
        ).join(
            EmployerJobPosting,
            StudentJobseekerSavedJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        ).join(
            EmployerPersonalInformation,
            EmployerJobPosting.user_id == EmployerPersonalInformation.user_id
        ).filter(
            StudentJobseekerSavedJobs.user_id == uid
        ).all()

        if not saved_jobs:
            return jsonify({"message": "No saved jobs found"}), 404
        
        result = []
        for saved_job, job_post, employer in saved_jobs:
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
                "created_at": saved_job.created_at,
                "expiration_date": job_post.expiration_date,
                "employer": {
                    "user_id": employer.user_id,
                    "prefix": employer.prefix,
                    "first_name": employer.first_name,
                    "middle_name": employer.middle_name,
                    "last_name": employer.last_name,
                    "suffix": employer.suffix,
                    "company_name": employer.company_name,
                    "email": employer.email,
                    "company_name": getattr(employer, 'company_name', None),
                }
            })

        # Return the list of saved jobs
        return jsonify({
            "success": True,
            "message": "Saved jobs retrieved successfully",
            "jobs": result
        }), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@student_jobseeker.route('/check-already-saved', methods=['POST'])
@auth.login_required
def check_saved_job():
    """
    Route to check if a job is already saved by the user.
    Query parameter:
    - employer_jobpost_id: ID of the job posting
    
    Returns:
    - is_saved: boolean indicating if the job is saved
    """
    data = request.get_json()
    uid = g.user.user_id
    employer_jobpost_id = data.get('employer_jobpost_id')
    
    # Validate required parameter
    if not employer_jobpost_id:
        return jsonify({
            "success": False,
            "error": "Missing required parameter: 'employer_jobpost_id'"
        }), 400
    try:
        # Check if the job is saved
        saved_job = StudentJobseekerSavedJobs.query.filter_by(
            user_id=uid,
            employer_jobpost_id=employer_jobpost_id
        ).first()
        
        if saved_job:
            # Return the result
            return jsonify({
                "is_saved": saved_job is not None
            }), 200
        else:
            return jsonify({
                "is_saved": False
            }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

# ========================================================================================================================================
#   SAVED TRAININGS
# ========================================================================================================================================
@student_jobseeker.route('/save-training', methods=['POST'])
@auth.login_required
def save_training():
    uid = g.user.user_id  # Replace with actual user ID from authentication later
    try:
        # Parse JSON data from the request
        data = request.get_json()
        employer_trainingpost_id = data.get('employer_trainingpost_id')
        status = data.get('status', 'pending')

        if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
            return jsonify({"error": "Unauthorized user type"}), 403

        if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
            return jsonify({"error": "Unauthorized user type"}), 403

        # Validate required fields
        if not uid or not employer_trainingpost_id:
            return jsonify({"error": "Missing required field: 'employer_trainingpost_id'"}), 400

        # Check if the training posting exists
        training_posting = EmployerTrainingPosting.query.get(employer_trainingpost_id)
        if not training_posting:
            return jsonify({"error": "Training posting not found"}), 404

        # Check if the saved training already exists for the user
        existing_saved_training = StudentJobseekerSavedTrainings.query.filter_by(
            user_id=uid,
            employer_trainingpost_id=employer_trainingpost_id
        ).first()

        if existing_saved_training:
            # If the training already exists, remove it
            db.session.delete(existing_saved_training)
            db.session.commit()
            return jsonify({
                "message": "Saved training removed successfully",
            }), 200
        else:
            # If the training does not exist, create a new saved training entry
            new_saved_training = StudentJobseekerSavedTrainings(
                user_id=uid,
                employer_trainingpost_id=employer_trainingpost_id,
                status=status
            )
            # Add to the database
            db.session.add(new_saved_training)
            db.session.commit()
            # Return success response
            return jsonify({
                "message": "Training saved successfully",
                "saved_training_id": new_saved_training.saved_training_id
            }), 201

    except IntegrityError as e:
        # Handle database integrity errors (e.g., foreign key violations)
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 400
    except Exception as e:
        # Handle other exceptions
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@student_jobseeker.route('/get-saved-trainings', methods=['GET'])
@auth.login_required
def get_saved_trainings():
    """
    Route to retrieve all saved trainings for a specific user.
    Uses the relationship defined in the models to simplify the query.
    """
    uid = g.user.user_id # For testing purposes; replace with actual user ID from authentication later
    try:
        # Query the database for saved trainings associated with the given user_id
        saved_trainings = (
            StudentJobseekerSavedTrainings.query
            .filter_by(user_id=uid)
            .order_by(StudentJobseekerSavedTrainings.status.asc())
            .all()
        )

        if not saved_trainings:
            return jsonify({
                "success": False,
                "message": "No saved trainings found",
                "trainings": []
            }), 200

        # Format the results using the relationship
        result = []
        for saved_training in saved_trainings:
            # Access the related training posting through the relationship
            training_post = saved_training.user_saved_trainings
            
            # Only include the training in the result if it exists
            if training_post:
                result.append({
                    "saved_training_id": saved_training.saved_training_id,
                    "user_id": saved_training.user_id,
                    "employer_trainingpost_id": saved_training.employer_trainingpost_id,
                    "training_title": training_post.training_title,
                    "training_description": training_post.training_description,
                    "status": saved_training.status,
                    "created_at": saved_training.created_at.strftime('%Y-%m-%d') if saved_training.created_at else None,
                    "expiration_date": training_post.expiration_date.strftime('%Y-%m-%d') if training_post.expiration_date else None
                })

        # Return the list of saved trainings
        return jsonify({
            "success": True,
            "message": "Saved trainings retrieved successfully",
            "trainings": result
        }), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

# ========================================================================================================================================
#   SAVED SCHOLARSHIPS
# ========================================================================================================================================
@student_jobseeker.route('/save-scholarship', methods=['POST'])
@auth.login_required
def save_scholarship():
    """
    Route for students to save a scholarship.
    Requires authentication.
    """
    uid = g.user.user_id  # for testing purposes; replace with actual user ID from authentication

    # Get request data
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
        return jsonify({"error": "Unauthorized user type"}), 403

    # Validate required fields
    if 'employer_scholarshippost_id' not in data:
        return jsonify({"error": "Scholarship posting ID is required"}), 400

    # Check if scholarship posting exists
    scholarship_posting = EmployerScholarshipPosting.query.get(data['employer_scholarshippost_id'])
    if not scholarship_posting:
        return jsonify({"error": "Scholarship posting not found"}), 404

    # Check if user already saved this scholarship
    existing_save_scholarship = StudentJobseekerSavedScholarships.query.filter_by(
        user_id=uid,
        employer_scholarshippost_id=data['employer_scholarshippost_id']
    ).first()

    if existing_save_scholarship:
            # If the job already exists, remove it
        db.session.delete(existing_save_scholarship)
        db.session.commit()
        return jsonify({
            "message": "Saved scholarship removed successfully",
    }), 200
    else:
        # Create new saved scholarship entry
        new_save = StudentJobseekerSavedScholarships(
            user_id=uid,
            employer_scholarshippost_id=data['employer_scholarshippost_id'],
            status='pending'  # Set initial status
        )

    try:
        db.session.add(new_save)
        db.session.commit()

        return jsonify({
            "message": "Scholarship saved successfully",
            "saved_scholarship_id": new_save.saved_scholarship_id
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

@student_jobseeker.route('/get-saved-scholarships', methods=['GET'])
@auth.login_required
def get_saved_scholarships():
    """
    Route for students to retrieve all saved scholarships.
    Requires authentication.
    """
    uid = g.user.user_id  # for testing purposes; replace with actual user ID from authentication

    try:
        # Query the database for all saved scholarships by the current user
        saved_scholarships = (
            StudentJobseekerSavedScholarships.query
            .filter_by(user_id=uid)
            .order_by(StudentJobseekerSavedScholarships.status.asc())  # Order by status (e.g., pending first)
            .all()
        )

        if not saved_scholarships:
            return jsonify({"message": "No saved scholarships found"}), 200

        # Serialize the results
        result = []
        for saved in saved_scholarships:
            scholarship_posting = saved.user_saved_scholarships  # Access the related EmployerScholarshipPosting
            result.append({
                "saved_scholarship_id": saved.saved_scholarship_id,
                "scholarship_posting_id": saved.employer_scholarshippost_id,
                "scholarship_title": scholarship_posting.scholarship_title if scholarship_posting else None,  # Fixed field name
                "scholarship_description": scholarship_posting.scholarship_description if scholarship_posting else None,
                "status": saved.status
            })

        return jsonify({
            "success": True,
            "message": "Saved scholarships retrieved successfully",
            "scholarships": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# ==============================================================================================================================================================================================================================================
# ========================================================================================================================================
#   APPLY JOBS - CRUD Operations
# ========================================================================================================================================

# CREATE - Apply for a job
@student_jobseeker.route('/apply-job', methods=['POST'])
@auth.login_required
def apply_for_job():
    """
    Route for students to apply for a job.
    Requires authentication.
    """
    uid = g.user.user_id  # for testing; replace with actual user ID from authentication
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
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
        return jsonify({
            "is_applied": True,
            "message": "You have already applied for this job"
            }), 409
    
    # Create new job application
    new_application = StudentJobseekerApplyJobs(
        user_id=uid,
        employer_jobpost_id=data['employer_jobpost_id'],
        status=data.get('status', 'pending')  # Use provided status or default to 'pending'
    )
    
    try:
        db.session.add(new_application)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Application submitted successfully",
            "application_id": new_application.apply_job_id
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# READ - Get all applied jobs
@student_jobseeker.route('/get-applied-jobs', methods=['GET'])
@auth.login_required
def get_applied_jobs():
    """
    Route for students to retrieve all jobs they have applied for.
    Requires authentication.
    """
    # Get current user ID from auth
    uid = g.user.user_id
    
    # Get query parameters for filtering
    status = request.args.get('status')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    try:
        # Start building the query
        query = StudentJobseekerApplyJobs.query.filter_by(user_id=uid)
        
        # Apply status filter if provided
        if status:
            query = query.filter_by(status=status)
        
        # Apply sorting
        if sort_order.lower() == 'asc':
            query = query.order_by(getattr(StudentJobseekerApplyJobs, sort_by).asc())
        else:
            query = query.order_by(getattr(StudentJobseekerApplyJobs, sort_by).desc())
        
        # Execute query
        applications = query.all()
        
        if not applications:
            return jsonify({
                "success": True,
                "message": "No job applications found",
                "applications": []
            }), 200
            
        # Serialize the results
        result = []
        for application in applications:
            # Get the related job posting using the relationship
            job_posting = application.user_apply_job
            
            if job_posting:
                # Get employer details if available
                employer_name = job_posting.employer.company_name if hasattr(job_posting, 'employer') and job_posting.employer else "Unknown Company"
                
                result.append({
                    "application_id": application.apply_job_id,
                    "job_posting_id": application.employer_jobpost_id,
                    "job_title": job_posting.job_title,
                    "company_name": employer_name,
                    "job_type": job_posting.job_type,
                    "experience_level": job_posting.experience_level,
                    "job_description": job_posting.job_description,
                    "estimated_salary_from": job_posting.estimated_salary_from,
                    "estimated_salary_to": job_posting.estimated_salary_to,
                    "country": job_posting.country,
                    "city_municipality": job_posting.city_municipality,
                    "status": application.status,
                    "job_status": job_posting.status if hasattr(job_posting, 'status') else None,
                    "applied_at": application.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": application.updated_at.strftime("%Y-%m-%d %H:%M:%S") if application.updated_at else None
                })
                
        return jsonify({
            "success": True,
            "message": "Applied jobs retrieved successfully",
            "count": len(result),
            "applications": result
        }), 200
        
    except SQLAlchemyError as e:
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

@student_jobseeker.route('/check-already-applied', methods=['POST'])
@auth.login_required
def check_already_applied():
    """
    Route to check if a student has already applied for a specific job.
    Returns true/false and application details if found.
    
    Expected JSON body: {"job_id": 1}
    """
    try:
        uid = g.user.user_id  # for testing; replace with actual user ID from authentication
        
        # Get data from JSON body
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Check if job_id is in the request data
        if 'job_id' not in data:
            return jsonify({"error": "Job ID is required"}), 400
        
        job_id = data['job_id']
        
        # Check if job posting exists
        job_posting = EmployerJobPosting.query.get(job_id)
        if not job_posting:
            return jsonify({"error": "Job posting not found"}), 404
        
        # Check if user already applied for this job
        existing_application = StudentJobseekerApplyJobs.query.filter_by(
            user_id=uid,
            employer_jobpost_id=job_id
        ).first()
        
        if existing_application:
            # User has already applied, return application details
            return jsonify({
                "success": True,
                "already_applied": True
            }), 200
        else:
            # User has not yet applied
            return jsonify({
                "success": True,
                "already_applied": False
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# # UPDATE - Update job application status
# @student_jobseeker.route('/applied-job/<int:application_id>', methods=['PUT'])
# @auth.login_required
# def update_job_application(application_id):
#     """
#     Route to update a job application's status.
#     Requires authentication.
#     """

#     uid = 1 # for testing
    
#     # Get request data
#     data = request.get_json()
    
#     if not data:
#         return jsonify({"error": "No data provided"}), 400
        
#     try:
#         # Find the application
#         application = StudentJobseekerApplyJobs.query.get(application_id)
        
#         if not application:
#             return jsonify({"error": "Application not found"}), 404
            
#         # Check if application belongs to the current user
#         if application.user_id != uid:
#             return jsonify({"error": "Unauthorized access"}), 403
            
#         # Get the related job posting
#         job_posting = application.user_apply_job
        
#         # Check if job posting is still active before allowing updates
#         if job_posting and hasattr(job_posting, 'status') and job_posting.status != 'active':
#             # Cannot update application for inactive jobs
#             return jsonify({"error": "This job is no longer active and cannot be updated"}), 400
        
#         # Update fields if provided
#         if 'status' in data:
#             # Validate that status is one of the allowed enum values
#             allowed_statuses = ['pending', 'approved', 'declined', 'applied']
#             if data['status'] not in allowed_statuses:
#                 return jsonify({"error": f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"}), 400
                
#             # Create notification for status change
#             old_status = application.status
#             application.status = data['status']
            
#             # Log status change
#             if old_status != data['status']:
#                 job_title = job_posting.job_title if job_posting else "a job"
#                 print(f"User {uid} changed application status for {job_title} from {old_status} to {data['status']}")
            
#         # Save changes
#         db.session.commit()
        
#         return jsonify({
#             "success": True,
#             "message": "Application updated successfully",
#             "application_id": application.apply_job_id,
#             "status": application.status
#         }), 200
        
#     except SQLAlchemyError as e:
#         db.session.rollback()
#         return jsonify({"error": "Database error occurred", "details": str(e)}), 500


# # DELETE - Withdraw job application
# @student_jobseeker.route('/applied-job/<int:application_id>', methods=['DELETE'])
# @auth.login_required
# def withdraw_job_application(application_id):
#     """
#     Route to withdraw/delete a job application.
#     Requires authentication.
#     """
#     # Get current user ID from auth
#     uid = 1 # for testing
    
#     try:
#         # Find the application
#         application = StudentJobseekerApplyJobs.query.get(application_id)
        
#         if not application:
#             return jsonify({"error": "Application not found"}), 404
            
#         # Check if application belongs to the current user
#         if application.user_id != uid:
#             return jsonify({"error": "Unauthorized access"}), 403
        
#         # Get job details for notification before deletion
#         job_title = "Unknown"
#         job_posting = application.user_apply_job
#         if job_posting:
#             job_title = job_posting.job_title
        
#         # Delete the application
#         db.session.delete(application)
        
#         # Log application deletion for auditing
#         print(f"User {uid} deleted application {application_id} for job {job_title}")
            
#         db.session.commit()
        
#         return jsonify({
#             "success": True,
#             "message": "Application withdrawn successfully"
#         }), 200
        
#     except SQLAlchemyError as e:
#         db.session.rollback()
#         return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# ========================================================================================================================================
#   APPLY SCHOLARSHIPS
# ========================================================================================================================================
@student_jobseeker.route('/apply-scholarships', methods=['POST'])
@auth.login_required
def apply_scholarships():
    """
    Route for students to apply for a scholarship
    Requires authentication
    """
    uid = g.user.user_id # for testing
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    # Validate required fields
    if 'employer_scholarshippost_id' not in data:
        return jsonify({"error": "Scholarship posting ID is required"}), 400
    
    # Check if scholarship posting exists
    scholarship_posting = EmployerScholarshipPosting.query.get(data['employer_scholarshippost_id'])
    if not scholarship_posting:
        return jsonify({"error": "Scholarship posting not found"}), 404
    
    # Check if user already applied for this scholarship
    existing_application = StudentJobseekerApplyScholarships.query.filter_by(
        user_id=uid,
        employer_scholarshippost_id=data['employer_scholarshippost_id']
    ).first()
    
    if existing_application:
        return jsonify({"error": "You have already applied for this scholarship"}), 400
    
    # Create new scholarship application
    new_application = StudentJobseekerApplyScholarships(
        user_id=uid,
        employer_scholarshippost_id=data['employer_scholarshippost_id']
    )
    
    try:
        db.session.add(new_application)
        db.session.commit()
        
        return jsonify({
            "message": "Scholarship application submitted successfully",
            "application_id": new_application.apply_scholarship_id
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

@student_jobseeker.route('/get-applied-scholarships', methods=['GET'])
@auth.login_required
def get_applied_scholarships():
    """
    Route for students to retrieve all scholarships they have applied for.
    Requires authentication.
    """
    # Replace this with the actual user ID from authentication
    uid = g.user.user_id  # For testing purposes
    
    # Get query parameters for filtering
    status = request.args.get('status')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    try:
        # Build query using the relationship approach instead of join
        query = StudentJobseekerApplyScholarships.query.filter_by(user_id=uid)
        
        # Apply status filter if provided
        if status:
            query = query.filter_by(status=status)
        
        # Apply sorting
        if sort_order.lower() == 'asc':
            query = query.order_by(getattr(StudentJobseekerApplyScholarships, sort_by).asc())
        else:
            query = query.order_by(getattr(StudentJobseekerApplyScholarships, sort_by).desc())
        
        # Execute query
        applications = query.all()

        if not applications:
            return jsonify({
                "success": True, 
                "message": "No scholarship applications found",
                "applications": []
            }), 200

        # Serialize the results
        result = []
        for application in applications:
            # Get the related scholarship posting using the relationship
            scholarship_posting = application.user_apply_scholarships
            
            if scholarship_posting:
                # Get employer details if available
                employer_name = "Unknown Company"
                if hasattr(scholarship_posting, 'user') and scholarship_posting.user:
                    if hasattr(scholarship_posting.user, 'company_name'):
                        employer_name = scholarship_posting.user.company_name
                
                result.append({
                    "application_id": application.apply_scholarship_id,
                    "user_id": uid,
                    "scholarship_posting_id": application.employer_scholarshippost_id,
                    "scholarship_title": scholarship_posting.scholarship_title,
                    "company_name": employer_name,
                    "scholarship_description": scholarship_posting.scholarship_description,
                    "status": application.status,
                    "scholarship_status": scholarship_posting.status,
                    "applied_at": application.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": application.updated_at.strftime("%Y-%m-%d %H:%M:%S") if application.updated_at else None
                })

        return jsonify({
            "success": True,
            "message": "Scholarship applications retrieved successfully",
            "count": len(result),
            "applications": result
        }), 200

    except SQLAlchemyError as e:
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# ========================================================================================================================================
#   APPLY TRAININGS
# ========================================================================================================================================
# Apply for a training
@student_jobseeker.route('/apply-training', methods=['POST'])
@auth.login_required
def apply_for_training():
    """
    Route for students to apply for a training.
    Requires authentication.
    """
    uid = g.user.user_id  # For testing; replace with actual user ID from authentication
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if g.user.user_type not in ['STUDENT', 'JOBSEEKER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    # Validate required fields
    if 'employer_trainingpost_id' not in data:
        return jsonify({"error": "Training posting ID is required"}), 400
    
    # Check if training posting exists
    training_posting = EmployerTrainingPosting.query.get(data['employer_trainingpost_id'])
    if not training_posting:
        return jsonify({"error": "Training posting not found"}), 404
    
    # Check if training posting is still open for applications
    if training_posting.status != 'active':
        return jsonify({"error": "This training is no longer accepting applications"}), 400
    
    # Check if user already applied for this training
    existing_application = StudentJobseekerApplyTrainings.query.filter_by(
        user_id=uid,
        employer_trainingpost_id=data['employer_trainingpost_id']
    ).first()
    
    if existing_application:
        return jsonify(
            {
                "message": "You have already applied for this training",
                "is_applied": True
            }
            ), 400
    
    # Create new training application
    new_application = StudentJobseekerApplyTrainings(
        user_id=uid,
        employer_trainingpost_id=data['employer_trainingpost_id'],
        status='applied'  # Set default status to 'applied' rather than 'pending'
    )
    
    try:
        db.session.add(new_application)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Training application submitted successfully",
            "application_id": new_application.apply_training_id,
            "training_title": training_posting.training_title
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# Get all applied trainings
@student_jobseeker.route('/get-applied-trainings', methods=['GET'])
@auth.login_required
def get_applied_trainings():
    """
    Route for students to retrieve all trainings they have applied for.
    Requires authentication.
    """
    # Replace this with the actual user ID from authentication
    uid = g.user.user_id  # For testing purposes
    
    # Get query parameters for filtering
    status = request.args.get('status')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    try:
        # Build query using the relationship approach instead of join
        query = StudentJobseekerApplyTrainings.query.filter_by(user_id=uid)
        
        # Apply status filter if provided
        if status:
            query = query.filter_by(status=status)
        
        # Apply sorting
        if sort_order.lower() == 'asc':
            query = query.order_by(getattr(StudentJobseekerApplyTrainings, sort_by).asc())
        else:
            query = query.order_by(getattr(StudentJobseekerApplyTrainings, sort_by).desc())
        
        # Execute query
        applications = query.all()

        if not applications:
            return jsonify({
                "success": True, 
                "message": "No training applications found",
                "applications": []
            }), 200

        # Serialize the results
        result = []
        for application in applications:
            # Get the related training posting using the relationship
            training_posting = application.user_apply_trainings
            
            if training_posting:
                # Get employer details if available
                employer_name = "Unknown Company"
                if hasattr(training_posting, 'user') and training_posting.user:
                    if hasattr(training_posting.user, 'company_name'):
                        employer_name = training_posting.user.company_name
                
                result.append({
                    "application_id": application.apply_training_id,
                    "user_id": uid,
                    "training_posting_id": application.employer_trainingpost_id,
                    "training_title": training_posting.training_title,
                    "company_name": employer_name,
                    "training_description": training_posting.training_description,
                    "status": application.status,
                    "training_status": training_posting.status,
                    "applied_at": application.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": application.updated_at.strftime("%Y-%m-%d %H:%M:%S") if application.updated_at else None
                })

        return jsonify({
            "success": True,
            "message": "Applied trainings retrieved successfully",
            "count": len(result),
            "applications": result
        }), 200

    except SQLAlchemyError as e:
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# ========================================================================================================================================
#   CHECK TRAINING STATUS (SAVED AND APPLIED)
# ========================================================================================================================================
@student_jobseeker.route('/check-training-status', methods=['POST'])
@auth.login_required
def check_training_status():
    """
    Route to check if a user has already saved or applied for a specific training.
    
    Expected JSON body: {"employer_trainingpost_id": 1}
    Returns: is_saved and is_applied status
    """
    uid = g.user.user_id
    
    # Get data from JSON body
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # Check if training ID is in the request data
    if 'employer_trainingpost_id' not in data:
        return jsonify({"error": "Training posting ID is required"}), 400
    
    training_id = data['employer_trainingpost_id']
    
    # Check if training posting exists
    training_posting = EmployerTrainingPosting.query.get(training_id)
    if not training_posting:
        return jsonify({"error": "Training posting not found"}), 404
    
    try:
        # Check if user already saved this training
        saved_training = StudentJobseekerSavedTrainings.query.filter_by(
            user_id=uid,
            employer_trainingpost_id=training_id
        ).first()
        
        # Check if user already applied for this training
        applied_training = StudentJobseekerApplyTrainings.query.filter_by(
            user_id=uid,
            employer_trainingpost_id=training_id
        ).first()
        
        return jsonify({
            "success": True,
            "is_saved": saved_training is not None,
            "is_applied": applied_training is not None,
            "application_status": applied_training.status if applied_training else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================================================================================================================================
#   CHECK SCHOLARSHIP STATUS (SAVED AND APPLIED)
# ========================================================================================================================================
@student_jobseeker.route('/check-scholarship-status', methods=['POST'])
@auth.login_required
def check_scholarship_status():
    """
    Route to check if a user has already saved or applied for a specific scholarship.
    
    Expected JSON body: {"employer_scholarshippost_id": 1}
    Returns: is_saved and is_applied status
    """
    uid = g.user.user_id
    
    # Get data from JSON body
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # Check if scholarship ID is in the request data
    if 'employer_scholarshippost_id' not in data:
        return jsonify({"error": "Scholarship posting ID is required"}), 400
    
    scholarship_id = data['employer_scholarshippost_id']
    
    # Check if scholarship posting exists
    scholarship_posting = EmployerScholarshipPosting.query.get(scholarship_id)
    if not scholarship_posting:
        return jsonify({"error": "Scholarship posting not found"}), 404
    
    try:
        # Check if user already saved this scholarship
        saved_scholarship = StudentJobseekerSavedScholarships.query.filter_by(
            user_id=uid,
            employer_scholarshippost_id=scholarship_id
        ).first()
        
        # Check if user already applied for this scholarship
        applied_scholarship = StudentJobseekerApplyScholarships.query.filter_by(
            user_id=uid,
            employer_scholarshippost_id=scholarship_id
        ).first()
        
        return jsonify({
            "success": True,
            "is_saved": saved_scholarship is not None,
            "is_applied": applied_scholarship is not None,
            "application_status": applied_scholarship.status if applied_scholarship else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
