from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, PersonalInformation, JobPreference, LanguageProficiency, StudentJobseekerApplyJobs, StudentJobseekerApplyTrainings, StudentJobseekerApplyScholarships, EducationalBackground,ProfessionalLicense, AcademePersonalInformation, OtherTraining, WorkExperience, OtherSkills, EmployerScholarshipPosting, EmployerPersonalInformation, EmployerJobPosting, EmployerTrainingPosting, EmployerJobPosting, WorkExperience, OtherSkills, ProfessionalLicense, OtherTraining, AcademePersonalInformation, EmployerPersonalInformation
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings, update_expired_scholarship_postings, convert_dates
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
        valid_statuses = ['active', 'rejected', 'expired']
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

@admin.route('/public/all-postings', methods=['GET'])
@auth.login_required
def get_categorized_postings():
    """
    Route to get all job, training, and scholarship postings from all employers.
    Returns postings categorized by type (job, scholarship, training) in separate sections.
    """
    try:
        # Update expired postings first
        update_expired_job_postings()
        update_expired_training_postings()
        update_expired_scholarship_postings()
        
        # Query the database for all postings
        job_postings = EmployerJobPosting.query.all()
        training_postings = EmployerTrainingPosting.query.all()
        scholarship_postings = EmployerScholarshipPosting.query.all()
        
        # If no postings found at all
        if not job_postings and not training_postings and not scholarship_postings:
            return jsonify({
                "success": False,
                "message": "No postings found"
            }), 404

        # Process job postings with employer information
        job_postings_data = []
        for job in job_postings:
            # Get employer information
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=job.user_id).first()
            user = User.query.get(job.user_id)
            
            if not employer_info or not user:
                continue
                
            job_data = {
                "id": job.employer_jobpost_id,
                "title": job.job_title,
                "description": job.job_description,
                "job_type": job.job_type,
                "experience_level": job.experience_level,
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
                "expiration_date": job.expiration_date.strftime('%Y-%m-%d') if job.expiration_date else None,
                "employer": {
                    "user_id": job.user_id,
                    "username": user.username,
                    "email": user.email,
                    "company_name": employer_info.company_name if hasattr(employer_info, 'company_name') else None,
                    "contact_number": employer_info.contact_number if hasattr(employer_info, 'contact_number') else None,
                    "address": employer_info.address if hasattr(employer_info, 'address') else None,
                    "website": employer_info.website if hasattr(employer_info, 'website') else None,
                    "company_description": employer_info.company_description if hasattr(employer_info, 'company_description') else None
                }
            }
            job_postings_data.append(job_data)
            
        # Process training postings with employer information
        training_postings_data = []
        for training in training_postings:
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=training.user_id).first()
            user = User.query.get(training.user_id)
            
            if not employer_info or not user:
                continue
                
            training_data = {
                "id": training.employer_trainingpost_id,
                "title": training.training_title,
                "description": training.training_description,
                "status": training.status,
                "created_at": training.created_at.strftime('%Y-%m-%d'),
                "updated_at": training.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": training.expiration_date.strftime('%Y-%m-%d') if training.expiration_date else None,
                "employer": {
                    "user_id": training.user_id,
                    "username": user.username,
                    "email": user.email,
                    "company_name": employer_info.company_name if hasattr(employer_info, 'company_name') else None,
                    "contact_number": employer_info.contact_number if hasattr(employer_info, 'contact_number') else None,
                    "address": employer_info.address if hasattr(employer_info, 'address') else None,
                    "website": employer_info.website if hasattr(employer_info, 'website') else None,
                    "company_description": employer_info.company_description if hasattr(employer_info, 'company_description') else None
                }
            }
            training_postings_data.append(training_data)
            
        # Process scholarship postings with employer information
        scholarship_postings_data = []
        for scholarship in scholarship_postings:
            employer_info = EmployerPersonalInformation.query.filter_by(user_id=scholarship.user_id).first()
            user = User.query.get(scholarship.user_id)
            
            if not employer_info or not user:
                continue
                
            scholarship_data = {
                "id": scholarship.employer_scholarshippost_id,
                "title": scholarship.scholarship_title,
                "description": scholarship.scholarship_description,
                "status": scholarship.status,
                "created_at": scholarship.created_at.strftime('%Y-%m-%d'),
                "updated_at": scholarship.updated_at.strftime('%Y-%m-%d'),
                "expiration_date": scholarship.expiration_date.strftime('%Y-%m-%d') if scholarship.expiration_date else None,
                "employer": {
                    "user_id": scholarship.user_id,
                    "username": user.username,
                    "email": user.email,
                    "company_name": employer_info.company_name if hasattr(employer_info, 'company_name') else None,
                    "contact_number": employer_info.contact_number if hasattr(employer_info, 'contact_number') else None,
                    "address": employer_info.address if hasattr(employer_info, 'address') else None,
                    "website": employer_info.website if hasattr(employer_info, 'website') else None,
                    "company_description": employer_info.company_description if hasattr(employer_info, 'company_description') else None
                }
            }
            scholarship_postings_data.append(scholarship_data)
        
        # Prepare response with counts and categorized postings
        response_data = {
            "success": True,
            "total_count": len(job_postings_data) + len(training_postings_data) + len(scholarship_postings_data),
            "job_postings": {
                "count": len(job_postings_data),
                "data": job_postings_data
            },
            "scholarship_postings": {
                "count": len(scholarship_postings_data),
                "data": scholarship_postings_data
            },
            "training_postings": {
                "count": len(training_postings_data),
                "data": training_postings_data
            }
        }
        
        return jsonify(response_data), 200
    
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

