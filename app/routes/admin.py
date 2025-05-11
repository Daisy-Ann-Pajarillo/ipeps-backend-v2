from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import (
        User, 
        PersonalInformation, 
        JobPreference, 
        LanguageProficiency, 
        StudentJobseekerApplyJobs, 
        StudentJobseekerApplyTrainings, 
        StudentJobseekerApplyScholarships, 
        EducationalBackground,
        ProfessionalLicense, 
        EmployerCompanyInformation, 
        AcademePersonalInformation, 
        OtherTraining, 
        WorkExperience, 
        OtherSkills, 
        EmployerScholarshipPosting, 
        EmployerPersonalInformation, 
        EmployerJobPosting, 
        EmployerTrainingPosting,
        Announcement
    )
from app.utils import get_user_data, exclude_fields, update_expired_job_postings, update_expired_training_postings, update_expired_scholarship_postings, convert_dates, convert
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, SQLAlchemyError,  NoResultFound
from werkzeug.exceptions import BadRequest
from sqlalchemy import func, desc, case, and_, distinct, extract

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
        posting.remarks = data.get('admin_remarks', None)  # Optional remarks field
        
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
            }, 404)

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
                "admin_remarks": job.remarks,
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
@admin.route('/admin/get-user-info/<int:user_id>', methods=['GET'])
@auth.login_required
def get_user_info(user_id):
    """
    Endpoint to retrieve detailed information about a user by their ID.
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_type = (user.user_type or "").upper()
        user_data = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type,
        }

        if user_type in ["JOBSEEKER", "STUDENT"]:
            personal_info = user.jobseeker_student_personal_information
            job_preference = user.jobseeker_student_job_preference
            educational_background = user.jobseeker_student_educational_background
            trainings = user.jobseeker_student_other_training
            professional_licenses = user.jobseeker_student_professional_license
            work_experiences = user.jobseeker_student_work_experience
            other_skills = user.jobseeker_student_other_skills

            user_data.update({
                "personal_information": personal_info.to_dict() if personal_info else None,
                "job_preference": job_preference.to_dict() if job_preference else None,
                "educational_background": [edu.to_dict() for edu in educational_background] if educational_background else [],
                "trainings": [training.to_dict() for training in trainings] if trainings else [],
                "professional_licenses": [license.to_dict() for license in professional_licenses] if professional_licenses else [],
                "work_experiences": [work.to_dict() for work in work_experiences] if work_experiences else [],
                "other_skills": [skill.to_dict() for skill in other_skills] if other_skills else [],
            })

        elif user_type == "EMPLOYER":
            # Always get the first EmployerPersonalInformation if it's a list or a relationship
            employer_info = None
            if hasattr(user, "employer_personal_information"):
                info = user.employer_personal_information
                # If it's a list-like (e.g., relationship with uselist=True)
                if isinstance(info, list):
                    employer_info = info[0] if info else None
                else:
                    employer_info = info
            # Compose all required fields for employer_personal_information
            if employer_info:
                user_data["personal_information"] = {
                    "employer_personal_info_id": getattr(employer_info, "employer_personal_info_id", None),
                    "user_id": getattr(employer_info, "user_id", None),
                    "prefix": getattr(employer_info, "prefix", None),
                    "first_name": getattr(employer_info, "first_name", None),
                    "middle_name": getattr(employer_info, "middle_name", None),
                    "last_name": getattr(employer_info, "last_name", None),
                    "suffix": getattr(employer_info, "suffix", None),
                    "company_type": getattr(employer_info, "company_type", None),
                    "company_classification": getattr(employer_info, "company_classification", None),
                    "company_industry": getattr(employer_info, "company_industry", None),
                    "company_workforce": getattr(employer_info, "company_workforce", None),
                    "email": getattr(employer_info, "email", None),
                    "employer_position": getattr(employer_info, "employer_position", None),
                    "employer_id_number": getattr(employer_info, "employer_id_number", None),
                    "temporary_country": getattr(employer_info, "temporary_country", None),
                    "temporary_province": getattr(employer_info, "temporary_province", None),
                    "temporary_municipality": getattr(employer_info, "temporary_municipality", None),
                    "temporary_zip_code": getattr(employer_info, "temporary_zip_code", None),
                    "temporary_barangay": getattr(employer_info, "temporary_barangay", None),
                    "temporary_house_no_street_village": getattr(employer_info, "temporary_house_no_street_village", None),
                    "permanent_country": getattr(employer_info, "permanent_country", None),
                    "permanent_municipality": getattr(employer_info, "permanent_municipality", None),
                    "permanent_zip_code": getattr(employer_info, "permanent_zip_code", None),
                    "permanent_barangay": getattr(employer_info, "permanent_barangay", None),
                    "permanent_house_no_street_village": getattr(employer_info, "permanent_house_no_street_village", None),
                    "cellphone_number": getattr(employer_info, "cellphone_number", None),
                    "landline_number": getattr(employer_info, "landline_number", None),
                    "valid_id_url": getattr(employer_info, "valid_id_url", None),
                }
            else:
                user_data["personal_information"] = None

        # ...existing code for other user types if needed...

        return jsonify(user_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#===========================================================================================================================================#
#                                                       ADMIN GET ALL USERS APPLICATIONS                                                    #
#===========================================================================================================================================#
@admin.route('/get-all-users-applied-jobs', methods=['GET'])
@auth.login_required
def get_all_users_applied_jobs():
    """
    Route to retrieve all users and their applied jobs.
    Requires authentication.
    """
    if g.user.user_type not in ['ADMIN']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        # Prepare the result
        result = []
        for user in users:
            personal_info = user.jobseeker_student_personal_information
            job_preferences = user.jobseeker_student_job_preference
            language_proficiencies = user.jobseeker_student_language_proficiency or []
            educational_backgrounds = user.jobseeker_student_educational_background or []
            other_trainings = user.jobseeker_student_other_training or []
            professional_licenses = user.jobseeker_student_professional_license or []
            work_experiences = user.jobseeker_student_work_experience or []
            other_skills = user.jobseeker_student_other_skills or []

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
                            "company_name": job_posting.company_name if hasattr(job_posting, 'company_name')  and job_posting.company_name else "Unknown Company",
                            "job_type": job_posting.job_type,
                            "experience_level": job_posting.experience_level,
                            "estimated_salary_from": job_posting.estimated_salary_from,
                            "estimated_salary_to": job_posting.estimated_salary_to,
                            "country": job_posting.country,
                            "city_municipality": job_posting.city_municipality,
                            "slots": job_posting.no_of_vacancies,
                            "remarks": job_posting.remarks,
                            "application_status": application.status,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "user_details": {
                                "fullname": f"{personal_info.first_name} {personal_info.last_name}" 
                                            if personal_info and personal_info.first_name and personal_info.last_name 
                                            else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                                "personal_information": {
                                    "prefix": personal_info.prefix if personal_info else None,
                                    "first_name": personal_info.first_name if personal_info else None,
                                    "middle_name": personal_info.middle_name if personal_info else None,
                                    "last_name": personal_info.last_name if personal_info else None,
                                    "suffix": personal_info.suffix if personal_info else None,
                                    "sex": personal_info.sex if personal_info else None,
                                    "date_of_birth": personal_info.date_of_birth.strftime("%Y-%m-%d") 
                                                     if personal_info and personal_info.date_of_birth else None,
                                    "place_of_birth": personal_info.place_of_birth if personal_info else None,
                                    "civil_status": personal_info.civil_status if personal_info else None,
                                    "height": personal_info.height if personal_info else None,
                                    "weight": personal_info.weight if personal_info else None,
                                    "religion": personal_info.religion if personal_info else None,
                                    "temporary_address": {
                                        "country": personal_info.temporary_country if personal_info else None,
                                        "province": personal_info.temporary_province if personal_info else None,
                                        "municipality": personal_info.temporary_municipality if personal_info else None,
                                        "zip_code": personal_info.temporary_zip_code if personal_info else None,
                                        "barangay": personal_info.temporary_barangay if personal_info else None,
                                        "house_no_street_village": personal_info.temporary_house_no_street_village 
                                                                   if personal_info else None,
                                    },
                                    "permanent_address": {
                                        "country": personal_info.permanent_country if personal_info else None,
                                        "province": personal_info.permanent_province if personal_info else None,
                                        "municipality": personal_info.permanent_municipality if personal_info else None,
                                        "zip_code": personal_info.permanent_zip_code if personal_info else None,
                                        "barangay": personal_info.permanent_barangay if personal_info else None,
                                        "house_no_street_village": personal_info.permanent_house_no_street_village 
                                                                   if personal_info else None,
                                    },
                                    "contact_number": personal_info.cellphone_number if personal_info else None,
                                    "landline_number": personal_info.landline_number if personal_info else None,
                                    "tin": personal_info.tin if personal_info else None,
                                    "sss_gsis_number": personal_info.sss_gsis_number if personal_info else None,
                                    "pag_ibig_number": personal_info.pag_ibig_number if personal_info else None,
                                    "phil_health_no": personal_info.phil_health_no if personal_info else None,
                                    "disability": personal_info.disability if personal_info else None,
                                    "employment_status": personal_info.employment_status if personal_info else None,
                                    "is_looking_for_work": personal_info.is_looking_for_work if personal_info else None,
                                    "since_when_looking_for_work": personal_info.since_when_looking_for_work.strftime("%Y-%m-%d") 
                                                                  if personal_info and personal_info.since_when_looking_for_work else None,
                                    "is_willing_to_work_immediately": personal_info.is_willing_to_work_immediately if personal_info else None,
                                    "is_ofw": personal_info.is_ofw if personal_info else None,
                                    "ofw_country": personal_info.ofw_country if personal_info else None,
                                    "is_former_ofw": personal_info.is_former_ofw if personal_info else None,
                                    "former_ofw_country": personal_info.former_ofw_country if personal_info else None,
                                    "former_ofw_country_date_return": personal_info.former_ofw_country_date_return.strftime("%Y-%m-%d") 
                                                                      if personal_info and personal_info.former_ofw_country_date_return else None,
                                    "is_4ps_beneficiary": personal_info.is_4ps_beneficiary if personal_info else None,
                                    "_4ps_household_id_no": personal_info._4ps_household_id_no if personal_info else None,
                                    "valid_id_url": personal_info.valid_id_url if personal_info else None,
                                },
                                "job_preferences": {
                                    "country": job_preferences.country if job_preferences else None,
                                    "province": job_preferences.province if job_preferences else None,
                                    "municipality": job_preferences.municipality if job_preferences else None,
                                    "industry": job_preferences.industry if job_preferences else None,
                                    "preferred_occupation": job_preferences.preferred_occupation if job_preferences else None,
                                    "salary_range": f"{job_preferences.salary_from}-{job_preferences.salary_to}" 
                                                    if job_preferences and job_preferences.salary_from and job_preferences.salary_to 
                                                    else None
                                },
                                "language_proficiencies": [
                                    {
                                        "language": lang.language,
                                        "can_read": lang.can_read,
                                        "can_write": lang.can_write,
                                        "can_speak": lang.can_speak,
                                        "can_understand": lang.can_understand
                                    } for lang in language_proficiencies
                                ],
                                "educational_background": [
                                    {
                                        "school_name": edu.school_name,
                                        "date_from": edu.date_from.strftime("%Y-%m-%d"),
                                        "date_to": edu.date_to.strftime("%Y-%m-%d") if edu.date_to else None,
                                        "degree_or_qualification": edu.degree_or_qualification,
                                        "field_of_study": edu.field_of_study,
                                        "program_duration_years": edu.program_duration
                                    } for edu in educational_backgrounds
                                ],
                                "other_trainings": [
                                    {
                                        "course_name": training.course_name,
                                        "start_date": training.start_date.strftime("%Y-%m-%d"),
                                        "end_date": training.end_date.strftime("%Y-%m-%d") if training.end_date else None,
                                        "training_institution": training.training_institution,
                                        "certificates_received": training.certificates_received,
                                        "hours_of_training": training.hours_of_training,
                                        "skills_acquired": training.skills_acquired
                                    } for training in other_trainings
                                ],
                                "professional_licenses": [
                                    {
                                        "license": license.license,
                                        "name": license.name,
                                        "date": license.date.strftime("%Y-%m-%d"),
                                        "valid_until": license.valid_until.strftime("%Y-%m-%d") if license.valid_until else None,
                                        "rating": license.rating
                                    } for license in professional_licenses
                                ],
                                "work_experiences": [
                                    {
                                        "company_name": exp.company_name,
                                        "company_address": exp.company_address,
                                        "position": exp.position,
                                        "employment_status": exp.employment_status,
                                        "date_start": exp.date_start.strftime("%Y-%m-%d"),
                                        "date_end": exp.date_end.strftime("%Y-%m-%d") if exp.date_end else None
                                    } for exp in work_experiences
                                ],
                                "other_skills": [
                                    {"skill": skill.skills} for skill in other_skills
                                ]
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
    if g.user.user_type not in ['ADMIN']:
        return jsonify({"error": "Unauthorized user type"}), 403

    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        result = []
        for user in users:
        
            personal_info = user.jobseeker_student_personal_information
            job_preferences = user.jobseeker_student_job_preference
            language_proficiencies = user.jobseeker_student_language_proficiency
            educational_backgrounds = user.jobseeker_student_educational_background
            other_trainings = user.jobseeker_student_other_training
            professional_licenses = user.jobseeker_student_professional_license
            work_experiences = user.jobseeker_student_work_experience
            other_skills = user.jobseeker_student_other_skills
            
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
                            "company_name": scholarship_posting.company_name if hasattr(scholarship_posting, 'company_name') and scholarship_posting.employer else "Unknown Company",
                            "scholarship_description": scholarship_posting.scholarship_description,
                            "slots": scholarship_posting.slots,
                            "remaining_slots": scholarship_posting.occupied_slots,
                            "remarks": scholarship_posting.remarks,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "expired_at": scholarship_posting.expiration_date.strftime("%Y-%m-%d") if scholarship_posting.expiration_date else None,
                            "application_status": application.status,
                            "user_details": {
                                "fullname": f"{personal_info.first_name} {personal_info.last_name}" if personal_info else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                                "personal_information": {
                                    "prefix": personal_info.prefix if hasattr(personal_info, 'prefix') else None,
                                    "first_name": personal_info.first_name if hasattr(personal_info, 'first_name') else None,
                                    "middle_name": personal_info.middle_name if hasattr(personal_info, 'middle_name') else None,
                                    "last_name": personal_info.last_name if hasattr(personal_info, 'last_name') else None,
                                    "suffix": personal_info.suffix if hasattr(personal_info, 'suffix') else None,
                                    "sex": personal_info.sex if hasattr(personal_info, 'sex') else None,
                                    "date_of_birth": personal_info.date_of_birth.strftime("%Y-%m-%d") if hasattr(personal_info, 'date_of_birth') and personal_info.date_of_birth else None,
                                    "place_of_birth": personal_info.place_of_birth if hasattr(personal_info, 'place_of_birth') else None,
                                    "civil_status": personal_info.civil_status if hasattr(personal_info, 'civil_status') else None,
                                    "height": personal_info.height if hasattr(personal_info, 'height') else None,
                                    "weight": personal_info.weight if hasattr(personal_info, 'weight') else None,
                                    "religion": personal_info.religion if hasattr(personal_info, 'religion') else None,
                                    "temporary_address": {
                                        "country": personal_info.temporary_country if hasattr(personal_info, 'temporary_country') else None,
                                        "province": personal_info.temporary_province if hasattr(personal_info, 'temporary_province') else None,
                                        "municipality": personal_info.temporary_municipality if hasattr(personal_info, 'temporary_municipality') else None,
                                        "zip_code": personal_info.temporary_zip_code if hasattr(personal_info, 'temporary_zip_code') else None,
                                        "barangay": personal_info.temporary_barangay if hasattr(personal_info, 'temporary_barangay') else None,
                                        "house_no_street_village": personal_info.temporary_house_no_street_village if hasattr(personal_info, 'temporary_house_no_street_village') else None,
                                    },
                                    "permanent_address": {
                                        "country": personal_info.permanent_country if hasattr(personal_info, 'permanent_country') else None,
                                        "province": personal_info.permanent_province if hasattr(personal_info, 'permanent_province') else None,
                                        "municipality": personal_info.permanent_municipality if hasattr(personal_info, 'permanent_municipality') else None,
                                        "zip_code": personal_info.permanent_zip_code if hasattr(personal_info, 'permanent_zip_code') else None,
                                        "barangay": personal_info.permanent_barangay if hasattr(personal_info, 'permanent_barangay') else None,
                                        "house_no_street_village": personal_info.permanent_house_no_street_village if hasattr(personal_info, 'permanent_house_no_street_village') else None,
                                    },
                                    "contact_number": personal_info.cellphone_number if hasattr(personal_info, 'cellphone_number') else None,
                                    "landline_number": personal_info.landline_number if hasattr(personal_info, 'landline_number') else None,
                                    "tin": personal_info.tin if hasattr(personal_info, 'tin') else None,
                                    "sss_gsis_number": personal_info.sss_gsis_number if hasattr(personal_info, 'sss_gsis_number') else None,
                                    "pag_ibig_number": personal_info.pag_ibig_number if hasattr(personal_info, 'pag_ibig_number') else None,
                                    "phil_health_no": personal_info.phil_health_no if hasattr(personal_info, 'phil_health_no') else None,
                                    "disability": personal_info.disability if hasattr(personal_info, 'disability') else None,
                                    "employment_status": personal_info.employment_status if hasattr(personal_info, 'employment_status') else None,
                                    "is_looking_for_work": personal_info.is_looking_for_work if hasattr(personal_info, 'is_looking_for_work') else None,
                                    "since_when_looking_for_work": personal_info.since_when_looking_for_work.strftime("%Y-%m-%d") if hasattr(personal_info, 'since_when_looking_for_work') and personal_info.since_when_looking_for_work else None,
                                    "is_willing_to_work_immediately": personal_info.is_willing_to_work_immediately if hasattr(personal_info, 'is_willing_to_work_immediately') else None,
                                    "is_ofw": personal_info.is_ofw if hasattr(personal_info, 'is_ofw') else None,
                                    "ofw_country": personal_info.ofw_country if hasattr(personal_info, 'ofw_country') else None,
                                    "is_former_ofw": personal_info.is_former_ofw if hasattr(personal_info, 'is_former_ofw') else None,
                                    "former_ofw_country": personal_info.former_ofw_country if hasattr(personal_info, 'former_ofw_country') else None,
                                    "former_ofw_country_date_return": personal_info.former_ofw_country_date_return.strftime("%Y-%m-%d") if hasattr(personal_info, 'former_ofw_country_date_return') and personal_info.former_ofw_country_date_return else None,
                                    "is_4ps_beneficiary": personal_info.is_4ps_beneficiary if hasattr(personal_info, 'is_4ps_beneficiary') else None,
                                    "_4ps_household_id_no": personal_info._4ps_household_id_no if hasattr(personal_info, '_4ps_household_id_no') else None,
                                    "valid_id_url": personal_info.valid_id_url if hasattr(personal_info, 'valid_id_url') else None,
                                },
                                "job_preferences": {
                                        "country": job_preferences.country,
                                        "province": job_preferences.province,
                                        "municipality": job_preferences.municipality,
                                        "industry": job_preferences.industry,
                                        "preferred_occupation": job_preferences.preferred_occupation,
                                        "salary_range": f"{job_preferences.salary_from}-{job_preferences.salary_to}"
                                    },
                                "language_proficiencies": [
                                    {
                                        "language": lang.language,
                                        "can_read": lang.can_read,
                                        "can_write": lang.can_write,
                                        "can_speak": lang.can_speak,
                                        "can_understand": lang.can_understand
                                    } for lang in language_proficiencies
                                ],
                                "educational_background": [
                                    {
                                        "school_name": edu.school_name,
                                        "date_from": edu.date_from.strftime("%Y-%m-%d"),
                                        "date_to": edu.date_to.strftime("%Y-%m-%d") if edu.date_to else None,
                                        "degree_or_qualification": edu.degree_or_qualification,
                                        "field_of_study": edu.field_of_study,
                                        "program_duration_years": edu.program_duration
                                    } for edu in educational_backgrounds
                                ],
                                "other_trainings": [
                                    {
                                        "course_name": training.course_name,
                                        "start_date": training.start_date.strftime("%Y-%m-%d"),
                                        "end_date": training.end_date.strftime("%Y-%m-%d") if training.end_date else None,
                                        "training_institution": training.training_institution,
                                        "certificates_received": training.certificates_received,
                                        "hours_of_training": training.hours_of_training,
                                        "skills_acquired": training.skills_acquired
                                    } for training in other_trainings
                                ],
                                "professional_licenses": [
                                    {
                                        "license": license.license,
                                        "name": license.name,
                                        "date": license.date.strftime("%Y-%m-%d"),
                                        "valid_until": license.valid_until.strftime("%Y-%m-%d") if license.valid_until else None,
                                        "rating": license.rating
                                    } for license in professional_licenses
                                ],
                                "work_experiences": [
                                    {
                                        "company_name": exp.company_name,
                                        "company_address": exp.company_address,
                                        "position": exp.position,
                                        "employment_status": exp.employment_status,
                                        "date_start": exp.date_start.strftime("%Y-%m-%d"),
                                        "date_end": exp.date_end.strftime("%Y-%m-%d") if exp.date_end else None
                                    } for exp in work_experiences
                                ],
                                "other_skills": [
                                    {"skill": skill.skills} for skill in other_skills
                                ]
                            }
                        })
        # Return the list of combined user-job objects
        return jsonify({
            "success": True,
            "message": "All users and their applied scholarships retrieved successfully",
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
    if g.user.user_type not in ['ADMIN']:
        return jsonify({"error": "Unauthorized user type"}), 403

    try:
        # Query all users
        users = User.query.all()
        if not users:
            return jsonify({"message": "No users found"}), 404

        result = []
        for user in users:
        
            personal_info = user.jobseeker_student_personal_information
            job_preferences = user.jobseeker_student_job_preference
            language_proficiencies = user.jobseeker_student_language_proficiency
            educational_backgrounds = user.jobseeker_student_educational_background
            other_trainings = user.jobseeker_student_other_training
            professional_licenses = user.jobseeker_student_professional_license
            work_experiences = user.jobseeker_student_work_experience
            other_skills = user.jobseeker_student_other_skills
            
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
                            "company_name": training_posting.company_name if hasattr(training_posting, 'company_name') and training_posting.employer else "Unknown Company",
                            "training_description": training_posting.training_description,
                            "slots": training_posting.slots,
                            "remaining_slots": training_posting.slots - training_posting.occupied_slots,
                            "remarks": training_posting.remarks,
                            "applied_at": application.created_at.strftime("%Y-%m-%d"),
                            "updated_at": application.updated_at.strftime("%Y-%m-%d") if application.updated_at else None,
                            "expired_at": training_posting.expiration_date.strftime("%Y-%m-%d") if training_posting.expiration_date else None,
                            "application_status": application.status,
                            "user_details": {
                                "fullname": f"{personal_info.first_name} {personal_info.last_name}" if personal_info else "Unknown",
                                "user_id": user.user_id,
                                "username": user.username,
                                "email": user.email,
                                "user_type": user.user_type,
                                "personal_information": {
                                    "prefix": personal_info.prefix if hasattr(personal_info, 'prefix') else None,
                                    "first_name": personal_info.first_name if hasattr(personal_info, 'first_name') else None,
                                    "middle_name": personal_info.middle_name if hasattr(personal_info, 'middle_name') else None,
                                    "last_name": personal_info.last_name if hasattr(personal_info, 'last_name') else None,
                                    "suffix": personal_info.suffix if hasattr(personal_info, 'suffix') else None,
                                    "sex": personal_info.sex if hasattr(personal_info, 'sex') else None,
                                    "date_of_birth": personal_info.date_of_birth.strftime("%Y-%m-%d") if hasattr(personal_info, 'date_of_birth') and personal_info.date_of_birth else None,
                                    "place_of_birth": personal_info.place_of_birth if hasattr(personal_info, 'place_of_birth') else None,
                                    "civil_status": personal_info.civil_status if hasattr(personal_info, 'civil_status') else None,
                                    "height": personal_info.height if hasattr(personal_info, 'height') else None,
                                    "weight": personal_info.weight if hasattr(personal_info, 'weight') else None,
                                    "religion": personal_info.religion if hasattr(personal_info, 'religion') else None,
                                    "temporary_address": {
                                        "country": personal_info.temporary_country if hasattr(personal_info, 'temporary_country') else None,
                                        "province": personal_info.temporary_province if hasattr(personal_info, 'temporary_province') else None,
                                        "municipality": personal_info.temporary_municipality if hasattr(personal_info, 'temporary_municipality') else None,
                                        "zip_code": personal_info.temporary_zip_code if hasattr(personal_info, 'temporary_zip_code') else None,
                                        "barangay": personal_info.temporary_barangay if hasattr(personal_info, 'temporary_barangay') else None,
                                        "house_no_street_village": personal_info.temporary_house_no_street_village if hasattr(personal_info, 'temporary_house_no_street_village') else None,
                                    },
                                    "permanent_address": {
                                        "country": personal_info.permanent_country if hasattr(personal_info, 'permanent_country') else None,
                                        "province": personal_info.permanent_province if hasattr(personal_info, 'permanent_province') else None,
                                        "municipality": personal_info.permanent_municipality if hasattr(personal_info, 'permanent_municipality') else None,
                                        "zip_code": personal_info.permanent_zip_code if hasattr(personal_info, 'permanent_zip_code') else None,
                                        "barangay": personal_info.permanent_barangay if hasattr(personal_info, 'permanent_barangay') else None,
                                        "house_no_street_village": personal_info.permanent_house_no_street_village if hasattr(personal_info, 'permanent_house_no_street_village') else None,
                                    },
                                    "contact_number": personal_info.cellphone_number if hasattr(personal_info, 'cellphone_number') else None,
                                    "landline_number": personal_info.landline_number if hasattr(personal_info, 'landline_number') else None,
                                    "tin": personal_info.tin if hasattr(personal_info, 'tin') else None,
                                    "sss_gsis_number": personal_info.sss_gsis_number if hasattr(personal_info, 'sss_gsis_number') else None,
                                    "pag_ibig_number": personal_info.pag_ibig_number if hasattr(personal_info, 'pag_ibig_number') else None,
                                    "phil_health_no": personal_info.phil_health_no if hasattr(personal_info, 'phil_health_no') else None,
                                    "disability": personal_info.disability if hasattr(personal_info, 'disability') else None,
                                    "employment_status": personal_info.employment_status if hasattr(personal_info, 'employment_status') else None,
                                    "is_looking_for_work": personal_info.is_looking_for_work if hasattr(personal_info, 'is_looking_for_work') else None,
                                    "since_when_looking_for_work": personal_info.since_when_looking_for_work.strftime("%Y-%m-%d") if hasattr(personal_info, 'since_when_looking_for_work') and personal_info.since_when_looking_for_work else None,
                                    "is_willing_to_work_immediately": personal_info.is_willing_to_work_immediately if hasattr(personal_info, 'is_willing_to_work_immediately') else None,
                                    "is_ofw": personal_info.is_ofw if hasattr(personal_info, 'is_ofw') else None,
                                    "ofw_country": personal_info.ofw_country if hasattr(personal_info, 'ofw_country') else None,
                                    "is_former_ofw": personal_info.is_former_ofw if hasattr(personal_info, 'is_former_ofw') else None,
                                    "former_ofw_country": personal_info.former_ofw_country if hasattr(personal_info, 'former_ofw_country') else None,
                                    "former_ofw_country_date_return": personal_info.former_ofw_country_date_return.strftime("%Y-%m-%d") if hasattr(personal_info, 'former_ofw_country_date_return') and personal_info.former_ofw_country_date_return else None,
                                    "is_4ps_beneficiary": personal_info.is_4ps_beneficiary if hasattr(personal_info, 'is_4ps_beneficiary') else None,
                                    "_4ps_household_id_no": personal_info._4ps_household_id_no if hasattr(personal_info, '_4ps_household_id_no') else None,
                                    "valid_id_url": personal_info.valid_id_url if hasattr(personal_info, 'valid_id_url') else None,
                                },
                                "job_preferences": {
                                        "country": job_preferences.country,
                                        "province": job_preferences.province,
                                        "municipality": job_preferences.municipality,
                                        "industry": job_preferences.industry,
                                        "preferred_occupation": job_preferences.preferred_occupation,
                                        "salary_range": f"{job_preferences.salary_from}-{job_preferences.salary_to}"
                                    },
                                "language_proficiencies": [
                                    {
                                        "language": lang.language,
                                        "can_read": lang.can_read,
                                        "can_write": lang.can_write,
                                        "can_speak": lang.can_speak,
                                        "can_understand": lang.can_understand
                                    } for lang in language_proficiencies
                                ],
                                "educational_background": [
                                    {
                                        "school_name": edu.school_name,
                                        "date_from": edu.date_from.strftime("%Y-%m-%d"),
                                        "date_to": edu.date_to.strftime("%Y-%m-%d") if edu.date_to else None,
                                        "degree_or_qualification": edu.degree_or_qualification,
                                        "field_of_study": edu.field_of_study,
                                        "program_duration_years": edu.program_duration
                                    } for edu in educational_backgrounds
                                ],
                                "other_trainings": [
                                    {
                                        "course_name": training.course_name,
                                        "start_date": training.start_date.strftime("%Y-%m-%d"),
                                        "end_date": training.end_date.strftime("%Y-%m-%d") if training.end_date else None,
                                        "training_institution": training.training_institution,
                                        "certificates_received": training.certificates_received,
                                        "hours_of_training": training.hours_of_training,
                                        "skills_acquired": training.skills_acquired
                                    } for training in other_trainings
                                ],
                                "professional_licenses": [
                                    {
                                        "license": license.license,
                                        "name": license.name,
                                        "date": license.date.strftime("%Y-%m-%d"),
                                        "valid_until": license.valid_until.strftime("%Y-%m-%d") if license.valid_until else None,
                                        "rating": license.rating
                                    } for license in professional_licenses
                                ],
                                "work_experiences": [
                                    {
                                        "company_name": exp.company_name,
                                        "company_address": exp.company_address,
                                        "position": exp.position,
                                        "employment_status": exp.employment_status,
                                        "date_start": exp.date_start.strftime("%Y-%m-%d"),
                                        "date_end": exp.date_end.strftime("%Y-%m-%d") if exp.date_end else None
                                    } for exp in work_experiences
                                ],
                                "other_skills": [
                                    {"skill": skill.skills} for skill in other_skills
                                ]
                            }
                        })
        # Return the list of combined user-job objects
        return jsonify({
            "success": True,
            "message": "All users and their applied trainings retrieved successfully",
            "applied_trainings": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500


#===========================================================================================================================================#
#                                                       ADMIN OR EMPLOYER USERS APPLICATION APPROVAL
#===========================================================================================================================================#
# UPDATE TRAINING STATUS
@admin.route('/update-training-status', methods=['PUT'])
@auth.login_required
def update_training_status():
    """
    Route for updating the status of a training application.
    Requires authentication.
    Only authorized users (e.g., employers or admins) can update the status.
    """
    
    # Check if the user is authorized to update the status
    if g.user.user_type not in ['ADMIN', 'EMPLOYER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    if 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    # Allowed statuses
    allowed_statuses = ['approved', 'declined', 'applied', 'hired']
    if data['status'] not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed values are {allowed_statuses}"}), 400
    
    # Fetch the training application by ID
    application = StudentJobseekerApplyTrainings.query.get(data['application_id'])
    
    if not application:
        return jsonify({"error": "Training application not found"}), 404
    
    if application.user_apply_trainings.occupied_slots >= application.user_apply_trainings.slots:
        return jsonify({"error": "This training has already been filled."}), 400
    
    if application.user_apply_trainings.status == 'expired':
        return jsonify({"error": "This training has already expired."}), 400
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_trainings.occupied_slots += 1 if data['status'] == 'hired' else 0  # Increment occupied slots if hired
        application.user_apply_trainings.updated_at = db.func.current_timestamp()  # Update the timestamp for the training posting
        application.remarks = data.get('admin_remarks', None)  # Optional remarks field for admin
        application.remarks = data.get('employer_remarks', None)  # Optional remarks field for employer

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Training application status updated successfully",
            "application_id": application.apply_training_id,
            "new_status": application.status
        }), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# UPDATE SCHOLARSHIP STATUS
@admin.route('/update-scholarship-status', methods=['PUT'])
@auth.login_required
def update_scholarship_status():
    """
    Route for updating the status of a scholarship application.
    Requires authentication.
    Only authorized users (e.g., employers or admins) can update the status.
    """
    
    # Check if the user is authorized to update the status
    if g.user.user_type not in ['ADMIN', 'EMPLOYER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    if 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    # Allowed statuses
    allowed_statuses = ['approved', 'declined', 'applied', 'hired']
    if data['status'] not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed values are {allowed_statuses}"}), 400
    
    # Fetch the scholarship application by ID
    application = StudentJobseekerApplyScholarships.query.get(data['application_id'])
    
    if not application:
        return jsonify({"error": "Scholarship application not found"}), 404
    
    if application.user_apply_scholarships.occupied_slots >= application.user_apply_scholarships.slots:
        return jsonify({"error": "This scholarship has already been filled."}), 400
    
    if application.user_apply_scholarships.status == 'expired':
        return jsonify({"error": "This scholarship has already expired."}), 400
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_scholarships.occupied_slots += 1 if data['status'] == 'hired' else 0  # Increment occupied slots if hired
        application.user_apply_scholarships.updated_at = db.func.current_timestamp()  # Update the timestamp for the scholarship posting
        application.remarks = data.get('admin_remarks', None)  # Optional remarks field for admin
        application.remarks = data.get('employer_remarks', None)  # Optional remarks field for employer

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Scholarship application status updated successfully",
            "application_id": application.apply_scholarship_id,
            "new_status": application.status
        }), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

# UPDATE JOB STATUS
@admin.route('/update-job-status', methods=['PUT'])
@auth.login_required
def update_job_status():
    """
    Route for updating the status of a job application.
    Requires authentication.
    Only authorized users (e.g., employers or admins) can update the status.
    """
    # Get the user ID from authentication
    
    # Check if the user is authorized to update the status
    if g.user.user_type not in ['ADMIN', 'EMPLOYER']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    # Get request data
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    if 'status' not in data:
        return jsonify({"error": "Status is required"}), 400
    
    # Allowed statuses
    allowed_statuses = ['approved', 'declined', 'applied', 'hired']
    if data['status'] not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Allowed values are {allowed_statuses}"}), 400
    
    # Fetch the job application by ID
    application = StudentJobseekerApplyJobs.query.get(data['application_id'])
    
    if not application:
        return jsonify({"error": "Job application not found"}), 404
    
    if application.user_apply_job.no_of_vacancies <= 0:
        return jsonify({"error": "This job has already been filled."}), 400

    if application.user_apply_job.status == 'expired':
        return jsonify({"error": "This job has already expired."}), 400
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_job.no_of_vacancies -= 1 if data['status'] == 'hired' else 0  # Increment occupied slots if hired
        application.user_apply_job.updated_at = db.func.current_timestamp()  # Update the timestamp for the job posting
        application.remarks = data.get('admin_remarks', None)  # Optional remarks field for admin
        application.remarks = data.get('employer_remarks', None)  # Optional remarks field for employer

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Job application status updated successfully",
            "application_id": application.apply_job_id,
            "new_status": application.status
        }), 200
    
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

#===========================================================================================================================================#
#                                                       ADMIN GET ALL EMPLOYERS AND COMPANY DETAILS
#===========================================================================================================================================#
@admin.route('/get-employer-details', methods=['GET'])
@auth.login_required
def get_employer_details():
    """
    Route to retrieve all employers and their company details.
    Requires authentication.
    """
    try:
        # Query all users with user_type "EMPLOYER"
        employers = User.query.filter_by(user_type="EMPLOYER").all()
        if not employers:
            return jsonify({"message": "No employers found"}), 404
        
        if g.user.user_type not in ['ADMIN']:
            return jsonify({"error": "Unauthorized user type"}), 403

        result = []
        for employer in employers:
            # Get the employer's personal information
            personal_info = employer.employer_personal_information

            # Construct employer details
            employer_details = {
                "user_id": employer.user_id,
                "username": employer.username,
                "email": employer.email,
                "user_type": employer.user_type,
                "personal_information": {
                    "prefix": personal_info.prefix if hasattr(personal_info, 'prefix') else None,
                    "first_name": personal_info.first_name if hasattr(personal_info, 'first_name') else None,
                    "middle_name": personal_info.middle_name if hasattr(personal_info, 'middle_name') else None,
                    "last_name": personal_info.last_name if hasattr(personal_info, 'last_name') else None,
                    "suffix": personal_info.suffix if hasattr(personal_info, 'suffix') else None,
                    "cellphone_number": personal_info.cellphone_number if hasattr(personal_info, 'cellphone_number') else None,
                    "landline_number": personal_info.landline_number if hasattr(personal_info, 'landline_number') else None,
                    "valid_id_url": personal_info.valid_id_url if hasattr(personal_info, 'valid_id_url') else None,
                    "temporary_address": {
                        "country": personal_info.temporary_country if hasattr(personal_info, 'temporary_country') else None,
                        "province": personal_info.temporary_province if hasattr(personal_info, 'temporary_province') else None,
                        "municipality": personal_info.temporary_municipality if hasattr(personal_info, 'temporary_municipality') else None,
                        "zip_code": personal_info.temporary_zip_code if hasattr(personal_info, 'temporary_zip_code') else None,
                        "barangay": personal_info.temporary_barangay if hasattr(personal_info, 'temporary_barangay') else None,
                        "house_no_street_village": personal_info.temporary_house_no_street_village if hasattr(personal_info, 'temporary_house_no_street_village') else None,
                    },
                    "permanent_address": {
                        "country": personal_info.permanent_country if hasattr(personal_info, 'permanent_country') else None,
                        "province": personal_info.permanent_province if hasattr(personal_info, 'permanent_province') else None,
                        "municipality": personal_info.permanent_municipality if hasattr(personal_info, 'permanent_municipality') else None,
                        "zip_code": personal_info.permanent_zip_code if hasattr(personal_info, 'permanent_zip_code') else None,
                        "barangay": personal_info.permanent_barangay if hasattr(personal_info, 'permanent_barangay') else None,
                        "house_no_street_village": personal_info.permanent_house_no_street_village if hasattr(personal_info, 'permanent_house_no_street_village') else None,
                    },
                },
                "company_details": {
                    "company_name": personal_info.company_name if hasattr(personal_info, 'company_name') else None,
                    "company_type": personal_info.company_type if hasattr(personal_info, 'company_type') else None,
                    "company_classification": personal_info.company_classification if hasattr(personal_info, 'company_classification') else None,
                    "company_industry": personal_info.company_industry if hasattr(personal_info, 'company_industry') else None,
                    "company_workforce": personal_info.company_workforce if hasattr(personal_info, 'company_workforce') else None,
                }
            }
            result.append(employer_details)

        return jsonify({
            "success": True,
            "message": "All employers and their company details retrieved successfully",
            "employers": result
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
#===========================================================================================================================================#
#                                                       ADMIN ADD REMARKS TO JOBS, TRAININGS, AND SCHOLARSHIPS
#===========================================================================================================================================#
@admin.route('/update-remarks', methods=['PUT'])
@auth.login_required
def update_remarks():
    """
    Update remarks for a specific job posting, training posting, or scholarship posting.
    
    :return: JSON response indicating success or failure.
    """
    if g.user.user_type not in ['ADMIN']:
        return jsonify({"error": "Unauthorized user type"}), 403
    # Extract data from the request body
    data = request.get_json()
    remarks = data.get('remarks')
    post_id = data.get('post_id')
    post_type = data.get('post_type')

    # Validate required fields
    if not remarks:
        return jsonify({"error": "Remarks field is required"}), 400
    if not post_id:
        return jsonify({"error": "Post ID is required"}), 400
    if not post_type:
        return jsonify({"error": "Post type is required"}), 400

    # Map post_type to the appropriate model
    if post_type == 'job':
        model = EmployerJobPosting
    elif post_type == 'training':
        model = EmployerTrainingPosting
    elif post_type == 'scholarship':
        model = EmployerScholarshipPosting
    else:
        return jsonify({"error": "Invalid post type. Must be 'job', 'training', or 'scholarship'."}), 400

    # Find the record by ID
    record = model.query.get(post_id)
    if not record:
        return jsonify({"error": f"{post_type.capitalize()} posting with ID {post_id} not found"}), 404

    # Update the remarks field
    record.remarks = remarks
    db.session.commit()

    return jsonify({
        "message": f"Remarks updated successfully for {post_type} posting with ID {post_id}",
        "updated_data": {
            "id": post_id,
            "remarks": remarks
        }
    }), 200

@admin.route('/approve-company-information', methods=['PUT'])
@auth.login_required
def add_remarks():
    """
    Route to add or update admin remarks for a specific company.
    Expects JSON payload with the 'admin_remarks' field.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        required_fields = ['admin_remarks', 'company_id', 'status']

        if g.user.user_type not in ['ADMIN']:
            return jsonify({"error": "Unauthorized user type"}), 403

        if not data or not all(field in data for field in required_fields):
            raise BadRequest("Missing required fields: admin_remarks, company_id, status")

        # Query the database for the company information
        company_info = db.session.query(EmployerCompanyInformation).get(data['company_id'])

        if not company_info:
            return jsonify({"error": "Company information not found"}), 404

        # Update the admin remarks
        company_info.admin_remarks = data['admin_remarks']
        company_info.status = data['status']
        company_info.updated_at = db.func.current_timestamp()

        # Commit the changes to the database
        db.session.commit()

        # Return success response
        return jsonify({
            "message": "Admin remarks updated successfully",
            "company_info_id": company_info.employer_companyinfo_id,
            "admin_remarks": company_info.admin_remarks
        }), 200

    except BadRequest as e:
        # Handle missing or invalid fields
        return jsonify({"error": str(e)}), 400

    except NoResultFound:
        # Handle case where no company information is found
        return jsonify({"error": "Company information not found"}), 404

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@admin.route('/get-all-company-information', methods=['GET'])
@auth.login_required
def get_all_company_information():
    """
    Route to retrieve all company information.
    This route is intended for administrative use.
    Only users with 'ADMIN' privileges can access this route.
    """
    try:
        # Check if the authenticated user has ADMIN privileges
        if g.user.user_type != 'ADMIN':
            return jsonify({"error": "Unauthorized access"}), 403

        # Query all company information from the database
        all_company_info = EmployerCompanyInformation.query.all()

        # Serialize the company information into a list of dictionaries
        company_data_list = [
            {
                "employer_companyinfo_id": info.employer_companyinfo_id,
                "user_id": info.user_id,
                "company_name": info.company_name,
                "company_email": info.company_email,
                "company_industry": info.company_industry,
                "company_type": info.company_type,
                "company_total_workforce": info.company_total_workforce,
                "company_country": info.company_country,
                "company_address": info.company_address,
                "company_house_no_street": info.company_house_no_street,
                "company_postal_code": info.company_postal_code,
                "company_website": info.company_website,
                "logo_image_path": info.logo_image_path,
                "business_permit_path": info.business_permit_path,
                "bir_form_path": info.bir_form_path,
                "poea_file_path": info.poea_file_path,
                "philhealth_file_path": info.philhealth_file_path,
                "dole_certificate_path": info.dole_certificate_path,
                "admin_remarks": info.admin_remarks,
                "status": info.status,
                "created_at": info.created_at.isoformat(),
                "updated_at": info.updated_at.isoformat()
            }
            for info in all_company_info
        ]

        # Return the list of company information as JSON
        return jsonify({
            "message": "All company information retrieved successfully",
            "company_information": company_data_list
        }), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# ===========================================================================================================================================#
