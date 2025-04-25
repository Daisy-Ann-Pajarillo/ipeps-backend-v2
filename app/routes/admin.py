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
    
    # Ensure the authenticated user is associated with this application (e.g., employer owns the training post)
    if application.user_id != data['user_id']:
        return jsonify({"error": "Application user_id and your user_id provided didn't match"}), 403
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_trainings.occupied_slots += 1 if data['status'] == 'approved' else 0  # Increment occupied slots if approved
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
    allowed_statuses = ['approved', 'declined', 'applied']
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
    
    # Ensure the authenticated user is associated with this application (e.g., employer owns the scholarship post)
    if application.user_id != data['user_id']:
        return jsonify({"error": "You are not authorized to update this application"}), 403
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_scholarships.occupied_slots += 1 if data['status'] == 'approved' else 0  # Increment occupied slots if approved
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
    allowed_statuses = ['approved', 'declined', 'applied']
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
    
    # Ensure the authenticated user is associated with this application (e.g., employer owns the job post)
    if application.user_id != data['user_id']:
        return jsonify({"error": "You are not authorized to update this application"}), 403
    
    # Update the status
    try:
        application.status = data['status']
        application.updated_at = db.func.current_timestamp()  # Update the timestamp
        application.user_apply_job.no_of_vacancies -= 1 if data['status'] == 'approved' else 0  # Increment occupied slots if approved
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
    - target_audience: list of str (required, e.g., ["Admin", "User"])
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


# ===========================================================================================================================================#
#                                                       ADMIN GET ALL ANNOUNCEMENTS
# ===========================================================================================================================================#
@admin.route('/get-announcements', methods=['GET'])
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

        # Return the list of announcements
        return jsonify(announcements_list), 200

    except Exception as e:
        # Handle unexpected errors
        db.session.rollback()
        return jsonify({"error": "An error occurred", "details": str(e)}), 500