@admin.route('/all-users', methods=['GET'])
@auth.login_required
def get_all_users():
    """
    Route to retrieve all users from the database.
    Requires authentication with admin access level.
    """
    try:
        # # Check if the user has admin privileges (access_level check)
        # if g.user.access_level < 2:  # Assuming access level 2 or higher is admin
        #     return jsonify({
        #         "success": False,
        #         "error": "Unauthorized access. Admin privileges required."
        #     }), 403
            
        # Query all users from the database
        users = User.query.all()
        
        # If no users found
        if not users:
            return jsonify({
                "success": False,
                "message": "No users found in the database"
            }), 404
            
        # Format user data for the response (exclude sensitive information)
        users_data = []
        for user in users:
            user_data = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "user_type": user.user_type,
                "access_level": user.access_level,
                "created_at": user.created_at.strftime('%Y-%m-%d')
            }
            
            # Get associated profile information based on user type
            if user.user_type == 'employer':
                if user.employer_personal_information:
                    employer_info = user.employer_personal_information[0] if user.employer_personal_information else None
                    if employer_info:
                        user_data["profile"] = {
                            "company_name": employer_info.company_name if hasattr(employer_info, 'company_name') else None,
                            "contact_number": employer_info.contact_number if hasattr(employer_info, 'contact_number') else None,
                            "address": employer_info.address if hasattr(employer_info, 'address') else None,
                            "website": employer_info.website if hasattr(employer_info, 'website') else None
                        }
            elif user.user_type in ['jobseeker', 'student']:
                if user.jobseeker_student_personal_information:
                    user_data["profile"] = {
                        "first_name": user.jobseeker_student_personal_information.first_name if hasattr(user.jobseeker_student_personal_information, 'first_name') else None,
                        "last_name": user.jobseeker_student_personal_information.last_name if hasattr(user.jobseeker_student_personal_information, 'last_name') else None,
                        "contact_number": user.jobseeker_student_personal_information.contact_number if hasattr(user.jobseeker_student_personal_information, 'contact_number') else None
                    }
            elif user.user_type == 'academe':
                if user.academe_personal_information:
                    academe_info = user.academe_personal_information[0] if user.academe_personal_information else None
                    if academe_info:
                        user_data["profile"] = {
                            "institution_name": academe_info.institution_name if hasattr(academe_info, 'institution_name') else None,
                            "contact_number": academe_info.contact_number if hasattr(academe_info, 'contact_number') else None,
                            "address": academe_info.address if hasattr(academe_info, 'address') else None
                        }
                        
            # # Add statistics about user's activities
            # user_data["statistics"] = {}
            
            # if user.user_type == 'employer':
            #     user_data["statistics"] = {
            #         "job_postings_count": len(user.employer_job_postings),
            #         "training_postings_count": len(user.employer_training_postings),
            #         "scholarship_postings_count": len(user.employer_scholarship_postings)
            #     }
            # elif user.user_type in ['jobseeker', 'student']:
            #     user_data["statistics"] = {
            #         "saved_jobs_count": len(user.jobseeker_student_saved_jobs),
            #         "applied_jobs_count": len(user.jobseeker_student_apply_jobs),
            #         "saved_trainings_count": len(user.jobseeker_student_saved_trainings),
            #         "applied_trainings_count": len(user.jobseeker_student_apply_trainings),
            #         "saved_scholarships_count": len(user.jobseeker_student_saved_scholarships),
            #         "applied_scholarships_count": len(user.jobseeker_student_apply_scholarships)
            #     }
            # elif user.user_type == 'academe':
            #     user_data["statistics"] = {
            #         "graduate_reports_count": len(user.academe_graduate_reports),
            #         "enrollment_reports_count": len(user.academe_enrollment_reports)
            #     }
                
            users_data.append(user_data)
            
        # Sort users by ID
        users_data.sort(key=lambda x: x["user_id"])
            
        # Return the user data in the response
        return jsonify({
            "success": True,
            "count": len(users_data),
            "users": users_data
        }), 200
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