#                                                       ADMIN ADD ANNOUNCEMENTS
# ===========================================================================================================================================#
@admin.route('/add-announcement', methods=['POST'])
@auth.login_required
def add_announcement():
    """
    Route to add a new announcement.
    Expects JSON payload with the following fields:
    - title: str (required)
    - details: str (required)
    - target_audience: list of str (required, e.g., ["JOBSEEKER", "EMPLOYER"])
    - expiration_date: str (ISO 8601 format, e.g., "2023-12-31T23:59:59")
    """
    try:
        # Parse JSON data from the request
        uid = g.user.user_id
        data = request.get_json()

        if g.user.user_type not in ['ADMIN']:
            return jsonify({"error": "Unauthorized user type"}), 403

        # Validate required fields
        required_fields = ['title', 'details', 'target_audience', 'expiration_date']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Convert expiration_date string to datetime object
        try:
            expiration_date = datetime.fromisoformat(data['expiration_date'])
        except ValueError:
            return jsonify({"error": "Invalid expiration_date format. Use ISO 8601 (e.g., '2023-12-31T23:59:59')"}), 400

        # Validate target_audience is a list
        if not isinstance(data['target_audience'], list):
            return jsonify({"error": "target_audience must be a list of strings"}), 400

        # Convert target_audience list to a comma-separated string
        target_audience_str = ','.join(data['target_audience'])

        # Create a new Announcement instance
        new_announcement = Announcement(
            user_id = uid,
            title=data['title'],
            details=data['details'],
            target_audience=target_audience_str,
            expiration_date=expiration_date
        )

        # Add and commit the new announcement to the database
        db.session.add(new_announcement)
        db.session.commit()

        # Return success response
        return jsonify({
            "message": "Announcement added successfully",
            "announcement_id": new_announcement.announcement_id
        }), 201

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

