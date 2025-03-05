from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, EmployerJobPosting, EmployerTrainingPosting, EmployerScholarshipPosting, EmployerPersonalInformation
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings
from datetime import datetime, timedelta

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


# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# EMPLOYER JOB POSTING. POST, GET, PUT, DELETE
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ADD JOB POSTING
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

        uid = 2 # for testing

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
            status=data.get('status', 'pending'),  # Default status is 'pending'
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
# @auth.login_required  # Uncomment if authentication is required
def get_job_postings():
    uid = 2  # For testing purposes
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
            "job_postings": job_postings_data
            }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# UPDATE JOB POSTING
@employer.route('/job-posting/<int:job_id>', methods=['PUT'])
# @auth.login_required
def update_job_posting(job_id):
    """
    Route to update an existing job posting.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = 2  # For testing purposes (replace with actual user ID)
        
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
# @auth.login_required
def delete_job_posting(job_id):
    """
    Route to delete a job posting.
    """
    try:
        uid = 2  # For testing purposes (replace with actual user ID)
        
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

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Training Posting. POST, GET, PUT, DELETE
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ADD DATA TRAINING POSTING
@employer.route('/training-posting', methods=['POST'])
# @auth.login_required  # Uncomment if authentication is required
def create_training_posting():
    """
    Route to create a new training posting.
    Expects JSON input with all relevant fields from the EmployerTrainingPosting model.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = 2  # For testing purposes (replace with actual user ID)

        # Validate required fields based on model's nullable=False constraints
        required_fields = [
            'training_title', 
            'training_type', 
            'training_description', 
            'no_of_vacancies', 
            'country', 
            'city_municipality'
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

        # Create a new EmployerTrainingPosting instance with all available fields
        new_training_posting = EmployerTrainingPosting(
            user_id=uid,
            training_title=data['training_title'],
            training_type=data['training_type'],
            training_description=data['training_description'],
            no_of_vacancies=data['no_of_vacancies'],
            country=data['country'],
            city_municipality=data['city_municipality'],
            # Optional fields
            experience_level=data.get('experience_level'),
            estimated_salary_from=data.get('estimated_salary_from'),
            estimated_salary_to=data.get('estimated_salary_to'),
            other_skills=data.get('other_skills'),
            course_name=data.get('course_name'),
            training_institution=data.get('training_institution'),
            certificate_received=data.get('certificate_received'),
            status=data.get('status', 'pending'),  # Use default if not provided
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
# @auth.login_required
def get_training_postings():
    """
    Route to get all training postings for a user.
    """
    uid = 2  # For testing purposes (replace with actual user ID)
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

        # Serialize the training postings into a list of dictionaries
        training_postings_data = [
            {
                "training_id": training.employer_trainingpost_id,
                "training_title": training.training_title,
                "training_type": training.training_type,
                "training_description": training.training_description,
                "experience_level": training.experience_level,
                "no_of_vacancies": training.no_of_vacancies,
                "country": training.country,
                "city_municipality": training.city_municipality,
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
            "training_postings": training_postings_data
        }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# UPDATE TRAINING POSTING
@employer.route('/training-posting/<int:training_id>', methods=['PUT'])
# @auth.login_required
def update_training_posting(training_id):
    """
    Route to update an existing training posting.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = 2  # For testing purposes (replace with actual user ID)
        
        # Find the training posting
        training = EmployerTrainingPosting.query.get(training_id)
        
        if not training:
            return jsonify({"error": "Training posting not found"}), 404
            
        # Verify the user owns this posting (once auth is implemented)
        # if training.user_id != current_user.id:
        #     return jsonify({"error": "Unauthorized access"}), 403
        
        # Update fields if provided in the request
        if 'training_title' in data:  # Fixed field name from training_name to training_title
            training.training_title = data['training_title']
        if 'training_type' in data:
            training.training_type = data['training_type']
        if 'experience_level' in data:
            training.experience_level = data['experience_level']
        if 'training_description' in data:
            training.training_description = data['training_description']
        if 'estimated_salary_from' in data:
            training.estimated_salary_from = data['estimated_salary_from']
        if 'estimated_salary_to' in data:
            training.estimated_salary_to = data['estimated_salary_to']
        if 'no_of_vacancies' in data:
            training.no_of_vacancies = data['no_of_vacancies']
        if 'country' in data:
            training.country = data['country']
        if 'city_municipality' in data:
            training.city_municipality = data['city_municipality']
        if 'other_skills' in data:
            training.other_skills = data['other_skills']
        if 'course_name' in data:
            training.course_name = data['course_name']
        if 'training_institution' in data:
            training.training_institution = data['training_institution']
        if 'certificate_received' in data:
            training.certificate_received = data['certificate_received']
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
# @auth.login_required
def delete_training_posting(training_id):
    """
    Route to delete a training posting.
    """
    try:
        uid = 2  # For testing purposes (replace with actual user ID)
        
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
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Scholarship posting, ADD or POST
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@employer.route('/scholarship-posting', methods=['POST'])
# @auth.login_required  # Uncomment if authentication is required
def create_scholarship_posting():
    """
    Route to create a new scholarship posting.
    Expects JSON input with the required fields.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        uid = 2  # For testing purposes (replace with actual user ID)

        # Validate required fields
        required_fields = ['scholarship_name', 'scholarship_description']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if the user already has a scholarship posting (optional validation)
        scholarship_posting = EmployerScholarshipPosting.query.filter_by(user_id=uid).first()

        # Create a new EmployerScholarshipPosting instance
        new_scholarship_posting = EmployerScholarshipPosting(
            user_id=uid,
            scholarship_name=data['scholarship_name'],
            scholarship_description=data['scholarship_description'],
        )

        # Add and commit to the database
        db.session.add(new_scholarship_posting)
        db.session.commit()

        # Return success response
        return jsonify({
            "success": True,
            "message": "Scholarship posting created successfully",
        }), 201
    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@employer.route('/get-scholarship-postings', methods=['GET'])
# @auth.login_required  # Uncomment if authentication is required
def get_scholarship_postings():
    uid = 2  # For testing purposes (replace with actual user ID)
    try:
        # Query the database for all scholarship postings associated with the given user_id
        scholarship_postings = EmployerScholarshipPosting.query.filter_by(user_id=uid).all()

        if not scholarship_postings:
            return jsonify({"error": "No scholarship postings found for this user"}), 404

        # Serialize the scholarship postings into a list of dictionaries
        scholarship_postings_data = [
            {
                "scholarshi_post_id": scholarship.employer_scholarshippost_id,
                "scholarship_name": scholarship.scholarship_name,
                "scholarship_description": scholarship.scholarship_description,
                "status": scholarship.status,
                "created_at": scholarship.created_at.strftime('%Y-%m-%d'),
                "updated_at": scholarship.updated_at.strftime('%Y-%m-%d')
            }
            for scholarship in scholarship_postings
        ]

        return jsonify({
            "success": True,
            "scholarship_postings": scholarship_postings_data
        }), 200
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500