# GET USER INFO BY ID
@admin.route('admin/get-user-info/<int:user_id>', methods=['GET'])
@auth.login_required
def get_personal_info(user_id):
    try:

        uid = user_id
        
        if uid is None:
            return jsonify({"error": "Missing user_id"}), 400
        
        # Query the database for the user
        user = User.query.filter_by(user_id=uid).first()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        # Common function to handle None responses
        def fetch_data(model):
            return exclude_fields(get_user_data(model, uid) or [])
        
        if user.user_type in ["STUDENT", "JOBSEEKER"]:
            personal_information = fetch_data(PersonalInformation)
            job_preference = fetch_data(JobPreference)
            language_proficiency = fetch_data(LanguageProficiency)
            educational_background = fetch_data(EducationalBackground)
            other_training = fetch_data(OtherTraining)
            professional_license = fetch_data(ProfessionalLicense)
            work_experience = fetch_data(WorkExperience)
            other_skills = fetch_data(OtherSkills)

            user = User.query.filter_by(user_id=uid).first()

            # Transform disability format
            for item in personal_information:
                disability_str = item.get("disability", "")
                if disability_str:
                    disabilities = [d.strip() for d in disability_str.split(",")]
                    item["disability"] = {
                        "visual": "visual" in disabilities,
                        "hearing": "hearing" in disabilities,
                        "speech": "speech" in disabilities,
                        "physical": "physical" in disabilities,
                    }

            personal_information[0]["username"] = user.username

            return jsonify({
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "user_type": user.user_type,
                "access_level": user.access_level,
                "created_at": user.created_at.strftime('%Y-%m-%d'),
                "personal_information": convert_dates(personal_information),
                "job_preference": convert_dates(job_preference),
                "language_proficiency": convert_dates(language_proficiency),
                "educational_background": convert_dates(educational_background),
                "other_training": convert_dates(other_training),
                "professional_license": convert_dates(professional_license),
                "work_experience": convert_dates(work_experience),
                "other_skills": convert_dates(other_skills)
            }), 200

        elif user.user_type == "EMPLOYER":
            employer = fetch_data(EmployerPersonalInformation)
            user = User.query.filter_by(user_id=uid).first()
            employer[0]["username"] = user.username
            return jsonify({
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "user_type": user.user_type,
                "access_level": user.access_level,
                "created_at": user.created_at.strftime('%Y-%m-%d'),
                "personal_information": employer
                }), 200

        elif user.user_type == "ACADEME":
            academe = fetch_data(AcademePersonalInformation)
            user = User.query.filter_by(user_id=uid).first()
            academe[0]["username"] = user.username
            return jsonify({
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "user_type": user.user_type,
                "access_level": user.access_level,
                "created_at": user.created_at.strftime('%Y-%m-%d'),
                "personal_information": academe
                }), 200

        return jsonify({"error": "Invalid user type"}), 400

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