@admin.route('/get-all-announcements', methods=['GET'])
@auth.login_required
def get_all_announcements():
    """
   
    Route to retrieve all announcements.
    Checks if announcements are expired and updates their status accordingly.
    Returns a list of announcements in JSON format.
    """
    try:
        # Query all announcements from the database
        announcements = Announcement.query.all()

        # Get the current time
        current_time = datetime.utcnow()

        if g.user.user_type not in ['ADMIN']:
            return jsonify({"error": "Unauthorized user type"}), 403

        # Format the announcements into a list of dictionaries
        announcements_list = []
        for announcement in announcements:
            # Check if the announcement has expired
            if announcement.expiration_date < current_time and announcement.status != 'expired':
                announcement.status = 'expired'
                db.session.commit()  # Update the status in the database

            # Add the announcement to the response list
            announcements_list.append({
                "announcement_id": announcement.announcement_id,
                "title": announcement.title,
                "details": announcement.details,
                "target_audience": announcement.target_audience.split(','),
                "status": announcement.status,
                "expiration_date":convert(announcement.expiration_date),
                "created_at": convert(announcement.created_at),
                "updated_at": convert(announcement.updated_at)
            })
    
        return jsonify({
            "success": True,
            "announcements": announcements_list
        }), 200

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

@admin.route('/get-announcements', methods=['GET'])
@auth.login_required
def get_user_announcements():
    """
   
    Route to retrieve all announcements.
    Checks if announcements are expired and updates their status accordingly.
    Returns a list of announcements in JSON format.
    """
    try:
        # Query all announcements from the database
        announcements = Announcement.query.all()

        # Get the current time
        current_time = datetime.utcnow()

        if g.user.user_type in ['ADMIN']:
            return jsonify({"error": "Unauthorized user type"}), 403

        # Format the announcements into a list of dictionaries
        announcements_list = []
        for announcement in announcements:
            # Check if the announcement has expired
            if announcement.expiration_date < current_time and announcement.status != 'expired':
                announcement.status = 'expired'
                db.session.commit()  # Update the status in the database

            # Add the announcement to the response list
            if g.user.user_type in announcement.target_audience.split(','):
                announcements_list.append({
                    "announcement_id": announcement.announcement_id,
                    "title": announcement.title,
                    "details": announcement.details,
                    "target_audience": announcement.target_audience.split(','),
                    "status": announcement.status,
                    "expiration_date":convert(announcement.expiration_date),
                    "created_at": convert(announcement.created_at),
                    "updated_at": convert(announcement.updated_at)
                })

        return jsonify({
            "success": True,
            "announcements": announcements_list
        }), 200

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": "An error occurred", "details": str(e)}), 500


