from flask import g, Blueprint, request, jsonify
from flask_cors import cross_origin
from app import db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, NoResultFound
from flask_httpauth import HTTPBasicAuth
from app.models import User, EmployerJobPosting, EmployerTrainingPosting, EmployerScholarshipPosting, EmployerPersonalInformation, StudentJobseekerApplyJobs, StudentJobseekerApplyTrainings, StudentJobseekerApplyScholarships, PersonalInformation, EmployerCompanyInformation
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings, update_expired_scholarship_postings
from datetime import datetime, timedelta
from werkzeug.exceptions import BadRequest
import logging

auth = HTTPBasicAuth()

employer = Blueprint("employer", __name__)

logger = logging.getLogger(__name__)

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


# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# EMPLOYER JOB POSTING. POST, GET, PUT, DELETE
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ADD JOB POSTING
@employer.route('/job-postings', methods=['POST'])
@auth.login_required
def create_job_posting():
    """
    Route to create a new job posting.
    Expects JSON input with the required fields.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()

        uid = g.user.user_id # for testing

        company_info = EmployerCompanyInformation.query.filter_by(user_id=uid).first()
        if not company_info:
            return jsonify({"error": "You must complete your company information before posting a job."}), 403
        
        if company_info.status != 'approved':
            return jsonify({"error": "Your company information is pending approval. You cannot post a job until it is approved."}), 403

        # Validate required fields
        required_fields = [
            'job_title', 'job_type', 'job_description',
            'no_of_vacancies', 'country', 'city_municipality'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        job_posting = EmployerJobPosting.query.filter_by(user_id = uid).first()
        
        # Set expiration date (default 30 days from now if not provided)
        expiration_date = None
        if 'expiration_date' in data and data['expiration_date']:
            expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        else:
            expiration_date = datetime.utcnow() + timedelta(days=30)
            
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
            expiration_date=expiration_date
        )

        # Add and commit to the database
        db.session.add(new_job_posting)
        db.session.commit()

        # Return success response
        return jsonify({
            "message": "Job posting created successfully",
            "job_posting_id": new_job_posting.employer_jobpost_id
        }), 201

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET JOB POSTINGS
@employer.route('/get-job-postings', methods=['GET'])
@auth.login_required  # Uncomment if authentication is required
def get_job_postings():
    uid = g.user.user_id  # For testing purposes
    try:
        # Update expired job postings first
        update_expired_job_postings()
        
        # Query the database for all job postings associated with the given user_id
        job_postings = EmployerJobPosting.query.filter_by(user_id=uid).all()
        employer = EmployerPersonalInformation.query.filter_by(user_id=uid).first()

        if not job_postings:
            return jsonify({"error": "No job postings found for this user"}), 404

        # Serialize the job postings into a list of dictionaries
        job_postings_data = [
            {
                "job_id": job.employer_jobpost_id,
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
                "remarks": job.remarks,
                "status": job.status,
                "created_at": job.created_at.strftime('%Y-%m-%d'),
                "updated_at": job.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": job.expiration_date.strftime('%Y-%m-%d') if job.expiration_date else None
            }
            for job in job_postings
        ]

        return jsonify({
            "success": True,
            "employer": exclude_fields(get_user_data(employer, uid)),
            "job_postings": job_postings_data,
            "full_name": employer.first_name + " " + employer.middle_name + " " + employer.last_name if employer else None,
            "employer_id": employer.user_id if employer else None,
            }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# UPDATE JOB POSTING
@employer.route('/job-posting/<int:job_id>', methods=['PUT'])
@auth.login_required
def update_job_posting(job_id):
    """
    Route to update an existing job posting.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        
        # Find the job posting
        job = EmployerJobPosting.query.get(job_id)
        
        if not job:
            return jsonify({"error": "Job posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if job.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Update fields if provided in the request
        if 'job_title' in data:
            job.job_title = data['job_title']
        if 'job_type' in data:
            job.job_type = data['job_type']
        if 'experience_level' in data:
            job.experience_level = data['experience_level']
        if 'job_description' in data:
            job.job_description = data['job_description']
        if 'estimated_salary_from' in data:
            job.estimated_salary_from = data['estimated_salary_from']
        if 'estimated_salary_to' in data:
            job.estimated_salary_to = data['estimated_salary_to']
        if 'no_of_vacancies' in data:
            job.no_of_vacancies = data['no_of_vacancies']
        if 'country' in data:
            job.country = data['country']
        if 'city_municipality' in data:
            job.city_municipality = data['city_municipality']
        if 'other_skills' in data:
            job.other_skills = data['other_skills']
        if 'course_name' in data:
            job.course_name = data['course_name']
        if 'training_institution' in data:
            job.training_institution = data['training_institution']
        if 'certificate_received' in data:
            job.certificate_received = data['certificate_received']
        if 'status' in data:
            job.status = data['status']
        if 'expiration_date' in data and data['expiration_date']:
            job.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        
        # Check if the job should be marked as expired
        if job.expiration_date and job.expiration_date < datetime.utcnow() and job.status != 'expired':
            job.status = 'expired'
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Job posting updated successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# DELETE JOB POSTING
@employer.route('/job-posting/<int:job_id>', methods=['DELETE'])
@auth.login_required
def delete_job_posting(job_id):
    """
    Route to delete a job posting.
    """
    try:
        
        # Find the job posting
        job = EmployerJobPosting.query.get(job_id)
        
        if not job:
            return jsonify({"error": "Job posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if job.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Delete the job posting
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Job posting deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET ALL JOB POSTING
@employer.route('/all-job-postings', methods=['GET'])
@auth.login_required
def get_all_job_postings():
    """
    Route to get all job postings with employer details.
    Returns a list of all active job postings along with the employer information.
    """
    try:
        # Update expired job postings first
        update_expired_job_postings()
        
        # Query all job postings that are not expired (status is not 'expired')
        job_postings = (EmployerJobPosting.query
                        .filter(EmployerJobPosting.status == 'active')
                        .all())
        
        if not job_postings:
            return jsonify({"message": "No active job postings found"}), 404
        
        result = []
        
        # For each job posting, get the employer information and combine them
        for job in job_postings:
            # Get employer information
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=job.user_id).first()
            
            # Skip if employer information is not available
            if not employer_info:
                continue
                
            # Get user information
            user = User.query.get(job.user_id)
            
            if not user:
                continue
            
            # Create a dictionary with job posting and employer details
            job_data = {
                "job_id": job.employer_jobpost_id,
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
                "remarks": job.remarks,
                "status": job.status,
                "created_at": job.created_at.strftime('%Y-%m-%d'),
                "updated_at": job.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": job.expiration_date.strftime('%Y-%m-%d') if job.expiration_date else None,
                "employer":{
                    "full_name": employer_info.first_name + " " + employer_info.middle_name + " " + employer_info.last_name if employer_info else None,
                }
            }
            
            result.append(job_data)
            
        return jsonify({
            "success": True,
            "count": len(result),
            "job_postings": result,
        }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

@employer.route('/get-applied-jobs/<int:job_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
@auth.login_required
def get_job_applicants(job_id):
    """
    Get all applicants for a specific job posting.
    Requires authentication and job must belong to the requesting employer.
    """
    if request.method == 'OPTIONS':
        # Handle preflight request
        return jsonify({"success": True}), 200

    try:
        # Verify job belongs to employer
        job = EmployerJobPosting.query.get(job_id)
        if not job:
            logger.error(f"Job posting not found. Job ID: {job_id}")
            return jsonify({"error": "Job posting not found"}), 404
        if job.user_id != g.user.user_id:
            logger.error(f"Unauthorized access. Job ID: {job_id}, User ID: {g.user.user_id}")
            return jsonify({"error": "Unauthorized access"}), 403

        # Fetch applications for the job
        applications = (StudentJobseekerApplyJobs.query
                        .filter_by(employer_jobpost_id=job_id)
                        .join(User, StudentJobseekerApplyJobs.user_id == User.user_id)
                        .options(db.joinedload(StudentJobseekerApplyJobs.user))
                        .order_by(StudentJobseekerApplyJobs.created_at.desc())
                        .all())

        if not applications:
            logger.info(f"No applications found for Job ID: {job_id}")
            return jsonify({"success": True, "applications": []}), 200

        logger.info(f"Found {len(applications)} applications for Job ID: {job_id}")

        result = []
        for application in applications:
            user = application.user
            if not user:
                logger.warning(f"Skipping application ID {application.apply_job_id} due to missing user data.")
                continue

            personal_info = user.jobseeker_student_personal_information
            if not personal_info:
                logger.warning(f"Skipping application ID {application.apply_job_id} due to missing personal information.")
                continue

            # Serialize applicant data
            result.append({
                "application_id": application.apply_job_id,
                "status": application.status,
                "created_at": application.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "user_details": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "personal_information": personal_info.to_dict(),
                    "job_preference": user.jobseeker_student_job_preference.to_dict() if user.jobseeker_student_job_preference else None,
                    "educational_background": [edu.to_dict() for edu in user.jobseeker_student_educational_background] if user.jobseeker_student_educational_background else [],
                    "trainings": [training.to_dict() for training in user.jobseeker_student_other_training] if user.jobseeker_student_other_training else [],
                    "professional_licenses": [license.to_dict() for license in user.jobseeker_student_professional_license] if user.jobseeker_student_professional_license else [],
                    "work_experiences": [work.to_dict() for work in user.jobseeker_student_work_experience] if user.jobseeker_student_work_experience else [],
                    "other_skills": [skill.to_dict() for skill in user.jobseeker_student_other_skills] if user.jobseeker_student_other_skills else []
                }
            })

        return jsonify({
            "success": True,
            "applications": result
        }), 200

    except Exception as e:
        logger.error(f"Error fetching job applicants for Job ID {job_id}: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Training Posting Routes - POST, GET, PUT, DELETE
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ADD DATA TRAINING POSTING
@employer.route('/training-posting', methods=['POST'])
@auth.login_required  # Uncomment if authentication is required
def create_training_posting():
    """
    Route to create a new training posting.
    Expects JSON input with all relevant fields from the EmployerTrainingPosting model.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = g.user.user_id  # For testing purposes (replace with actual user ID)

        company_info = EmployerCompanyInformation.query.filter_by(user_id=uid).first()
        if not company_info:
            return jsonify({"error": "You must complete your company information before posting a job."}), 403
        
        if company_info.status != 'approved':
            return jsonify({"error": "Your company information is pending approval. You cannot post a job until it is approved."}), 403



        # Validate required fields based on model's nullable=False constraints
        required_fields = [
            'training_title', 
            'training_description'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Set expiration date (default 30 days from now if not provided)
        expiration_date = None
        if 'expiration_date' in data and data['expiration_date']:
            expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        else:
            expiration_date = datetime.utcnow() + timedelta(days=30)

        # Create a new EmployerTrainingPosting instance based on the actual model fields
        new_training_posting = EmployerTrainingPosting(
            user_id=uid,
            training_title=data['training_title'],
            training_description=data['training_description'],
            expiration_date=expiration_date
        )

        # Add and commit to the database
        db.session.add(new_training_posting)
        db.session.commit()

        # Return success response with the created posting's ID
        return jsonify({
            "success": True,
            "message": "Training posting created successfully",
            "training_id": new_training_posting.employer_trainingpost_id
        }), 201
    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# GET TRAINING POSTING AND THE EMPLOYER PERSONAL INFORMATION
@employer.route('/get-training-postings', methods=['GET'])
@auth.login_required
def get_training_postings():
    """
    Route to get all training postings for a user.
    """
    uid = g.user.user_id  # For testing purposes (replace with actual user ID)
    try:
        # Update expired training postings first
        update_expired_training_postings()
        
        # Query the database for all training postings associated with the given user_id
        training_postings = EmployerTrainingPosting.query.filter_by(user_id=uid).all()
        employer = EmployerPersonalInformation.query.filter_by(user_id=uid).first()

        if not training_postings:
            return jsonify({
                "success": False,
                "error": "No training postings found for this user"
                }), 404

        # Serialize the training postings into a list of dictionaries based on actual model fields
        training_postings_data = [
            {
                "training_id": training.employer_trainingpost_id,
                "training_title": training.training_title,
                "training_description": training.training_description,
                "slots": training.slots,
                "occupied_slots": training.occupied_slots,
                "remarks": training.remarks,
                "status": training.status,
                "created_at": training.created_at.strftime('%Y-%m-%d'),
                "updated_at": training.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": training.expiration_date.strftime('%Y-%m-%d') if training.expiration_date else None
            }
            for training in training_postings
        ]

        return jsonify({
            "success": True,
            "employer": exclude_fields(get_user_data(employer, uid)),
            "training_postings": training_postings_data,
            "full_name": employer.first_name + " " + employer.middle_name + " " + employer.last_name if employer else None,
            "employer_id": employer.user_id if employer else None,
        }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# UPDATE TRAINING POSTING
@employer.route('/training-posting/<int:training_id>', methods=['PUT'])
@auth.login_required
def update_training_posting(training_id):
    """
    Route to update an existing training posting.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        
        # Find the training posting
        training = EmployerTrainingPosting.query.get(training_id)
        
        if not training:
            return jsonify({"error": "Training posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if training.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Update fields if provided in the request based on actual model fields
        if 'training_title' in data:
            training.training_title = data['training_title']
        if 'training_description' in data:
            training.training_description = data['training_description']
        if 'status' in data:
            training.status = data['status']
        if 'expiration_date' in data and data['expiration_date']:
            training.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        
        # Check if the training should be marked as expired
        if training.expiration_date and training.expiration_date < datetime.utcnow() and training.status != 'expired':
            training.status = 'expired'
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Training posting updated successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# DELETE TRAINING POSTING
@employer.route('/training-posting/<int:training_id>', methods=['DELETE'])
@auth.login_required
def delete_training_posting(training_id):
    """
    Route to delete a training posting.
    """
    try:
        
        # Find the training posting
        training = EmployerTrainingPosting.query.get(training_id)
        
        if not training:
            return jsonify({"error": "Training posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if training.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Delete the training posting
        db.session.delete(training)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Training posting deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@employer.route('/all-training-postings', methods=['GET'])
@auth.login_required
def get_all_training_postings():
    """
    Route to get all training postings with employer details.
    Returns a list of all active training postings along with the employer information.
    """
    try:
        # Update expired training postings first
        update_expired_training_postings()
        
        # Query all training postings that are not expired (status is not 'expired')
        training_postings = (EmployerTrainingPosting.query
                            .filter(EmployerTrainingPosting.status == 'active')
                            .all())
        employer = EmployerPersonalInformation.query.filter_by(user_id=g.user.user_id).first()
        
        if not training_postings:
            return jsonify({"message": "No active training postings found"}), 404
        
        result = []
        
        # For each training posting, get the employer information and combine them
        for training in training_postings:
            # Get employer information
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=training.user_id).first()
            
            # Skip if employer information is not available
            if not employer_info:
                continue
                
            # Get user information
            user = User.query.get(training.user_id)
            
            if not user:
                continue
            
            # Create a dictionary with training posting and employer details based on actual model fields
            training_data = {
                "training_id": training.employer_trainingpost_id,
                "training_title": training.training_title,
                "training_description": training.training_description,
                "slots": training.slots,
                "occupied_slots": training.occupied_slots,
                "remarks": training.remarks,
                "status": training.status,
                "created_at": training.created_at.strftime('%Y-%m-%d'),
                "updated_at": training.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": training.expiration_date.strftime('%Y-%m-%d') if training.expiration_date else None,
                "employer":{
                    "full_name": employer_info.first_name + " " + employer_info.middle_name + " " + employer_info.last_name if employer_info else None,
                }
            }
            
            result.append(training_data)
        
        return jsonify({
            "success": True,
            "count": len(result),
            "training_postings": result,
        }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500
    
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Scholarship Posting Routes - POST, GET, PUT, DELETE
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ADD DATA SCHOLARSHIP POSTING
@employer.route('/scholarship-posting', methods=['POST'])
@auth.login_required  # Uncomment if authentication is required
def create_scholarship_posting():
    """
    Route to create a new scholarship posting.
    Expects JSON input with all relevant fields from the EmployerScholarshipPosting model.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = g.user.user_id

        company_info = EmployerCompanyInformation.query.filter_by(user_id=uid).first()
        if not company_info:
            return jsonify({"error": "You must complete your company information before posting a job."}), 403
        
        if company_info.status != 'approved':
            return jsonify({"error": "Your company information is pending approval. You cannot post a job until it is approved."}), 403



        # Validate required fields based on model's nullable=False constraints
        required_fields = [
            'scholarship_title', 
            'scholarship_description'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Set expiration date (default 30 days from now if not provided)
        expiration_date = None
        if 'expiration_date' in data and data['expiration_date']:
            expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        else:
            expiration_date = datetime.utcnow() + timedelta(days=30)

        # Create a new EmployerScholarshipPosting instance with the model fields
        new_scholarship_posting = EmployerScholarshipPosting(
            user_id=uid,
            scholarship_title=data['scholarship_title'],
            scholarship_description=data['scholarship_description'],
            expiration_date=expiration_date
        )

        # Add and commit to the database
        db.session.add(new_scholarship_posting)
        db.session.commit()

        # Return success response with the created posting's ID
        return jsonify({
            "success": True,
            "message": "Scholarship posting created successfully",
            "scholarship_id": new_scholarship_posting.employer_scholarshippost_id
        }), 201
    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# GET SCHOLARSHIP POSTINGS
@employer.route('/get-scholarship-postings', methods=['GET'])
@auth.login_required
def get_scholarship_postings():
    """
    Route to get all scholarship postings for a user.
    """
    uid = g.user.user_id  # For testing purposes (replace with actual user ID)
    try:
        # Update expired scholarship postings first (if you have this function)
        update_expired_scholarship_postings()
        
        # Query the database for all scholarship postings associated with the given user_id
        scholarship_postings = EmployerScholarshipPosting.query.filter_by(user_id=uid).all()
        employer = EmployerPersonalInformation.query.filter_by(user_id=uid).first()

        if not scholarship_postings:
            return jsonify({
                "success": False,
                "error": "No scholarship postings found for this user"
                }), 404

        # Serialize the scholarship postings into a list of dictionaries
        scholarship_postings_data = [
            {
                "scholarship_id": scholarship.employer_scholarshippost_id,
                "scholarship_title": scholarship.scholarship_title,
                "scholarship_description": scholarship.scholarship_description,
                "slots": scholarship.slots,
                "occupied_slots": scholarship.occupied_slots,
                "remarks": scholarship.remarks,
                "status": scholarship.status,
                "created_at": scholarship.created_at.strftime('%Y-%m-%d'),
                "updated_at": scholarship.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": scholarship.expiration_date.strftime('%Y-%m-%d') if scholarship.expiration_date else None
            }
            for scholarship in scholarship_postings
        ]

        return jsonify({
            "success": True,
            "employer": exclude_fields(get_user_data(employer, uid)) if employer else None,
            "scholarship_postings": scholarship_postings_data,
            "full_name": employer.first_name + " " + employer.middle_name + " " + employer.last_name if employer else None,
            "employer_id": employer.user_id if employer else None,
        }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# UPDATE SCHOLARSHIP POSTING
@employer.route('/scholarship-posting/<int:scholarship_id>', methods=['PUT'])
@auth.login_required
def update_scholarship_posting(scholarship_id):
    """
    Route to update an existing scholarship posting.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        
        # Find the scholarship posting
        scholarship = EmployerScholarshipPosting.query.get(scholarship_id)
        
        if not scholarship:
            return jsonify({"error": "Scholarship posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if scholarship.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Update fields if provided in the request
        if 'scholarship_title' in data:
            scholarship.scholarship_title = data['scholarship_title']
        if 'scholarship_description' in data:
            scholarship.scholarship_description = data['scholarship_description']
        if 'status' in data:
            scholarship.status = data['status']
        if 'expiration_date' in data and data['expiration_date']:
            scholarship.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d')
        
        # Check if the scholarship should be marked as expired
        if scholarship.expiration_date and scholarship.expiration_date < datetime.utcnow() and scholarship.status != 'expired':
            scholarship.status = 'expired'
        
        # Commit the changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Scholarship posting updated successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# DELETE SCHOLARSHIP POSTING
@employer.route('/scholarship-posting/<int:scholarship_id>', methods=['DELETE'])
@auth.login_required
def delete_scholarship_posting(scholarship_id):
    """
    Route to delete a scholarship posting.
    """
    try:
        
        # Find the scholarship posting
        scholarship = EmployerScholarshipPosting.query.get(scholarship_id)
        
        if not scholarship:
            return jsonify({"error": "Scholarship posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if scholarship.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Delete the scholarship posting
        db.session.delete(scholarship)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Scholarship posting deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@employer.route('/all-scholarship-postings', methods=['GET'])
@auth.login_required
def get_all_scholarship_postings():
    """
    Route to get all scholarship postings with employer details.
    Returns a list of all active scholarship postings along with the employer information.
    """
    try:
        # Update expired scholarship postings first (if you have this function)
        update_expired_scholarship_postings()
        
        # Query all scholarship postings that are not expired (status is not 'expired')
        scholarship_postings = (EmployerScholarshipPosting.query
                              .filter(EmployerScholarshipPosting.status == 'active')
                              .all())
        
        if not scholarship_postings:
            return jsonify({"message": "No active scholarship postings found"}), 404
        
        result = []
        
        # For each scholarship posting, get the employer information and combine them
        for scholarship in scholarship_postings:
            # Get employer information
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=scholarship.user_id).first()
            
            # Skip if employer information is not available
            if not employer_info:
                continue
                
            # Get user information
            user = User.query.get(scholarship.user_id)
            
            if not user:
                continue
            
            # Create a dictionary with scholarship posting and employer details
            scholarship_data = {
                "scholarship_id": scholarship.employer_scholarshippost_id,
                "scholarship_title": scholarship.scholarship_title,
                "scholarship_description": scholarship.scholarship_description,
                "slots": scholarship.slots,
                "occupied_slots": scholarship.occupied_slots,
                "remarks": scholarship.remarks,
                "status": scholarship.status,
                "created_at": scholarship.created_at.strftime('%Y-%m-%d'),
                "updated_at": scholarship.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": scholarship.expiration_date.strftime('%Y-%m-%d') if scholarship.expiration_date else None,
                "employer":{
                    "full_name": employer_info.first_name + " " + employer_info.middle_name + " " + employer_info.last_name if employer_info else None,
                }
            }
            
            result.append(scholarship_data)
        
        return jsonify({
            "success": True,
            "count": len(result),
            "scholarship_postings": result
        }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

#===========================================================================================================================================#
#                                                     GET ALL APPROVED APPLICANTS FOR JOBS, TRAININGS, AND SCHOLARSHIPS
#===========================================================================================================================================#
@employer.route('/approved-applicants', methods=['GET'])
@auth.login_required
def get_applicants():
    """
    Route to retrieve all approved applicants for jobs, trainings, and scholarships.
    Returns a list of approved applicants along with their details and associated postings.
    """
    try:
        uid = g.user.user_id  # Get the current employer's user ID

        # Fetch approved job applicants
        approved_job_applicants = (
            db.session.query(StudentJobseekerApplyJobs)
            .filter_by(status="approved")
            .join(EmployerJobPosting, StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id)
            .filter(EmployerJobPosting.user_id == uid)
            .all()
        )

        # Fetch approved training applicants
        approved_training_applicants = (
            db.session.query(StudentJobseekerApplyTrainings)
            .filter_by(status="approved")
            .join(EmployerTrainingPosting, StudentJobseekerApplyTrainings.employer_trainingpost_id == EmployerTrainingPosting.employer_trainingpost_id)
            .filter(EmployerTrainingPosting.user_id == uid)
            .all()
        )

        # Fetch approved scholarship applicants
        approved_scholarship_applicants = (
            db.session.query(StudentJobseekerApplyScholarships)
            .filter_by(status="approved")
            .join(EmployerScholarshipPosting, StudentJobseekerApplyScholarships.employer_scholarshippost_id == EmployerScholarshipPosting.employer_scholarshippost_id)
            .filter(EmployerScholarshipPosting.user_id == uid)
            .all()
        )

        # Helper function to serialize applicant details
        def serialize_applicant(application, posting_model):
            user = User.query.get(application.user_id)
            personal_info = user.jobseeker_student_personal_information
            job_preferences = user.jobseeker_student_job_preference
            language_proficiencies = user.jobseeker_student_language_proficiency
            educational_backgrounds = user.jobseeker_student_educational_background
            other_trainings = user.jobseeker_student_other_training
            professional_licenses = user.jobseeker_student_professional_license
            work_experiences = user.jobseeker_student_work_experience
            other_skills = user.jobseeker_student_other_skills

            posting = posting_model.query.get(
                getattr(application, f"employer_{posting_model.__tablename__.split('_')[1]}post_id")
            )

            return {
                "application_id": getattr(application, f"apply_{posting_model.__tablename__.split('_')[1]}_id"),
                "user_details": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "user_type": user.user_type,
                    "personal_information": personal_info.to_dict() if personal_info else None,
                    "job_preferences": job_preferences.to_dict() if job_preferences else None,
                    "language_proficiencies": [lang.to_dict() for lang in language_proficiencies] if language_proficiencies else [],
                    "educational_background": [edu.to_dict() for edu in educational_backgrounds] if educational_backgrounds else [],
                    "other_trainings": [train.to_dict() for train in other_trainings] if other_trainings else [],
                    "professional_licenses": [license.to_dict() for license in professional_licenses] if professional_licenses else [],
                    "work_experiences": [exp.to_dict() for exp in work_experiences] if work_experiences else [],
                    "other_skills": [skill.to_dict() for skill in other_skills] if other_skills else [],
                },
                "posting_details": posting.to_dict() if posting else None,
                "application_status": application.status,
                "applied_at": application.created_at.strftime("%Y-%m-%d"),
                "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
            }

        # Serialize job applicants
        approved_jobs_data = [
            serialize_applicant(app, EmployerJobPosting) for app in approved_job_applicants
        ]

        # Serialize training applicants
        approved_trainings_data = [
            serialize_applicant(app, EmployerTrainingPosting) for app in approved_training_applicants
        ]

        # Serialize scholarship applicants
        approved_scholarships_data = [
            serialize_applicant(app, EmployerScholarshipPosting) for app in approved_scholarship_applicants
        ]

        # Return the combined result
        return jsonify({
            "success": True,
            "count_approved_jobs_data": len(approved_jobs_data),
            "count_approved_trainings_data": len(approved_trainings_data),
            "count_approved_scholarships_data": len(approved_scholarships_data),
            "approved_applicants": {
                "jobs": approved_jobs_data,
                "trainings": approved_trainings_data,
                "scholarships": approved_scholarships_data,
            }
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

#===========================================================================================================================================#
#                                                     ADD, GET COMPANY INFORMATION
#===========================================================================================================================================#
@employer.route('/add-company-information', methods=['POST'])
@auth.login_required  
def add_company_information():
    """
    Route to add or update company information for an employer.
    Expects JSON payload with all required fields.
    If company information already exists, it will be updated.
    """
    try:
        # Get the authenticated user's ID
        uid = g.user.user_id 

        # Parse JSON data from the request
        data = request.get_json()
        if not data:
            raise BadRequest("Invalid JSON payload")

        # Validate required fields
        required_fields = [
            'company_name', 'company_email', 'company_industry',
            'company_type', 'company_total_workforce', 'company_country',
            'company_address', 'company_house_no_street', 'company_postal_code'
        ]
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")

        # Check if the user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if company information already exists for the user
        company_info = EmployerCompanyInformation.query.filter_by(user_id=uid).first()

        if company_info:
            # Update the existing company information
            company_info.company_name = data['company_name']
            company_info.company_email = data['company_email']
            company_info.company_industry = data['company_industry']
            company_info.company_type = data['company_type']
            company_info.company_total_workforce = data['company_total_workforce']
            company_info.company_country = data['company_country']
            company_info.company_address = data['company_address']
            company_info.company_house_no_street = data['company_house_no_street']
            company_info.company_postal_code = data['company_postal_code']
            company_info.company_website = data.get('company_website')
            company_info.logo_image_path = data.get('logo_image_path')
            company_info.business_permit_path = data.get('business_permit_path')
            company_info.bir_form_path = data.get('bir_form_path')
            company_info.poea_file_path = data.get('poea_file_path')
            company_info.philhealth_file_path = data.get('philhealth_file_path')
            company_info.dole_certificate_path = data.get('dole_certificate_path')
            company_info.admin_remarks = data.get('admin_remarks')
            company_info.status = data.get('status', company_info.status)  # Preserve status unless explicitly updated
            company_info.updated_at = db.func.current_timestamp()  # Update the timestamp

            message = "Company information updated successfully"
        else:
            # Create a new EmployerCompanyInformation instance
            company_info = EmployerCompanyInformation(
                user_id=uid,
                company_name=data['company_name'],
                company_email=data['company_email'],
                company_industry=data['company_industry'],
                company_type=data['company_type'],
                company_total_workforce=data['company_total_workforce'],
                company_country=data['company_country'],
                company_address=data['company_address'],
                company_house_no_street=data['company_house_no_street'],
                company_postal_code=data['company_postal_code'],
                company_website=data.get('company_website'),
                logo_image_path=data.get('logo_image_path'),
                business_permit_path=data.get('business_permit_path'),
                bir_form_path=data.get('bir_form_path'),
                poea_file_path=data.get('poea_file_path'),
                philhealth_file_path=data.get('philhealth_file_path'),
                dole_certificate_path=data.get('dole_certificate_path'),
                admin_remarks=data.get('admin_remarks'),
                status=data.get('status', 'pending')  # Default status is 'pending'
            )
            db.session.add(company_info)

            message = "Company information added successfully"

        # Commit the changes to the database
        db.session.commit()

        # Return success response
        return jsonify({
            "message": message,
            "company_info_id": company_info.employer_companyinfo_id
        }), 201 if not company_info else 200

    except BadRequest as e:
        # Handle missing or invalid fields
        return jsonify({"error": str(e)}), 400

    except IntegrityError:
        # Handle database integrity errors (e.g., duplicate entries)
        db.session.rollback()
        return jsonify({"error": "Integrity error: Data already exists or is invalid"}), 409

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@employer.route('/get-company-information', methods=['GET'])
@auth.login_required
def get_company_information():
    """
    Route to retrieve company information for an employer.
    Retrieves data based on the authenticated user's ID.
    """
    try:
        # Get the authenticated user's ID
        uid = g.user.user_id

        # Query the database for the company information
        company_info = db.session.query(EmployerCompanyInformation).filter_by(user_id=uid).first()

        if not uid:
            return jsonify({"error": "User not found"}), 404

        if not company_info:
            return jsonify({"error": "Company information not found"}), 404

        # Serialize the company information into a dictionary
        company_data = {
            "employer_companyinfo_id": company_info.employer_companyinfo_id,
            "user_id": company_info.user_id,
            "company_name": company_info.company_name,
            "company_email": company_info.company_email,
            "company_industry": company_info.company_industry,
            "company_type": company_info.company_type,
            "company_total_workforce": company_info.company_total_workforce,
            "company_country": company_info.company_country,
            "company_address": company_info.company_address,
            "company_house_no_street": company_info.company_house_no_street,
            "company_postal_code": company_info.company_postal_code,
            "company_website": company_info.company_website,
            "logo_image_path": company_info.logo_image_path,
            "business_permit_path": company_info.business_permit_path,
            "bir_form_path": company_info.bir_form_path,
            "poea_file_path": company_info.poea_file_path,
            "philhealth_file_path": company_info.philhealth_file_path,
            "dole_certificate_path": company_info.dole_certificate_path,
            "admin_remarks": company_info.admin_remarks,
            "status": company_info.status,
            "created_at": company_info.created_at.isoformat(),
            "updated_at": company_info.updated_at.isoformat()
        }

        # Return the company information as JSON
        return jsonify({
            "message": "Company information retrieved successfully",
            "company_information": company_data
        }), 200

    except NoResultFound:
        # Handle case where no company information is found
        return jsonify({"error": "Company information not found"}), 404

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    
# ===========================================================================================================================================#
#                                                     GET APPROVED APPLICANTS FOR JOBS, TRAININGS, AND SCHOLARSHIPS
# ===========================================================================================================================================#
@employer.route('/get-applicants', methods=['GET'])
def get_approved_applicants():
    """
    Route to retrieve all approved applicants (applied) for a specific posting.
    """
    # Parse input data
    data = request.get_json()
    posting_type = data.get('posting_type')
    posting_id = data.get('posting_id')

    if not posting_type or not posting_id:
        return jsonify({"error": "Both 'posting_type' and 'posting_id' are required."}), 400

    try:
        # Initialize result container
        applied_jobseekers = []

        # Query based on posting type
        if posting_type == 'job':
            applied_jobseekers = db.session.query(StudentJobseekerApplyJobs, User).join(
                User, StudentJobseekerApplyJobs.user_id == User.user_id
            ).filter(
                StudentJobseekerApplyJobs.employer_jobpost_id == posting_id,
                StudentJobseekerApplyJobs.status == 'approved'
            ).all()

        elif posting_type == 'training':
            applied_jobseekers = db.session.query(StudentJobseekerApplyTrainings, User).join(
                User, StudentJobseekerApplyTrainings.user_id == User.user_id
            ).filter(
                StudentJobseekerApplyTrainings.employer_trainingpost_id == posting_id,
                StudentJobseekerApplyTrainings.status == 'approved'
            ).all()

        elif posting_type == 'scholarship':
            applied_jobseekers = db.session.query(StudentJobseekerApplyScholarships, User).join(
                User, StudentJobseekerApplyScholarships.user_id == User.user_id
            ).filter(
                StudentJobseekerApplyScholarships.employer_scholarshippost_id == posting_id,
                StudentJobseekerApplyScholarships.status == 'approved'
            ).all()

        else:
            return jsonify({"error": "Invalid posting_type. Must be 'job', 'training', or 'scholarship'."}), 400

        # Serialize results
        result = [
            {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "status": record.status,
                "applied_at": record.created_at.strftime('%Y-%m-%d'),
                "type": "applied"
            }
            for record, user in applied_jobseekers
        ]

        return jsonify({
            "success": True,
            "count": len(result),
            "approved_applicants": result
        }), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500