# GET ALL USER AND THEIR APPLIED JOBS
@admin.route('/get-all-users-applied-jobs', methods=['GET'])
@auth.login_required
def get_all_users_applied_jobs():
    """
    Route to retrieve all users and their applied jobs.
    Requires authentication.
    """
    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        # Prepare the result
        result = []
        for user in users:
            # Fetch the applied jobs for each user
            applied_jobs = (
                StudentJobseekerApplyJobs.query
                .filter_by(user_id=user.user_id)
                .order_by(StudentJobseekerApplyJobs.created_at.desc())
                .all()
            )

            # Serialize the applied jobs
            if user.user_type in ["JOBSEEKER", "STUDENT"]:
                for application in applied_jobs:
                    job_posting = application.user_apply_job  # Access the related job posting
                    if job_posting:
                        # Create an object combining user details and job application details
                        result.append({
                            "application_id": application.apply_job_id,
                            "job_posting_id": application.employer_jobpost_id,
                            "job_title": job_posting.job_title,
                            "company_name": job_posting.employer.company_name if hasattr(job_posting, 'employer') and job_posting.employer else "Unknown Company",
                            "job_type": job_posting.job_type,
                            "experience_level": job_posting.experience_level,
                            "estimated_salary_from": job_posting.estimated_salary_from,
                            "estimated_salary_to": job_posting.estimated_salary_to,
                            "country": job_posting.country,
                            "city_municipality": job_posting.city_municipality,
                            "application_status": application.status,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "user_details": {
                                "fullname": f"{user.jobseeker_student_personal_information.first_name} {user.jobseeker_student_personal_information.last_name}" if user.jobseeker_student_personal_information else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                            }
                        })

        # Return the list of combined user-job objects
        return jsonify({
            "success": True,
            "message": "All users and their applied jobs retrieved successfully",
            "applied_jobs": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# GET ALL USER AND THEIR APPLIED SCHOLARSHIPS
@admin.route('/get-all-users-applied-scholarships', methods=['GET'])
@auth.login_required
def get_all_users_applied_scholarships():
    """
    Route to retrieve all users and their applied scholarships.
    Requires authentication.
    """
    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        result = []
        for user in users:
            
            applied_scholarships = (
                StudentJobseekerApplyScholarships.query
                .filter_by(user_id=user.user_id)
                .order_by(StudentJobseekerApplyScholarships.created_at.desc())
                .all()
            )

            
            if user.user_type in ["JOBSEEKER", "STUDENT"]:
                for application in applied_scholarships:
                    scholarship_posting = application.user_apply_scholarships  
                    if scholarship_posting:
                  
                        result.append({
                            "application_id": application.apply_scholarship_id,
                            "scholarship_posting_id": application.employer_scholarshippost_id,
                            "scholarship_title": scholarship_posting.scholarship_title,
                            "company_name": scholarship_posting.employer.company_name if hasattr(scholarship_posting, 'employer') and scholarship_posting.employer else "Unknown Company",
                            "scholarship_description": scholarship_posting.scholarship_description,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "expired_at": scholarship_posting.expiration_date.strftime("%Y-%m-%d") if scholarship_posting.expiration_date else None,
                            "application_status": application.status,
                            "user_details": {
                                "fullname": f"{user.jobseeker_student_personal_information.first_name} {user.jobseeker_student_personal_information.last_name}" if user.jobseeker_student_personal_information else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                            }
                        })

        return jsonify({
            "success": True,
            "message": "All users and their applied schilarships retrieved successfully",
            "applied_scholarships": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# GET ALL USER AND THEIR APPLIED TRAININGS
@admin.route('/get-all-users-applied-trainings', methods=['GET'])
@auth.login_required
def get_all_users_applied_trainings():
    """
    Route to retrieve all users and their applied trainings.
    Requires authentication.
    """
    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        result = []
        for user in users:
            
            applied_trainings = (
                StudentJobseekerApplyTrainings.query
                .filter_by(user_id=user.user_id)
                .order_by(StudentJobseekerApplyTrainings.created_at.desc())
                .all()
            )

            if user.user_type in ["JOBSEEKER", "STUDENT"]:
                for application in applied_trainings:
                    training_posting = application.user_apply_trainings
                    if training_posting:
                  
                        result.append({
                            "application_id": application.apply_training_id,
                            "training_posting_id": application.employer_trainingpost_id,
                            "training_title": training_posting.training_title,
                            "company_name": training_posting.employer.company_name if hasattr(training_posting, 'employer') and training_posting.employer else "Unknown Company",
                            "training_description": training_posting.training_description,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "expired_at": training_posting.expiration_date.strftime("%Y-%m-%d") if training_posting.expiration_date else None,
                            "application_status": application.status,
                            "user_details": {
                                "fullname": f"{user.jobseeker_student_personal_information.first_name} {user.jobseeker_student_personal_information.last_name}" if user.jobseeker_student_personal_information else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                            }
                        })

        return jsonify({
            "success": True,
            "message": "All users and their applied trainings retrieved successfully",
            "applied_trainings": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