@admin.route('/create-user', methods=['POST'])
@auth.login_required
def create_user():
    """
    Route to create a new user (admin only).
    Accepts both JSON and form-data formats.
    Required fields: username, email, password, user_type
    """
    try:
        # Only allow admin to create users
        if getattr(g.user, "user_type", "").upper() != "ADMIN":
            return jsonify({"error": "Unauthorized. Only admin can create users."}), 403

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

        # Create new user with normalized user_type
        user_type = str(data['user_type']).upper()
        access_level = 2 if user_type == "ADMIN" else 1 if user_type == "EMPLOYER" else 0

        user = User(
            username=data['username'],
            email=data['email'],
            user_type=user_type,
            access_level=access_level
        )
        user.hash_password(data['password'])
        
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully", 
            "user_id": user.user_id
        }), 201

    except Exception as e:
        db.session.rollback()
        print("Error in /api/create-user:", str(e))
        return jsonify({"error": str(e)}), 500

# ===========================================================================================================================================#
#                                                       ADMIN PLACEMENT REPORTS
# ===========================================================================================================================================#
@admin.route('/placement-reports', methods=['GET'])
@auth.login_required
def get_hired_applicants():
    """Retrieve all hired applicants with minimal required fields"""
    if g.user.user_type not in ['ADMIN']:
        return jsonify({"error": "Unauthorized user type"}), 403
    
    try:
        # Query hired applications
        applications = StudentJobseekerApplyJobs.query.filter_by(status='hired').all()
        
        result = []
        for app in applications:
            job = app.user_apply_job  # Get related job posting
            employer = job.user  # Get employer user
            company = employer.employer_company_information[0] if employer.employer_company_information else None
            
            result.append({
                "applicant_firstname": app.user.jobseeker_student_personal_information.first_name if app.user.jobseeker_student_personal_information else None,
                "position_hired": job.job_title if job else None,
                "applicant_lastname": app.user.jobseeker_student_personal_information.last_name if app.user.jobseeker_student_personal_information else None,
                "employer_fullname": f"{employer.employer_personal_information[0].first_name} {employer.employer_personal_information[0].last_name}" if employer.employer_personal_information else None,
                "job_country": job.country if job else None,
                "deployment_country": job.Deployment_region if job.Deployment_region else None,
                "salary": f"100000",
                "contract_period": job.Contract_period if job.Contract_period else None,
                "company_name": company.company_name if company else "N/A",
                "local_overseas": job.local_or_overseas if job.local_or_overseas else None,
                "remarks": app.employer_remarks or "No remarks",
                "created_at": convert(app.created_at) if app.created_at else None,
                "updated_at": convert(app.updated_at) if app.updated_at else None,
            })
        
        return jsonify({
            "success": True,
            "count": len(result),
            "data": result
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================================================================================================================================#
#                                                       ADMIN JOBSEEKER STATISTICS
# ===========================================================================================================================================#
@admin.route('/jobsekeer_bar_chart', methods=['GET'])
@auth.login_required
def bar_chart():
    # Get the current authenticated user
    current_user = auth.current_user()
    
    # Query to count applications by employment status
    # Using only the PersonalInformation table
    status_counts = (
        db.session.query(
            PersonalInformation.employment_status.label('status'),
            func.count(PersonalInformation.personal_info_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(PersonalInformation.employment_status)
        .all()
    )
    
    # Format the data for visualization
    labels = [item.status for item in status_counts]
    data = [item.count for item in status_counts]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,  # X-axis: Employment status categories
            "datasets": [
                {
                    "label": "Number of Job Seekers",
                    "data": data,  # Y-axis: Count of job seekers
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# A. Job Seeker Distribution by Job Title
@admin.route('/job_seekers_by_job_title', methods=['GET'])
@auth.login_required
def job_seekers_by_job_title():
    # Query to count job seekers by preferred occupation
    job_title_counts = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(JobPreference.preferred_occupation)
        .order_by(desc('count'))
        .all()
    )
    
    # Format the data for visualization
    labels = [item.job_title for item in job_title_counts]
    data = [item.count for item in job_title_counts]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,  # X-axis: Job titles
            "datasets": [
                {
                    "label": "Number of Job Seekers",
                    "data": data,  # Y-axis: Count of job seekers
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# B. Most In-Demand Job Titles (Using real job posting data)
@admin.route('/most_in_demand_job_titles', methods=['GET'])
@auth.login_required
def most_in_demand_job_titles():
    # Query actual job posting data instead of using job preferences as a proxy
    job_demand = (
        db.session.query(
            EmployerJobPosting.job_title.label('job_title'),
            func.count(EmployerJobPosting.employer_jobpost_id).label('demand_score')
        )
        .filter(EmployerJobPosting.status == 'approved')  # Only count approved job postings
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow())  # Only active jobs
        .group_by(EmployerJobPosting.job_title)
        .order_by(desc('demand_score'))
        .limit(10)  # Top 10 most in-demand
        .all()
    )
    
    # Format the data for visualization
    labels = [item.job_title for item in job_demand]
    data = [item.demand_score for item in job_demand]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,  # Y-axis: Job titles
            "datasets": [
                {
                    "label": "Number of Active Job Postings",
                    "data": data,  # X-axis: Demand score
                    "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
        }
    }
    
    return jsonify(response)

# C. Job Posting Trends Over Time (Replacing mock data)
@admin.route('/job_postings_trend', methods=['GET'])
@auth.login_required
def job_postings_trend():
    # Query to group job postings by month
    from sqlalchemy import func, extract
    
    # Query to get job posting counts by month for the past 6 months
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    job_postings_by_month = (
        db.session.query(
            func.date_trunc('month', EmployerJobPosting.created_at).label('month'),
            func.count(EmployerJobPosting.employer_jobpost_id).label('count')
        )
        .filter(EmployerJobPosting.created_at >= six_months_ago)
        .group_by('month')
        .order_by('month')
        .all()
    )
    
    # Format the data for visualization
    months = [item.month.strftime('%Y-%m') for item in job_postings_by_month]
    counts = [item.count for item in job_postings_by_month]
    
    # Get the top 5 job titles for the trend lines
    top_job_titles = (
        db.session.query(EmployerJobPosting.job_title)
        .group_by(EmployerJobPosting.job_title)
        .order_by(desc(func.count(EmployerJobPosting.employer_jobpost_id)))
        .limit(5)
        .all()
    )
    
    job_titles = [item.job_title for item in top_job_titles]
    
    # Create datasets for each job title
    datasets = []
    colors = [
        "rgba(54, 162, 235, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(153, 102, 255, 1)",
        "rgba(255, 159, 64, 1)"
    ]
    
    # First dataset is for overall job posting count
    datasets.append({
        "label": "All Job Postings",
        "data": counts,
        "borderColor": "rgba(0, 0, 0, 1)",
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "pointBackgroundColor": "rgba(0, 0, 0, 1)",
        "pointBorderColor": "#fff",
        "pointHoverBackgroundColor": "#fff",
        "pointHoverBorderColor": "rgba(0, 0, 0, 1)",
        "tension": 0.1
    })
    
    # Add datasets for each top job title
    for i, job_title in enumerate(job_titles):
        # Query to get job posting counts by month for this specific job title
        job_title_trend = (
            db.session.query(
                func.date_trunc('month', EmployerJobPosting.created_at).label('month'),
                func.count(EmployerJobPosting.employer_jobpost_id).label('count')
            )
            .filter(EmployerJobPosting.created_at >= six_months_ago)
            .filter(EmployerJobPosting.job_title == job_title)
            .group_by('month')
            .order_by('month')
            .all()
        )
        
        # Create a dictionary to match months with counts
        trend_data = {item.month.strftime('%Y-%m'): item.count for item in job_title_trend}
        
        # Ensure all months have data points (use 0 if none exists)
        job_title_data = [trend_data.get(month, 0) for month in months]
        
        datasets.append({
            "label": job_title,
            "data": job_title_data,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "pointBackgroundColor": colors[i % len(colors)],
            "pointBorderColor": "#fff",
            "pointHoverBackgroundColor": "#fff",
            "pointHoverBorderColor": colors[i % len(colors)],
            "tension": 0.1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": months,  # X-axis: Months
            "datasets": datasets  # Multiple lines for each job title
        }
    }
    
    return jsonify(response)

# D. Employment Metrics Table
@admin.route('/employment_metrics', methods=['GET'])
@auth.login_required
def employment_metrics():
    # Total job seekers
    total_job_seekers = db.session.query(func.count(PersonalInformation.user_id))\
        .filter(PersonalInformation.is_looking_for_work == True).scalar()
    
    # Employment status breakdown
    employment_status_counts = (
        db.session.query(
            PersonalInformation.employment_status.label('status'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(PersonalInformation.employment_status)
        .all()
    )
    
    # Calculate willing to work immediately
    willing_to_work = db.session.query(func.count(PersonalInformation.user_id))\
        .filter(PersonalInformation.is_looking_for_work == True)\
        .filter(PersonalInformation.is_willing_to_work_immediately == True).scalar()
    
    # Prepare metrics with mock trend data (in a real app, compare with previous period)
    metrics = [
        {
            "metric_name": "Total Job Seekers",
            "metric_value": total_job_seekers,
            "trend_direction": "up",  # Mock trend
            "change_percent": "5.2%"   # Mock change
        }
    ]
    
    # Add employment status metrics
    for status in employment_status_counts:
        metrics.append({
            "metric_name": f"{status.status}",
            "metric_value": status.count,
            "trend_direction": "up" if status.status == "Unemployed" else "down",  # Mock trend
            "change_percent": "3.1%"  # Mock change
        })
    
    # Add willing to work metric
    metrics.append({
        "metric_name": "Ready to Work",
        "metric_value": willing_to_work,
        "trend_direction": "up",  # Mock trend
        "change_percent": "7.8%"  # Mock change
    })
    
    return jsonify({"metrics": metrics})

# E. Overall Sex Distribution
@admin.route('/sex_distribution', methods=['GET'])
@auth.login_required
def sex_distribution():
    # Query to count job seekers by sex
    sex_counts = (
        db.session.query(
            PersonalInformation.sex.label('sex'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(PersonalInformation.sex)
        .all()
    )
    
    # Format the data for visualization
    labels = [item.sex for item in sex_counts]
    data = [item.count for item in sex_counts]
    
    # Color coding for genders
    background_colors = ["rgba(54, 162, 235, 0.6)", "rgba(75, 192, 192, 0.6)"]
    border_colors = ["rgba(54, 162, 235, 1)", "rgba(75, 192, 192, 1)"]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": background_colors[:len(labels)],
                    "borderColor": border_colors[:len(labels)],
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# F. Job Preferences by Sex
@admin.route('/job_preferences_by_sex', methods=['GET'])
@auth.login_required
def job_preferences_by_sex():
    # Query to count job preferences by sex and job title
    job_prefs_by_sex = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            PersonalInformation.sex.label('sex'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(JobPreference.preferred_occupation, PersonalInformation.sex)
        .order_by(desc('count'))
        .all()
    )
    
    # Process data for grouped bar chart
    job_titles = list(set([item.job_title for item in job_prefs_by_sex]))
    sexes = list(set([item.sex for item in job_prefs_by_sex]))
    
    # Create datasets for each sex
    datasets = []
    for sex in sexes:
        data = []
        for job_title in job_titles:
            # Find count for this job_title and sex
            count_item = next((item for item in job_prefs_by_sex if item.job_title == job_title and item.sex == sex), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        # Color coding
        color = "rgba(54, 162, 235, 0.6)" if sex == "Male" else "rgba(75, 192, 192, 0.6)"
        border_color = "rgba(54, 162, 235, 1)" if sex == "Male" else "rgba(75, 192, 192, 1)"
        
        datasets.append({
            "label": sex,
            "data": data,
            "backgroundColor": color,
            "borderColor": border_color,
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": job_titles,  # X-axis: Job titles
            "datasets": datasets   # Grouped by sex
        }
    }
    
    return jsonify(response)

# G. Gender Distribution by Municipality
@admin.route('/gender_by_municipality', methods=['GET'])
@auth.login_required
def gender_by_municipality():
    # Query to count job seekers by municipality and sex
    gender_by_muni = (
        db.session.query(
            PersonalInformation.permanent_municipality.label('municipality'),
            PersonalInformation.sex.label('sex'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .filter(PersonalInformation.permanent_municipality != None)
        .group_by(PersonalInformation.permanent_municipality, PersonalInformation.sex)
        .order_by(PersonalInformation.permanent_municipality, PersonalInformation.sex)
        .all()
    )
    
    # Process data for grouped bar chart
    municipalities = list(set([item.municipality for item in gender_by_muni]))
    sexes = list(set([item.sex for item in gender_by_muni]))
    
    # Create datasets for each sex
    datasets = []
    for sex in sexes:
        data = []
        for municipality in municipalities:
            # Find count for this municipality and sex
            count_item = next((item for item in gender_by_muni if item.municipality == municipality and item.sex == sex), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        # Color coding
        color = "rgba(54, 162, 235, 0.6)" if sex == "Male" else "rgba(75, 192, 192, 0.6)"
        border_color = "rgba(54, 162, 235, 1)" if sex == "Male" else "rgba(75, 192, 192, 1)"
        
        datasets.append({
            "label": sex,
            "data": data,
            "backgroundColor": color,
            "borderColor": border_color,
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": municipalities,  # X-axis: Municipalities
            "datasets": datasets       # Grouped by sex
        }
    }
    
    return jsonify(response)

# H. Job Posting Distribution by Municipality (Replacing mock data)
@admin.route('/job_postings_by_municipality', methods=['GET'])
@auth.login_required
def job_postings_by_municipality():
    # Query to count job postings by municipality/city
    job_postings_by_location = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            func.count(EmployerJobPosting.employer_jobpost_id).label('count')
        )
        .filter(EmployerJobPosting.status == 'approved')  # Only count approved job postings
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow())  # Only active jobs
        .group_by(EmployerJobPosting.city_municipality)
        .order_by(desc('count'))
        .all()
    )
    
    # Format the data for visualization
    municipality_names = [item.municipality for item in job_postings_by_location]
    job_counts = [item.count for item in job_postings_by_location]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": municipality_names,  # X-axis: Municipalities
            "datasets": [
                {
                    "label": "Active Job Postings",
                    "data": job_counts,  # Y-axis: Number of job postings
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_job_postings": sum(job_counts)
    }
    
    return jsonify(response)

# I. Job Vacancy Status by Municipality (Replacing mock data)
@admin.route('/job_vacancies_by_municipality', methods=['GET'])
@auth.login_required
def job_vacancies_by_municipality():
    # Get municipalities with job postings
    municipalities = (
        db.session.query(EmployerJobPosting.city_municipality)
        .filter(EmployerJobPosting.status == 'approved')
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow())
        .group_by(EmployerJobPosting.city_municipality)
        .all()
    )
    
    municipality_names = [item.city_municipality for item in municipalities]
    
    # Query to get filled, open, and expiring vacancies for each municipality
    datasets = []
    
    # Open vacancies (plenty of time before expiration)
    open_vacancies = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            func.sum(EmployerJobPosting.no_of_vacancies).label('count')
        )
        .filter(EmployerJobPosting.status == 'approved')
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow() + timedelta(days=30))  # Not expiring soon
        .group_by(EmployerJobPosting.city_municipality)
        .all()
    )
    
    # Create a dictionary to match municipalities with counts
    open_data = {item.municipality: item.count for item in open_vacancies}
    
    # Ensure all municipalities have data points (use 0 if none exists)
    open_counts = [open_data.get(muni, 0) for muni in municipality_names]
    
    # Expiring soon (less than 30 days until expiration)
    expiring_vacancies = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            func.sum(EmployerJobPosting.no_of_vacancies).label('count')
        )
        .filter(EmployerJobPosting.status == 'approved')
        .filter(EmployerJobPosting.expiration_date < datetime.utcnow() + timedelta(days=30))  # Expiring soon
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow())  # Not yet expired
        .group_by(EmployerJobPosting.city_municipality)
        .all()
    )
    
    # Create a dictionary to match municipalities with counts
    expiring_data = {item.municipality: item.count for item in expiring_vacancies}
    
    # Ensure all municipalities have data points (use 0 if none exists)
    expiring_counts = [expiring_data.get(muni, 0) for muni in municipality_names]
    
    # Recently expired (for historical data)
    expired_vacancies = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            func.sum(EmployerJobPosting.no_of_vacancies).label('count')
        )
        .filter(EmployerJobPosting.status == 'approved')
        .filter(EmployerJobPosting.expiration_date < datetime.utcnow())  # Already expired
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow() - timedelta(days=30))  # Recently expired
        .group_by(EmployerJobPosting.city_municipality)
        .all()
    )
    
    # Create a dictionary to match municipalities with counts
    expired_data = {item.municipality: item.count for item in expired_vacancies}
    
    # Ensure all municipalities have data points (use 0 if none exists)
    expired_counts = [expired_data.get(muni, 0) for muni in municipality_names]
    
    # Prepare the response with multiple datasets
    response = {
        "chart_data": {
            "labels": municipality_names,  # X-axis: Municipalities
            "datasets": [
                {
                    "label": "Open Vacancies",
                    "data": open_counts,
                    "backgroundColor": "rgba(75, 192, 192, 0.6)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Expiring Soon",
                    "data": expiring_counts,
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Recently Expired",
                    "data": expired_counts,
                    "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
        }
    }
    
    return jsonify(response)

# K. Educational Attainment Distribution
@admin.route('/educational_attainment_distribution', methods=['GET'])
@auth.login_required
def educational_attainment_distribution():
    # Query to count job seekers by educational attainment
    edu_counts = (
        db.session.query(
            EducationalBackground.degree_or_qualification.label('education'),
            func.count(distinct(EducationalBackground.user_id)).label('count')
        )
        .join(PersonalInformation, EducationalBackground.user_id == PersonalInformation.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(EducationalBackground.degree_or_qualification)
        .all()
    )
    
    # Format the data for visualization
    labels = [item.education for item in edu_counts]
    data = [item.count for item in edu_counts]
    
    # Generate colors for pie chart
    import random
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)"
    ]
    
    background_colors = colors[:len(labels)]
    border_colors = [color.replace("0.6", "1") for color in background_colors]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": background_colors,
                    "borderColor": border_colors,
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# L. Job Preferences by Educational Attainment
@admin.route('/job_preferences_by_education', methods=['GET'])
@auth.login_required
def job_preferences_by_education():
    # Query to count job preferences by educational attainment and job title
    job_prefs_by_edu = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            EducationalBackground.degree_or_qualification.label('education'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .join(EducationalBackground, JobPreference.user_id == EducationalBackground.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(JobPreference.preferred_occupation, EducationalBackground.degree_or_qualification)
        .order_by(desc('count'))
        .limit(50)  # Limit to top combinations
        .all()
    )
    
    # Process data for visualization
    # Focus on top job titles for clarity
    top_job_titles = list(set([item.job_title for item in job_prefs_by_edu]))[:10]
    education_levels = list(set([item.education for item in job_prefs_by_edu]))
    
    # Create datasets for each education level
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)"
    ]
    
    for i, edu in enumerate(education_levels):
        data = []
        for job_title in top_job_titles:
            # Find count for this job_title and education level
            count_item = next((item for item in job_prefs_by_edu if item.job_title == job_title and item.education == edu), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        color_index = i % len(colors)
        
        datasets.append({
            "label": edu,
            "data": data,
            "backgroundColor": colors[color_index],
            "borderColor": colors[color_index].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": top_job_titles,  # X-axis: Job titles
            "datasets": datasets        # Grouped by education level
        }
    }
    
    return jsonify(response)

# M. Educational Attainment by Municipality
@admin.route('/education_by_municipality', methods=['GET'])
@auth.login_required
def education_by_municipality():
    # Query to count job seekers by municipality and educational attainment
    edu_by_muni = (
        db.session.query(
            PersonalInformation.permanent_municipality.label('municipality'),
            EducationalBackground.degree_or_qualification.label('education'),
            func.count(distinct(PersonalInformation.user_id)).label('count')
        )
        .join(EducationalBackground, PersonalInformation.user_id == EducationalBackground.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .filter(PersonalInformation.permanent_municipality != None)
        .group_by(PersonalInformation.permanent_municipality, EducationalBackground.degree_or_qualification)
        .order_by(PersonalInformation.permanent_municipality, EducationalBackground.degree_or_qualification)
        .all()
    )
    
    # Process data for grouped bar chart
    # Focus on top municipalities for clarity
    municipality_counts = {}
    for item in edu_by_muni:
        municipality_counts[item.municipality] = municipality_counts.get(item.municipality, 0) + item.count
    
    top_municipalities = sorted(municipality_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_municipality_names = [item[0] for item in top_municipalities]
    
    education_levels = list(set([item.education for item in edu_by_muni]))
    
    # Create datasets for each education level
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)"
    ]
    
    for i, edu in enumerate(education_levels):
        data = []
        for municipality in top_municipality_names:
            # Find count for this municipality and education level
            count_item = next((item for item in edu_by_muni if item.municipality == municipality and item.education == edu), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        color_index = i % len(colors)
        
        datasets.append({
            "label": edu,
            "data": data,
            "backgroundColor": colors[color_index],
            "borderColor": colors[color_index].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": top_municipality_names,  # X-axis: Municipalities
            "datasets": datasets              # Grouped by education level
        }
    }
    
    return jsonify(response)

# N. Age Distribution of Job Seekers
@admin.route('/age_distribution', methods=['GET'])
@auth.login_required
def age_distribution():
    from datetime import datetime
    current_year = datetime.now().year
    
    # Create age brackets using case statement
    age_brackets = (
        db.session.query(
            case(
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 18, "Under 18"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 25, "18-24"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 35, "25-34"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 45, "35-44"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 55, "45-54"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 65, "55-64"),
                else_="65+")
            .label('age_bracket'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by('age_bracket')
        .order_by(
            case(
                (func.lower('age_bracket') == "under 18", 1),
                (func.lower('age_bracket') == "18-24", 2),
                (func.lower('age_bracket') == "25-34", 3),
                (func.lower('age_bracket') == "35-44", 4),
                (func.lower('age_bracket') == "45-54", 5),
                (func.lower('age_bracket') == "55-64", 6),
                else_=7
            )
        )
        .all()
    )
    
    # Format the data for visualization
    labels = [item.age_bracket for item in age_brackets]
    data = [item.count for item in age_brackets]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,  # X-axis: Age brackets
            "datasets": [
                {
                    "label": "Number of Job Seekers",
                    "data": data,  # Y-axis: Count of job seekers
                    "backgroundColor": "rgba(153, 102, 255, 0.6)",
                    "borderColor": "rgba(153, 102, 255, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# O. Job Preferences by Age Group
@admin.route('/job_preferences_by_age', methods=['GET'])
@auth.login_required
def job_preferences_by_age():
    from datetime import datetime
    current_year = datetime.now().year
    
    # Create age bracket subquery
    subq = db.session.query(
        PersonalInformation.user_id,
        case(
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 18, "Under 18"),
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 25, "18-24"),
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 35, "25-34"),
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 45, "35-44"),
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 55, "45-54"),
            (current_year - func.extract('year', PersonalInformation.date_of_birth) < 65, "55-64"),
            else_="65+"
        ).label('age_bracket')
    ).filter(PersonalInformation.is_looking_for_work == True).subquery()
    
    # Query to count job preferences by age group and job title
    job_prefs_by_age = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            subq.c.age_bracket.label('age_bracket'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(subq, JobPreference.user_id == subq.c.user_id)
        .group_by(JobPreference.preferred_occupation, subq.c.age_bracket)
        .order_by(desc('count'))
        .limit(50)  # Limit to top combinations
        .all()
    )
    
    # Process data for visualization
    # Focus on top job titles for clarity
    top_job_titles = list(set([item.job_title for item in job_prefs_by_age]))[:10]
    age_brackets = [
        "Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"
    ]
    
    # Create datasets for each age bracket
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)",
        "rgba(201, 203, 207, 0.6)"
    ]
    
    for i, age in enumerate(age_brackets):
        data = []
        for job_title in top_job_titles:
            # Find count for this job_title and age bracket
            count_item = next((item for item in job_prefs_by_age if item.job_title == job_title and item.age_bracket == age), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        color_index = i % len(colors)
        
        datasets.append({
            "label": age,
            "data": data,
            "backgroundColor": colors[color_index],
            "borderColor": colors[color_index].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": top_job_titles,  # X-axis: Job titles
            "datasets": datasets        # Grouped by age bracket
        }
    }
    
    return jsonify(response)

# P. Age Distribution by Municipality
@admin.route('/age_by_municipality', methods=['GET'])
@auth.login_required
def age_by_municipality():
    from datetime import datetime
    current_year = datetime.now().year
    
    # Create age bracket and municipality count query
    age_by_muni = (
        db.session.query(
            PersonalInformation.permanent_municipality.label('municipality'),
            case(
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 18, "Under 18"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 25, "18-24"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 35, "25-34"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 45, "35-44"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 55, "45-54"),
                (current_year - func.extract('year', PersonalInformation.date_of_birth) < 65, "55-64"),
                else_="65+"
            ).label('age_bracket'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .filter(PersonalInformation.permanent_municipality != None)
        .group_by(PersonalInformation.permanent_municipality, 'age_bracket')
        .all()
    )
    
    # Process data for heatmap
    municipalities = list(set([item.municipality for item in age_by_muni]))
    age_brackets = ["Under 18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    
    # Create 2D array for heatmap data
    heatmap_data = []
    for municipality in municipalities:
        row_data = []
        for age in age_brackets:
            # Find count for this municipality and age bracket
            count_item = next((item for item in age_by_muni if item.municipality == municipality and item.age_bracket == age), None)
            count = count_item.count if count_item else 0
            row_data.append(count)
        heatmap_data.append(row_data)
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": {
                "x": age_brackets,      # X-axis: Age brackets
                "y": municipalities     # Y-axis: Municipalities
            },
            "data": heatmap_data,       # 2D array of counts
            "max_value": max(max(row) for row in heatmap_data) if heatmap_data and heatmap_data[0] else 0
        }
    }
    
    return jsonify(response)

# Q. Course Distribution
@admin.route('/course_distribution', methods=['GET'])
@auth.login_required
def course_distribution():
    # Query to count job seekers by course (field of study)
    course_counts = (
        db.session.query(
            EducationalBackground.field_of_study.label('course'),
            func.count(distinct(EducationalBackground.user_id)).label('count')
        )
        .join(PersonalInformation, EducationalBackground.user_id == PersonalInformation.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(EducationalBackground.field_of_study)
        .order_by(desc('count'))
        .all()
    )
    
    # Format the data for visualization
    labels = [item.course for item in course_counts]
    data = [item.count for item in course_counts]
    
    # Generate colors for pie chart
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)",
        "rgba(201, 203, 207, 0.6)",
        "rgba(255, 99, 71, 0.6)",
        "rgba(50, 205, 50, 0.6)",
        "rgba(255, 165, 0, 0.6)"
    ]
    
    # Ensure we have enough colors
    while len(colors) < len(labels):
        colors.extend(colors)
    
    background_colors = colors[:len(labels)]
    border_colors = [color.replace("0.6", "1") for color in background_colors]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": background_colors,
                    "borderColor": border_colors,
                    "borderWidth": 1
                }
            ]
        },
        "total_job_seekers": sum(data)
    }
    
    return jsonify(response)

# R. Job Preferences by Course
@admin.route('/job_preferences_by_course', methods=['GET'])
@auth.login_required
def job_preferences_by_course():
    # Query to count job preferences by course and job title
    job_prefs_by_course = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            EducationalBackground.field_of_study.label('course'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .join(EducationalBackground, JobPreference.user_id == EducationalBackground.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(JobPreference.preferred_occupation, EducationalBackground.field_of_study)
        .order_by(desc('count'))
        .limit(50)  # Limit to top combinations
        .all()
    )
    
    # Process data for visualization
    # Focus on top job titles for clarity
    top_job_titles = list(set([item.job_title for item in job_prefs_by_course]))[:10]
    
    # Get top courses by count
    course_counts = {}
    for item in job_prefs_by_course:
        course_counts[item.course] = course_counts.get(item.course, 0) + item.count
    
    top_courses = sorted(course_counts.items(), key=lambda x: x[1], reverse=True)[:7]  # Top 7 courses
    top_course_names = [item[0] for item in top_courses]
    
    # Create datasets for each course
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(255, 206, 86, 0.6)",
        "rgba(201, 203, 207, 0.6)"
    ]
    
    for i, course in enumerate(top_course_names):
        data = []
        for job_title in top_job_titles:
            # Find count for this job_title and course
            count_item = next((item for item in job_prefs_by_course if item.job_title == job_title and item.course == course), None)
            count = count_item.count if count_item else 0
            data.append(count)
        
        color_index = i % len(colors)
        
        datasets.append({
            "label": course,
            "data": data,
            "backgroundColor": colors[color_index],
            "borderColor": colors[color_index].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": top_job_titles,  # X-axis: Job titles
            "datasets": datasets        # Grouped by course
        }
    }
    
    return jsonify(response)

# S. Top 10 Skills in Demand (Using actual job postings)
@admin.route('/top_skills_in_demand', methods=['GET'])
@auth.login_required
def top_skills_in_demand():
    # Query actual skills demand from job postings' other_skills field
    skills_demand = (
        db.session.query(
            EmployerJobPosting.other_skills,
            func.count(EmployerJobPosting.employer_jobpost_id).label('demand_score')
        )
        .filter(EmployerJobPosting.status == 'approved')
        .filter(EmployerJobPosting.expiration_date >= datetime.utcnow())
        .filter(EmployerJobPosting.other_skills != None)
        .filter(EmployerJobPosting.other_skills != '')
        .group_by(EmployerJobPosting.other_skills)
        .order_by(desc('demand_score'))
        .all()
    )
    
    # Process skills (assuming other_skills might contain multiple skills separated by commas)
    skill_counts = {}
    for item in skills_demand:
        if item.other_skills:
            skills_list = [skill.strip() for skill in item.other_skills.split(',')]
            for skill in skills_list:
                if skill:
                    skill_counts[skill] = skill_counts.get(skill, 0) + item.demand_score
    
    # Get top 10 skills
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Format the data for visualization
    labels = [item[0] for item in top_skills]
    data = [item[1] for item in top_skills]
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": labels,  # Y-axis: Skills
            "datasets": [
                {
                    "label": "Demand Score",
                    "data": data,  # X-axis: Demand score
                    "backgroundColor": "rgba(255, 159, 64, 0.6)",
                    "borderColor": "rgba(255, 159, 64, 1)",
                    "borderWidth": 1
                }
            ]
        }
    }
    
    return jsonify(response)

###########################################################################################################################################
#                                                              JOB TREND DASHBOARD
###########################################################################################################################################
# A. Gender Distribution
@admin.route('/gender_distribution', methods=['GET'])
@auth.login_required
def gender_distribution():
    gender_counts = (
        db.session.query(
            PersonalInformation.sex.label('gender'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(PersonalInformation.sex)
        .all()
    )
    
    # Format the data for visualization
    response = {
        "chart_data": {
            "labels": [item.gender for item in gender_counts],
            "datasets": [{
                "label": "Gender Distribution",
                "data": [item.count for item in gender_counts],
                "backgroundColor": [
                    "rgba(54, 162, 235, 0.6)",  # Blue for Male
                    "rgba(255, 99, 132, 0.6)",   # Pink for Female
                ],
                "borderColor": [
                    "rgba(54, 162, 235, 1)",
                    "rgba(255, 99, 132, 1)",
                ],
                "borderWidth": 1
            }]
        },
        "total_jobseekers": sum(item.count for item in gender_counts)
    }
    
    return jsonify(response)

# B. Gender Count
@admin.route('/gender_count', methods=['GET'])
@auth.login_required
def gender_count():
    gender_counts = (
        db.session.query(
            PersonalInformation.sex.label('gender'),
            func.count(PersonalInformation.user_id).label('count')
        )
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(PersonalInformation.sex)
        .all()
    )
    
    # Format the data for visualization
    response = {
        "chart_data": {
            "labels": [item.gender for item in gender_counts],  # X-axis: Gender labels
            "datasets": [{
                "label": "Number of Job Seekers",
                "data": [item.count for item in gender_counts],  # Y-axis: Count of job seekers
                "backgroundColor": [
                    "rgba(54, 162, 235, 0.6)",  # Blue for Male
                    "rgba(255, 99, 132, 0.6)",   # Pink for Female
                ],
                "borderColor": [
                    "rgba(54, 162, 235, 1)",
                    "rgba(255, 99, 132, 1)",
                ],
                "borderWidth": 1
            }]
        }
    }
    
    return jsonify(response)

# C. Educational Attainment
@admin.route('/educational_attainment', methods=['GET'])
@auth.login_required
def educational_attainment():
    education_counts = (
        db.session.query(
            EducationalBackground.degree_or_qualification.label('education_level'),
            func.count(EducationalBackground.user_id).label('count')
        )
        .join(PersonalInformation, EducationalBackground.user_id == PersonalInformation.user_id)
        .filter(PersonalInformation.is_looking_for_work == True)
        .group_by(EducationalBackground.degree_or_qualification)
        .order_by(desc('count'))
        .all()
    )
    
    # Format the data for visualization
    response = {
        "chart_data": {
            "labels": [item.education_level for item in education_counts],  # X-axis: Education levels
            "datasets": [{
                "label": "Number of Job Seekers",
                "data": [item.count for item in education_counts],  # Y-axis: Count of job seekers
                "backgroundColor": "rgba(75, 192, 192, 0.6)",
                "borderColor": "rgba(75, 192, 192, 1)",
                "borderWidth": 1
            }]
        }
    }
    
    return jsonify(response)

# D. Job Applications by Educational Attainment
@admin.route('/job_applications_by_education', methods=['GET'])
@auth.login_required
def job_applications_by_education():
    applications_by_education = (
        db.session.query(
            EducationalBackground.degree_or_qualification.label('education_level'),
            EmployerJobPosting.job_title.label('job_title'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EducationalBackground.user_id == StudentJobseekerApplyJobs.user_id)
        .join(EmployerJobPosting, StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id)
        .group_by(EducationalBackground.degree_or_qualification, EmployerJobPosting.job_title)
        .order_by(EducationalBackground.degree_or_qualification, desc('application_count'))
        .all()
    )
    
    # Process data for visualization
    education_levels = list(set([item.education_level for item in applications_by_education]))
    job_titles = list(set([item.job_title for item in applications_by_education]))
    
    # Create datasets for each job title
    datasets = []
    for job_title in job_titles:
        job_data = []
        for edu in education_levels:
            # Find the count for this job and education level
            count = next((item.application_count for item in applications_by_education 
                          if item.job_title == job_title and item.education_level == edu), 0)
            job_data.append(count)
        
        # Generate a random color for this job title
        datasets.append({
            "label": job_title,
            "data": job_data,
            # You would need a color generation function here to assign different colors
            "backgroundColor": f"rgba({hash(job_title) % 255}, {(hash(job_title) // 255) % 255}, {(hash(job_title) // (255*255)) % 255}, 0.6)"
        })
    
    response = {
        "chart_data": {
            "labels": education_levels,  # X-axis: Education levels
            "datasets": datasets
        }
    }
    
    return jsonify(response)

# E. Top Fields of Study
@admin.route('/top_fields_of_study', methods=['GET'])
@auth.login_required
def top_fields_of_study():
    # Get the top jobs and their application counts by field of study
    top_jobs_by_field = (
        db.session.query(
            EmployerJobPosting.job_title.label('job_title'),
            EducationalBackground.field_of_study.label('field_of_study'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EmployerJobPosting.employer_jobpost_id == StudentJobseekerApplyJobs.employer_jobpost_id)
        .join(EducationalBackground, StudentJobseekerApplyJobs.user_id == EducationalBackground.user_id)
        .group_by(EmployerJobPosting.job_title, EducationalBackground.field_of_study)
        .order_by(desc('application_count'))
        .limit(10)  # Top 10 combinations
        .all()
    )
    
    # Format the data for visualization
    labels = [item.job_title for item in top_jobs_by_field]
    data = [item.application_count for item in top_jobs_by_field]
    fields = [item.field_of_study for item in top_jobs_by_field]
    
    response = {
        "chart_data": {
            "labels": labels,  # Y-axis: Jobs
            "datasets": [{
                "label": "Number of Applications",
                "data": data,  # X-axis: Number of applications
                "backgroundColor": "rgba(153, 102, 255, 0.6)",
                "borderColor": "rgba(153, 102, 255, 1)",
                "borderWidth": 1
            }]
        },
        "fields_of_study": fields  # Additional information about field of study for each job
    }
    
    return jsonify(response)

# F. Top Jobs Field of Study
@admin.route('/top_jobs_by_field', methods=['GET'])
@auth.login_required
def top_jobs_by_field():
    top_fields = (
        db.session.query(
            EducationalBackground.field_of_study.label('field_of_study'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EducationalBackground.user_id == StudentJobseekerApplyJobs.user_id)
        .group_by(EducationalBackground.field_of_study)
        .order_by(desc('application_count'))
        .limit(10)  # Top 10 fields
        .all()
    )
    
    # Format the data for visualization
    response = {
        "chart_data": {
            "labels": [item.field_of_study for item in top_fields],  # X-axis: Field of study
            "datasets": [{
                "label": "Number of Job Applications",
                "data": [item.application_count for item in top_fields],  # Y-axis: Number of applications
                "backgroundColor": "rgba(255, 159, 64, 0.6)",
                "borderColor": "rgba(255, 159, 64, 1)",
                "borderWidth": 1
            }]
        }
    }
    
    return jsonify(response)

# G. Job Applications by Municipality
@admin.route('/job_applications_by_municipality', methods=['GET'])
@auth.login_required
def job_applications_by_municipality():
    applications_by_municipality = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            EmployerJobPosting.job_title.label('job_category'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EmployerJobPosting.employer_jobpost_id == StudentJobseekerApplyJobs.employer_jobpost_id)
        .group_by(EmployerJobPosting.city_municipality, EmployerJobPosting.job_title)
        .order_by(EmployerJobPosting.city_municipality, desc('application_count'))
        .all()
    )
    
    # Process data for stacked bar chart
    municipalities = list(set([item.municipality for item in applications_by_municipality]))
    job_categories = list(set([item.job_category for item in applications_by_municipality]))
    
    # Create datasets for each job category
    datasets = []
    for job in job_categories:
        job_data = []
        for muni in municipalities:
            # Find the count for this job and municipality
            count = next((item.application_count for item in applications_by_municipality 
                          if item.job_category == job and item.municipality == muni), 0)
            job_data.append(count)
        
        # Generate a color for this job category
        datasets.append({
            "label": job,
            "data": job_data,
            "backgroundColor": f"rgba({hash(job) % 255}, {(hash(job) // 255) % 255}, {(hash(job) // (255*255)) % 255}, 0.6)"
        })
    
    response = {
        "chart_data": {
            "labels": municipalities,  # X-axis: Municipalities
            "datasets": datasets  # Stacked segments for different job categories
        }
    }
    
    return jsonify(response)

# H. Job Trend By Municipality
@admin.route('/job_trend_by_municipality', methods=['GET'])
@auth.login_required
def job_trend_by_municipality():
    # Get application counts by municipality over time (monthly)
    # First, get data for the last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 12 months
    
    trend_by_municipality = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('municipality'),
            extract('year', StudentJobseekerApplyJobs.created_at).label('year'),
            extract('month', StudentJobseekerApplyJobs.created_at).label('month'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EmployerJobPosting.employer_jobpost_id == StudentJobseekerApplyJobs.employer_jobpost_id)
        .filter(StudentJobseekerApplyJobs.created_at.between(start_date, end_date))
        .group_by('municipality', 'year', 'month')
        .order_by('municipality', 'year', 'month')
        .all()
    )
    
    # Process data for line chart
    municipalities = list(set([item.municipality for item in trend_by_municipality]))
    
    # Generate date labels for the last 12 months
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        date_labels.append(current_date.strftime('%Y-%m'))
        # Increment by one month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # Create datasets for each municipality
    datasets = []
    for muni in municipalities:
        muni_data = []
        for date_label in date_labels:
            year, month = map(int, date_label.split('-'))
            # Find the count for this municipality and date
            count = next((item.application_count for item in trend_by_municipality 
                          if item.municipality == muni and item.year == year and item.month == month), 0)
            muni_data.append(count)
        
        # Generate a color for this municipality
        datasets.append({
            "label": muni,
            "data": muni_data,
            "borderColor": f"rgba({hash(muni) % 255}, {(hash(muni) // 255) % 255}, {(hash(muni) // (255*255)) % 255}, 1)",
            "backgroundColor": "rgba(0, 0, 0, 0)",  # Transparent background for line charts
            "fill": False
        })
    
    response = {
        "chart_data": {
            "labels": date_labels,  # X-axis: Date
            "datasets": datasets  # Different colored lines for municipalities
        }
    }
    
    return jsonify(response)

# I. Job Demand Interest
@admin.route('/job_demand_interest', methods=['GET'])
@auth.login_required
def job_demand_interest():
    job_interest = (
        db.session.query(
            EmployerJobPosting.job_title.label('job_title'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('interest_count')
        )
        .join(StudentJobseekerApplyJobs, EmployerJobPosting.employer_jobpost_id == StudentJobseekerApplyJobs.employer_jobpost_id)
        .group_by(EmployerJobPosting.job_title)
        .order_by(desc('interest_count'))
        .limit(10)  # Top 10 jobs by interest
        .all()
    )
    
    # Format the data for visualization
    response = {
        "chart_data": {
            "labels": [item.job_title for item in job_interest],  # Y-axis: Job titles
            "datasets": [{
                "label": "Number of Applications",
                "data": [item.interest_count for item in job_interest],  # X-axis: Interest count
                "backgroundColor": "rgba(54, 162, 235, 0.6)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 1
            }]
        }
    }
    
    return jsonify(response)

# J. Application vs Preference
@admin.route('/application_vs_preference', methods=['GET'])
@auth.login_required
def application_vs_preference():
    # Get the job application counts
    applications = (
        db.session.query(
            EmployerJobPosting.job_title.label('job_title'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('application_count')
        )
        .join(StudentJobseekerApplyJobs, EmployerJobPosting.employer_jobpost_id == StudentJobseekerApplyJobs.employer_jobpost_id)
        .group_by(EmployerJobPosting.job_title)
        .order_by(desc('application_count'))
        .all()
    )
    
    # Get the job preference counts
    preferences = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            func.count(JobPreference.user_id).label('preference_count')
        )
        .group_by(JobPreference.preferred_occupation)
        .order_by(desc('preference_count'))
        .all()
    )
    
    # Combine both datasets for comparison
    all_jobs = list(set([item.job_title for item in applications] + [item.job_title for item in preferences]))
    
    application_data = []
    preference_data = []
    
    for job in all_jobs:
        # Find application count for this job
        app_count = next((item.application_count for item in applications if item.job_title == job), 0)
        application_data.append(app_count)
        
        # Find preference count for this job
        pref_count = next((item.preference_count for item in preferences if item.job_title == job), 0)
        preference_data.append(pref_count)
    
    response = {
        "chart_data": {
            "labels": all_jobs,  # X-axis: Job titles
            "datasets": [
                {
                    "label": "Applications",
                    "data": application_data,
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Preferences",
                    "data": preference_data,
                    "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
        }
    }
    
    return jsonify(response)

##########################################################################################################################################
#                                                       JOB PREFERENCES DASHBOARD
##########################################################################################################################################

# A, B, C. Gender distribution across job preferences
@admin.route('/job_preferences_by_gender', methods=['GET'])
@auth.login_required
def job_preferences_by_gender():
    # Query to count job preferences by gender
    gender_job_counts = (
        db.session.query(
            JobPreference.preferred_occupation.label('job_title'),
            PersonalInformation.sex.label('gender'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .group_by(JobPreference.preferred_occupation, PersonalInformation.sex)
        .order_by(JobPreference.preferred_occupation, PersonalInformation.sex)
        .all()
    )
    
    # Process query results to organize by job title
    job_titles = list(set([item.job_title for item in gender_job_counts]))
    
    male_counts = {job: 0 for job in job_titles}
    female_counts = {job: 0 for job in job_titles}
    
    for item in gender_job_counts:
        if item.gender.lower() == 'male':
            male_counts[item.job_title] = item.count
        elif item.gender.lower() == 'female':
            female_counts[item.job_title] = item.count
    
    # Format data for visualization
    response = {
        "chart_data": {
            "labels": job_titles,  # X-axis: Job titles
            "datasets": [
                {
                    "label": "Male",
                    "data": [male_counts[job] for job in job_titles],
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Female",
                    "data": [female_counts[job] for job in job_titles],
                    "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_preferences": sum([item.count for item in gender_job_counts])
    }
    
    return jsonify(response)

# D, E. Occupation by Field of Study
@admin.route('/occupation_by_field_of_study', methods=['GET'])
@auth.login_required
def occupation_by_field_of_study():
    # Query to count occupations by field of study
    field_occupation_counts = (
        db.session.query(
            JobPreference.preferred_occupation.label('occupation'),
            EducationalBackground.field_of_study.label('field'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(
            EducationalBackground, 
            JobPreference.user_id == EducationalBackground.user_id
        )
        .group_by(JobPreference.preferred_occupation, EducationalBackground.field_of_study)
        .order_by(desc('count'))
        .all()
    )
    
    # Group data by occupation
    occupations = list(set([item.occupation for item in field_occupation_counts]))
    fields = list(set([item.field for item in field_occupation_counts]))
    
    # Create a dictionary to store counts by field for each occupation
    occupation_field_data = {occupation: {field: 0 for field in fields} for occupation in occupations}
    
    for item in field_occupation_counts:
        occupation_field_data[item.occupation][item.field] = item.count
    
    # Format data for visualization
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)",
        "rgba(199, 199, 199, 0.6)", "rgba(83, 102, 255, 0.6)"
    ]
    
    for i, field in enumerate(fields):
        datasets.append({
            "label": field,
            "data": [occupation_field_data[occupation][field] for occupation in occupations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    response = {
        "chart_data": {
            "labels": occupations,  # X-axis: Occupations
            "datasets": datasets    # Y-axis: Counts by field of study
        },
        "total_records": sum([item.count for item in field_occupation_counts])
    }
    
    return jsonify(response)

# F, G. Location by Sex
@admin.route('/location_by_gender', methods=['GET'])
@auth.login_required
def location_by_gender():
    # Query to count location preferences by gender
    location_gender_counts = (
        db.session.query(
            JobPreference.province.label('location'),  # Can be changed to municipality or country as needed
            PersonalInformation.sex.label('gender'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .group_by(JobPreference.province, PersonalInformation.sex)
        .order_by(JobPreference.province, PersonalInformation.sex)
        .all()
    )
    
    # Process query results to organize by location
    locations = list(set([item.location for item in location_gender_counts]))
    
    male_counts = {location: 0 for location in locations}
    female_counts = {location: 0 for location in locations}
    
    for item in location_gender_counts:
        if item.gender.lower() == 'male':
            male_counts[item.location] = item.count
        elif item.gender.lower() == 'female':
            female_counts[item.location] = item.count
    
    # Format data for visualization
    response = {
        "chart_data": {
            "labels": locations,  # X-axis: Locations
            "datasets": [
                {
                    "label": "Male",
                    "data": [male_counts[location] for location in locations],
                    "backgroundColor": "rgba(54, 162, 235, 0.6)",
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "borderWidth": 1
                },
                {
                    "label": "Female",
                    "data": [female_counts[location] for location in locations],
                    "backgroundColor": "rgba(255, 99, 132, 0.6)",
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderWidth": 1
                }
            ]
        },
        "total_preferences": sum([item.count for item in location_gender_counts])
    }
    
    return jsonify(response)

# H, I. Location by Sex (Pie Charts)
@admin.route('/location_by_gender_pie', methods=['GET'])
@auth.login_required
def location_by_gender_pie():
    # Query to count location preferences by gender
    location_gender_counts = (
        db.session.query(
            JobPreference.province.label('location'),  # Can be changed to municipality or country
            PersonalInformation.sex.label('gender'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .group_by(JobPreference.province, PersonalInformation.sex)
        .order_by(JobPreference.province, PersonalInformation.sex)
        .all()
    )
    
    # Process query results for male and female separately
    male_data = [item for item in location_gender_counts if item.gender.lower() == 'male']
    female_data = [item for item in location_gender_counts if item.gender.lower() == 'female']
    
    # Format data for male pie chart
    male_chart = {
        "labels": [item.location for item in male_data],
        "datasets": [{
            "data": [item.count for item in male_data],
            "backgroundColor": [
                "rgba(54, 162, 235, 0.6)", "rgba(255, 206, 86, 0.6)",
                "rgba(75, 192, 192, 0.6)", "rgba(153, 102, 255, 0.6)",
                "rgba(255, 159, 64, 0.6)", "rgba(199, 199, 199, 0.6)"
            ],
            "borderColor": [
                "rgba(54, 162, 235, 1)", "rgba(255, 206, 86, 1)",
                "rgba(75, 192, 192, 1)", "rgba(153, 102, 255, 1)",
                "rgba(255, 159, 64, 1)", "rgba(199, 199, 199, 1)"
            ],
            "borderWidth": 1
        }]
    }
    
    # Format data for female pie chart
    female_chart = {
        "labels": [item.location for item in female_data],
        "datasets": [{
            "data": [item.count for item in female_data],
            "backgroundColor": [
                "rgba(255, 99, 132, 0.6)", "rgba(255, 206, 86, 0.6)",
                "rgba(75, 192, 192, 0.6)", "rgba(153, 102, 255, 0.6)",
                "rgba(255, 159, 64, 0.6)", "rgba(199, 199, 199, 0.6)"
            ],
            "borderColor": [
                "rgba(255, 99, 132, 1)", "rgba(255, 206, 86, 1)",
                "rgba(75, 192, 192, 1)", "rgba(153, 102, 255, 1)",
                "rgba(255, 159, 64, 1)", "rgba(199, 199, 199, 1)"
            ],
            "borderWidth": 1
        }]
    }
    
    response = {
        "male_chart_data": male_chart,
        "female_chart_data": female_chart,
        "total_male_preferences": sum([item.count for item in male_data]),
        "total_female_preferences": sum([item.count for item in female_data])
    }
    
    return jsonify(response)

# J, K, L, M. Location by Field
@admin.route('/location_by_field', methods=['GET'])
@auth.login_required
def location_by_field():
    # Query to count location preferences by field of study
    location_field_counts = (
        db.session.query(
            JobPreference.province.label('location'),  # Can be changed to municipality or country
            EducationalBackground.field_of_study.label('field'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(
            EducationalBackground, 
            JobPreference.user_id == EducationalBackground.user_id
        )
        .group_by(JobPreference.province, EducationalBackground.field_of_study)
        .order_by(JobPreference.province, EducationalBackground.field_of_study)
        .all()
    )
    
    # Process query results to organize by location
    locations = list(set([item.location for item in location_field_counts]))
    fields = list(set([item.field for item in location_field_counts]))
    
    # Create a dictionary to store counts by field for each location
    location_field_data = {location: {field: 0 for field in fields} for location in locations}
    
    for item in location_field_counts:
        location_field_data[item.location][item.field] = item.count
    
    # Format data for stacked bar visualization
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)",
        "rgba(199, 199, 199, 0.6)", "rgba(83, 102, 255, 0.6)"
    ]
    
    for i, field in enumerate(fields):
        datasets.append({
            "label": field,
            "data": [location_field_data[location][field] for location in locations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    response = {
        "chart_data": {
            "labels": locations,  # X-axis: Locations
            "datasets": datasets  # Y-axis: Counts by field of study
        },
        "stacked_chart_data": {
            "labels": locations,
            "datasets": datasets
        },
        "total_records": sum([item.count for item in location_field_counts])
    }
    
    return jsonify(response)

# N, O, P. Preferred Occupation By Age Bracket
@admin.route('/occupation_by_age', methods=['GET'])
@auth.login_required
def occupation_by_age():
    current_year = datetime.now().year
    
    # Query to count occupation preferences by age bracket
    occupation_age_counts = (
        db.session.query(
            JobPreference.preferred_occupation.label('occupation'),
            case(
                [
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 20, 'Under 20'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 30, '20-29'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 40, '30-39'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 50, '40-49'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 60, '50-59')
                ],
                else_='60+'
            ).label('age_bracket'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .group_by('occupation', 'age_bracket')
        .order_by('occupation', 'age_bracket')
        .all()
    )
    
    # Define age brackets in order
    age_brackets = ['Under 20', '20-29', '30-39', '40-49', '50-59', '60+']
    
    # Process query results to organize by occupation
    occupations = list(set([item.occupation for item in occupation_age_counts]))
    
    # Create a dictionary to store counts by age bracket for each occupation
    occupation_age_data = {occupation: {age: 0 for age in age_brackets} for occupation in occupations}
    
    for item in occupation_age_counts:
        occupation_age_data[item.occupation][item.age_bracket] = item.count
    
    # Format data for bar chart visualization
    bar_datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)"
    ]
    
    for i, age in enumerate(age_brackets):
        bar_datasets.append({
            "label": age,
            "data": [occupation_age_data[occupation][age] for occupation in occupations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Format data for line chart visualization
    line_datasets = []
    
    # Reorganize data for line chart (age bracket on x-axis)
    occupation_counts_by_age = {occupation: [] for occupation in occupations}
    
    for occupation in occupations:
        for age in age_brackets:
            occupation_counts_by_age[occupation].append(occupation_age_data[occupation][age])
    
    for i, occupation in enumerate(occupations):
        line_datasets.append({
            "label": occupation,
            "data": occupation_counts_by_age[occupation],
            "backgroundColor": "transparent",
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "pointBackgroundColor": colors[i % len(colors)],
            "tension": 0.1,
            "fill": False
        })
    
    response = {
        "bar_chart_data": {
            "labels": occupations,  # X-axis: Occupations
            "datasets": bar_datasets  # Y-axis: Counts by age bracket
        },
        "line_chart_data": {
            "labels": age_brackets,  # X-axis: Age brackets
            "datasets": line_datasets  # Y-axis: Counts by occupation
        },
        "total_records": sum([item.count for item in occupation_age_counts])
    }
    
    return jsonify(response)

# Q, R, S. Location By Age
@admin.route('/location_by_age', methods=['GET'])
@auth.login_required
def location_by_age():
    current_year = datetime.now().year
    
    # Query to count location preferences by age bracket
    location_age_counts = (
        db.session.query(
            JobPreference.province.label('location'),  # Can be changed to municipality or country
            case(
                [
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 20, 'Under 20'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 30, '20-29'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 40, '30-39'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 50, '40-49'),
                    (current_year - extract('year', PersonalInformation.date_of_birth) < 60, '50-59')
                ],
                else_='60+'
            ).label('age_bracket'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(PersonalInformation, JobPreference.user_id == PersonalInformation.user_id)
        .group_by('location', 'age_bracket')
        .order_by('location', 'age_bracket')
        .all()
    )
    
    # Define age brackets in order
    age_brackets = ['Under 20', '20-29', '30-39', '40-49', '50-59', '60+']
    
    # Process query results to organize by location
    locations = list(set([item.location for item in location_age_counts]))
    
    # Create a dictionary to store counts by age bracket for each location
    location_age_data = {location: {age: 0 for age in age_brackets} for location in locations}
    
    for item in location_age_counts:
        location_age_data[item.location][item.age_bracket] = item.count
    
    # Format data for bar chart visualization
    bar_datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)"
    ]
    
    for i, age in enumerate(age_brackets):
        bar_datasets.append({
            "label": age,
            "data": [location_age_data[location][age] for location in locations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Format data for line chart visualization
    line_datasets = []
    
    # Reorganize data for line chart (age bracket on x-axis)
    location_counts_by_age = {location: [] for location in locations}
    
    for location in locations:
        for age in age_brackets:
            location_counts_by_age[location].append(location_age_data[location][age])
    
    for i, location in enumerate(locations):
        line_datasets.append({
            "label": location,
            "data": location_counts_by_age[location],
            "backgroundColor": "transparent",
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "pointBackgroundColor": colors[i % len(colors)],
            "tension": 0.1,
            "fill": False
        })
    
    response = {
        "bar_chart_data": {
            "labels": locations,  # X-axis: Locations
            "datasets": bar_datasets  # Y-axis: Counts by age bracket
        },
        "line_chart_data": {
            "labels": age_brackets,  # X-axis: Age brackets
            "datasets": line_datasets  # Y-axis: Counts by location
        },
        "total_records": sum([item.count for item in location_age_counts])
    }
    
    return jsonify(response)

# T, U. Occupation by Education
@admin.route('/occupation_by_education', methods=['GET'])
@auth.login_required
def occupation_by_education():
    # Query to count occupation preferences by education level
    occupation_education_counts = (
        db.session.query(
            JobPreference.preferred_occupation.label('occupation'),
            EducationalBackground.degree_or_qualification.label('education_level'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(
            EducationalBackground, 
            JobPreference.user_id == EducationalBackground.user_id
        )
        .group_by(JobPreference.preferred_occupation, EducationalBackground.degree_or_qualification)
        .order_by(JobPreference.preferred_occupation, EducationalBackground.degree_or_qualification)
        .all()
    )
    
    # Process query results to organize by occupation
    occupations = list(set([item.occupation for item in occupation_education_counts]))
    education_levels = list(set([item.education_level for item in occupation_education_counts]))
    
    # Create a dictionary to store counts by education level for each occupation
    occupation_education_data = {
        occupation: {level: 0 for level in education_levels} for occupation in occupations
    }
    
    for item in occupation_education_counts:
        occupation_education_data[item.occupation][item.education_level] = item.count
    
    # Format data for visualization
    datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)",
        "rgba(199, 199, 199, 0.6)", "rgba(83, 102, 255, 0.6)"
    ]
    
    for i, level in enumerate(education_levels):
        datasets.append({
            "label": level,
            "data": [occupation_education_data[occupation][level] for occupation in occupations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    response = {
        "chart_data": {
            "labels": occupations,  # X-axis: Occupations
            "datasets": datasets    # Y-axis: Counts by education level
        },
        "total_records": sum([item.count for item in occupation_education_counts])
    }
    
    return jsonify(response)

# V, W, X. Location by Education
@admin.route('/location_by_education', methods=['GET'])
@auth.login_required
def location_by_education():
    # Query to count location preferences by education level
    location_education_counts = (
        db.session.query(
            JobPreference.province.label('location'),  # Can be changed to municipality or country
            EducationalBackground.degree_or_qualification.label('education_level'),
            func.count(JobPreference.user_id).label('count')
        )
        .join(
            EducationalBackground, 
            JobPreference.user_id == EducationalBackground.user_id
        )
        .group_by(JobPreference.province, EducationalBackground.degree_or_qualification)
        .order_by(JobPreference.province, EducationalBackground.degree_or_qualification)
        .all()
    )
    
    # Process query results to organize by location
    locations = list(set([item.location for item in location_education_counts]))
    education_levels = list(set([item.education_level for item in location_education_counts]))
    
    # Create a dictionary to store counts by education level for each location
    location_education_data = {
        location: {level: 0 for level in education_levels} for location in locations
    }
    
    for item in location_education_counts:
        location_education_data[item.location][item.education_level] = item.count
    
    # Format data for bar chart visualization
    bar_datasets = []
    colors = [
        "rgba(54, 162, 235, 0.6)", "rgba(255, 99, 132, 0.6)",
        "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)",
        "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)",
        "rgba(199, 199, 199, 0.6)", "rgba(83, 102, 255, 0.6)"
    ]
    
    for i, level in enumerate(education_levels):
        bar_datasets.append({
            "label": level,
            "data": [location_education_data[location][level] for location in locations],
            "backgroundColor": colors[i % len(colors)],
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "borderWidth": 1
        })
    
    # Format data for line chart visualization
    line_datasets = []
    
    # Reorganize data for line chart (education level on x-axis)
    location_counts_by_education = {location: [] for location in locations}
    
    for location in locations:
        for level in education_levels:
            location_counts_by_education[location].append(location_education_data[location][level])
    
    for i, location in enumerate(locations):
        line_datasets.append({
            "label": location,
            "data": location_counts_by_education[location],
            "backgroundColor": "transparent",
            "borderColor": colors[i % len(colors)].replace("0.6", "1"),
            "pointBackgroundColor": colors[i % len(colors)],
            "tension": 0.1,
            "fill": False
        })
    
    response = {
        "bar_chart_data": {
            "labels": locations,  # X-axis: Locations
            "datasets": bar_datasets  # Y-axis: Counts by education level
        },
        "line_chart_data": {
            "labels": education_levels,  # X-axis: Education levels
            "datasets": line_datasets  # Y-axis: Counts by location
        },
        "total_records": sum([item.count for item in location_education_counts])
    }
    
    return jsonify(response)

###########################################################################################################################################
#                                                              JOB PLACEMENT REPORT
###########################################################################################################################################
# 1. Placement Report by Country
@admin.route('/placement_by_country', methods=['GET'])
@auth.login_required
def placement_by_country():
    # Optional date range filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = (
        db.session.query(
            EmployerJobPosting.country.label('country'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('hired_count')
        )
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
    )
    
    # Apply date filters if provided
    if start_date:
        query = query.filter(StudentJobseekerApplyJobs.updated_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(StudentJobseekerApplyJobs.updated_at <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    # Complete the query
    hired_by_country = (
        query
        .group_by(EmployerJobPosting.country)
        .order_by(desc('hired_count'))
        .all()
    )
    
    # Calculate total hires for percentage calculation
    total_hired = sum(item.hired_count for item in hired_by_country)
    
    # Format the data for visualization
    countries = []
    hired_counts = []
    percentages = []
    
    for item in hired_by_country:
        countries.append(item.country)
        hired_counts.append(item.hired_count)
        percentage = (item.hired_count / total_hired * 100) if total_hired > 0 else 0
        percentages.append(round(percentage, 2))
    
    # Prepare the response
    response = {
        "chart_data": {
            "countries": countries,
            "hired_counts": hired_counts,
            "percentages": percentages,
            "total_hired": total_hired
        }
    }
    
    return jsonify(response)

# Country Hiring Trends
@admin.route('/country_hiring_trends', methods=['GET'])
@auth.login_required
def country_hiring_trends():
    # Get trends over the past 12 months by default
    months_ago = int(request.args.get('months', 12))
    start_date = datetime.utcnow() - timedelta(days=months_ago * 30)
    
    # Query to get top 5 countries by hire count
    top_countries = (
        db.session.query(EmployerJobPosting.country)
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
        .group_by(EmployerJobPosting.country)
        .order_by(desc(func.count(StudentJobseekerApplyJobs.apply_job_id)))
        .limit(5)
        .all()
    )
    
    top_country_names = [country.country for country in top_countries]
    
    # Get monthly hire data for each top country
    monthly_data = {}
    all_months = []
    
    for country in top_country_names:
        hiring_trend = (
            db.session.query(
                func.date_trunc('month', StudentJobseekerApplyJobs.updated_at).label('month'),
                func.count(StudentJobseekerApplyJobs.apply_job_id).label('count')
            )
            .join(
                EmployerJobPosting,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(StudentJobseekerApplyJobs.status == 'hired')
            .filter(StudentJobseekerApplyJobs.updated_at >= start_date)
            .filter(EmployerJobPosting.country == country)
            .group_by('month')
            .order_by('month')
            .all()
        )
        
        country_months = [item.month.strftime('%Y-%m') for item in hiring_trend]
        country_counts = [item.count for item in hiring_trend]
        
        monthly_data[country] = {
            "months": country_months,
            "counts": country_counts
        }
        
        # Track all months across all countries
        all_months.extend(country_months)
    
    # Get unique, sorted list of all months
    unique_months = sorted(list(set(all_months)))
    
    # Prepare the datasets for the line chart
    datasets = []
    colors = [
        "rgba(54, 162, 235, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(153, 102, 255, 1)",
        "rgba(255, 159, 64, 1)"
    ]
    
    for i, country in enumerate(top_country_names):
        # Create a lookup dictionary for this country's data
        data_dict = {month: 0 for month in unique_months}
        
        # Fill in actual values
        for j, month in enumerate(monthly_data[country]["months"]):
            data_dict[month] = monthly_data[country]["counts"][j]
        
        # Convert to ordered list matching unique_months
        ordered_data = [data_dict[month] for month in unique_months]
        
        datasets.append({
            "label": country,
            "data": ordered_data,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "pointBackgroundColor": colors[i % len(colors)],
            "pointBorderColor": "#fff",
            "pointHoverBackgroundColor": "#fff",
            "pointHoverBorderColor": colors[i % len(colors)],
            "tension": 0.1
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "labels": unique_months,  # X-axis: Months
            "datasets": datasets
        }
    }
    
    return jsonify(response)

# 2. City/Municipality of Hired Users
@admin.route('/placement_by_city', methods=['GET'])
@auth.login_required
def placement_by_city():
    # Optional country filter
    country = request.args.get('country')
    
    # Base query
    query = (
        db.session.query(
            EmployerJobPosting.country.label('country'),
            EmployerJobPosting.city_municipality.label('city'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('hired_count')
        )
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
    )
    
    # Apply country filter if provided
    if country:
        query = query.filter(EmployerJobPosting.country == country)
    
    # Complete the query
    hired_by_city = (
        query
        .group_by(EmployerJobPosting.country, EmployerJobPosting.city_municipality)
        .order_by(desc('hired_count'))
        .limit(15)  # Top 15 cities
        .all()
    )
    
    # Format the data for visualization
    cities = []
    countries = []
    hired_counts = []
    
    for item in hired_by_city:
        cities.append(item.city)
        countries.append(item.country)
        hired_counts.append(item.hired_count)
    
    # Get job sectors breakdown for top cities
    city_job_sectors = {}
    
    for city in cities:
        job_sectors = (
            db.session.query(
                EmployerJobPosting.job_type.label('job_type'),
                func.count(StudentJobseekerApplyJobs.apply_job_id).label('count')
            )
            .join(
                StudentJobseekerApplyJobs,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(StudentJobseekerApplyJobs.status == 'hired')
            .filter(EmployerJobPosting.city_municipality == city)
            .group_by(EmployerJobPosting.job_type)
            .order_by(desc('count'))
            .all()
        )
        
        city_job_sectors[city] = {
            "job_types": [item.job_type for item in job_sectors],
            "counts": [item.count for item in job_sectors]
        }
    
    # Prepare the response
    response = {
        "chart_data": {
            "cities": cities,
            "countries": countries,
            "hired_counts": hired_counts,
            "job_sectors": city_job_sectors
        }
    }
    
    return jsonify(response)

# City Comparison Table Data
@admin.route('/city_comparison_table', methods=['GET'])
@auth.login_required
def city_comparison_table():
    # Optional country filter
    country = request.args.get('country')
    
    # Define comparison period
    current_period_end = datetime.utcnow()
    current_period_start = current_period_end - timedelta(days=90)  # Last 3 months
    previous_period_end = current_period_start
    previous_period_start = previous_period_end - timedelta(days=90)  # Previous 3 months
    
    # Base query for current period
    current_query = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('city'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('hired_count'),
            func.avg(EmployerJobPosting.estimated_salary_from + EmployerJobPosting.estimated_salary_to).label('avg_salary'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('applications')
        )
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
        .filter(StudentJobseekerApplyJobs.updated_at.between(current_period_start, current_period_end))
    )
    
    # Apply country filter if provided
    if country:
        current_query = current_query.filter(EmployerJobPosting.country == country)
    
    # Complete the current period query
    current_period_data = (
        current_query
        .group_by(EmployerJobPosting.city_municipality)
        .order_by(desc('hired_count'))
        .all()
    )
    
    # Similar query for previous period to calculate growth rate
    previous_query = (
        db.session.query(
            EmployerJobPosting.city_municipality.label('city'),
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('hired_count')
        )
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
        .filter(StudentJobseekerApplyJobs.updated_at.between(previous_period_start, previous_period_end))
    )
    
    # Apply country filter if provided
    if country:
        previous_query = previous_query.filter(EmployerJobPosting.country == country)
    
    # Complete the previous period query
    previous_period_data = (
        previous_query
        .group_by(EmployerJobPosting.city_municipality)
        .all()
    )
    
    # Create lookup for previous period data
    previous_hired = {item.city: item.hired_count for item in previous_period_data}
    
    # Query most common job types for each city
    city_job_types = {}
    for item in current_period_data:
        city = item.city
        
        common_job_types = (
            db.session.query(
                EmployerJobPosting.job_type.label('job_type'),
                func.count(StudentJobseekerApplyJobs.apply_job_id).label('count')
            )
            .join(
                StudentJobseekerApplyJobs,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(StudentJobseekerApplyJobs.status == 'hired')
            .filter(EmployerJobPosting.city_municipality == city)
            .group_by(EmployerJobPosting.job_type)
            .order_by(desc('count'))
            .limit(1)
            .first()
        )
        
        if common_job_types:
            city_job_types[city] = common_job_types.job_type
        else:
            city_job_types[city] = "N/A"
    
    # Format the data for the table
    table_data = []
    
    for item in current_period_data:
        city = item.city
        current_hired = item.hired_count
        previous_hired = previous_hired.get(city, 0)
        
        # Calculate growth rate
        growth_rate = 0
        if previous_hired > 0:
            growth_rate = ((current_hired - previous_hired) / previous_hired) * 100
        
        # Time to hire calculation would require additional data
        # Using a placeholder for now
        avg_time_to_hire = "N/A"  # This would need additional tracking
        
        table_data.append({
            "city": city,
            "hired_count": current_hired,
            "growth_rate": round(growth_rate, 2),
            "avg_salary": round(item.avg_salary, 2) if item.avg_salary else 0,
            "most_common_job": city_job_types.get(city, "N/A"),
            "avg_time_to_hire": avg_time_to_hire
        })
    
    # Sort by hired count
    table_data.sort(key=lambda x: x["hired_count"], reverse=True)
    
    # Prepare the response
    response = {
        "table_data": table_data
    }
    
    return jsonify(response)

# 3. Placement Hired Users by District
@admin.route('/placement_by_district', methods=['GET'])
@auth.login_required
def placement_by_district():
    # Note: This is a simplified implementation since the schema doesn't have a 'district' field
    # In practice, we'd need to map city_municipality to districts or use a geolocation service
    
    # For demonstration, we'll use the country as a proxy for district
    # In a real application, you'd need to implement proper district mapping
    
    # Optional region filter
    region = request.args.get('region')
    
    # Base query using country as a stand-in for district
    query = (
        db.session.query(
            EmployerJobPosting.country.label('region'),  # Using country as proxy for region
            EmployerJobPosting.Deployment_region.label('district'),  # Using Deployment_region as district
            func.count(StudentJobseekerApplyJobs.apply_job_id).label('hired_count')
        )
        .join(
            StudentJobseekerApplyJobs,
            StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
        )
        .filter(StudentJobseekerApplyJobs.status == 'hired')
        .filter(EmployerJobPosting.Deployment_region.isnot(None))  # Ensure district info exists
    )
    
    # Apply region filter if provided
    if region:
        query = query.filter(EmployerJobPosting.country == region)
    
    # Complete the query
    hired_by_district = (
        query
        .group_by(EmployerJobPosting.country, EmployerJobPosting.Deployment_region)
        .order_by(desc('hired_count'))
        .all()
    )
    
    # Calculate total hires for percentage calculation
    total_hired = sum(item.hired_count for item in hired_by_district)
    
    # Format the data for visualization
    regions = []
    districts = []
    hired_counts = []
    percentages = []
    
    for item in hired_by_district:
        regions.append(item.region)
        districts.append(item.district)
        hired_counts.append(item.hired_count)
        percentage = (item.hired_count / total_hired * 100) if total_hired > 0 else 0
        percentages.append(round(percentage, 2))
    
    # Get job type breakdown for each district
    district_job_types = {}
    
    for district in districts:
        job_types = (
            db.session.query(
                EmployerJobPosting.job_type.label('job_type'),
                func.count(StudentJobseekerApplyJobs.apply_job_id).label('count')
            )
            .join(
                StudentJobseekerApplyJobs,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(StudentJobseekerApplyJobs.status == 'hired')
            .filter(EmployerJobPosting.Deployment_region == district)
            .group_by(EmployerJobPosting.job_type)
            .order_by(desc('count'))
            .all()
        )
        
        district_job_types[district] = {
            "job_types": [item.job_type for item in job_types],
            "counts": [item.count for item in job_types]
        }
    
    # Get district performance comparison data
    district_performance = []
    
    for district in districts:
        # Get total applications for this district
        total_applications = (
            db.session.query(func.count(StudentJobseekerApplyJobs.apply_job_id))
            .join(
                EmployerJobPosting,
                StudentJobseekerApplyJobs.employer_jobpost_id == EmployerJobPosting.employer_jobpost_id
            )
            .filter(EmployerJobPosting.Deployment_region == district)
            .scalar() or 0
        )
        
        # Get hired count for this district
        hired_count = next((item.hired_count for item in hired_by_district if item.district == district), 0)
        
        # Calculate hire rate
        hire_rate = (hired_count / total_applications * 100) if total_applications > 0 else 0
        
        district_performance.append({
            "district": district,
            "hired_count": hired_count,
            "total_applications": total_applications,
            "hire_rate": round(hire_rate, 2)
        })
    
    # Prepare the response
    response = {
        "chart_data": {
            "regions": regions,
            "districts": districts,
            "hired_counts": hired_counts,
            "percentages": percentages,
            "job_types": district_job_types,
            "performance": district_performance
        }
    }
    
    return jsonify(response)