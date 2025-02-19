from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, PersonalInformation, JobPreference, LanguageProficiency, EducationalBackground, WorkExperience, OtherSkills, ProfessionalLicense, OtherTraining, AcademePersonalInformation, EmployerPersonalInformation

from datetime import datetime
from app.utils.user_app_form_helper import get_user_data, exclude_fields

auth = HTTPBasicAuth()

user_application_form = Blueprint("user_application_form", __name__)

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

# Route to add or update personal information for a user jobseeker or student
@user_application_form.route('/add-jobseeker-student-personal-information', methods=['POST'])
# @auth.login_required
def add_or_update_personal_info():
    try:
        # Parse JSON data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check for required fields
        required_fields = (
            "prefix", "first_name", "last_name", "sex", "date_of_birth",
            "place_of_birth", "civil_status", "height", "weight", "religion",
            "temporary_country", "cellphone_number", "employment_status",
            "is_looking_for_work", "is_willing_to_work_immediately"
        )
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Parse date_of_birth
        try:
            date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            if date_of_birth > datetime.now().date():
                return jsonify({"error": "Invalid date_of_birth. Date cannot be in the future."}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format for date_of_birth. Use YYYY-MM-DD."}), 400

        # Parse since_when_looking_for_work (optional field)
        since_when_looking_for_work = None
        if 'since_when_looking_for_work' in data and data['since_when_looking_for_work']:
            try:
                since_when_looking_for_work = datetime.strptime(data['since_when_looking_for_work'], '%Y-%m-%d').date()
                if since_when_looking_for_work > datetime.now().date():
                    return jsonify({"error": "Invalid date for since_when_looking_for_work. Date cannot be in the future."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for since_when_looking_for_work. Use YYYY-MM-DD."}), 400

        # Parse former_ofw_country_date_return (optional field)
        former_ofw_country_date_return = None
        if 'former_ofw_country_date_return' in data and data['former_ofw_country_date_return']:
            try:
                former_ofw_country_date_return = datetime.strptime(data['former_ofw_country_date_return'], '%Y-%m-%d').date()
                if former_ofw_country_date_return > datetime.now().date():
                    return jsonify({"error": "Invalid date for former_ofw_country_date_return. Future dates are not allowed."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for former_ofw_country_date_return. Use YYYY-MM-DD."}), 400

        # Convert height and weight to float
        try:
            height = float(data['height'])
            weight = float(data['weight'])
        except ValueError:
            return jsonify({"error": "Invalid value for height or weight. Must be a number."}), 400

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if personal information already exists for the user
        personal_info = PersonalInformation.query.filter_by(user_id=uid).first()

        # Create or update personal information
        if personal_info:
            message = "Personal information updated successfully"
        else:
            personal_info = PersonalInformation(user_id=uid)
            db.session.add(personal_info)
            message = "Personal information added successfully"

        # Add or update fields
        personal_info.prefix = data.get('prefix')
        personal_info.first_name = data['first_name']
        personal_info.middle_name = data.get('middle_name')
        personal_info.last_name = data['last_name']
        personal_info.suffix = data.get('suffix')
        personal_info.sex = data['sex']
        personal_info.date_of_birth = date_of_birth
        personal_info.place_of_birth = data['place_of_birth']
        personal_info.civil_status = data['civil_status']
        personal_info.height = height
        personal_info.weight = weight
        personal_info.religion = data['religion']

        # Temporary Address
        personal_info.temporary_country = data.get('temporary_country')
        personal_info.temporary_province = data.get('temporary_province')
        personal_info.temporary_municipality = data.get('temporary_municipality')
        personal_info.temporary_zip_code = data.get('temporary_zip_code')
        personal_info.temporary_barangay = data.get('temporary_barangay')
        personal_info.temporary_house_no_street_village = data.get('temporary_house_no_street_village')

        # Permanent Address
        personal_info.permanent_country = data.get('permanent_country')
        personal_info.permanent_province = data.get('permanent_province')
        personal_info.permanent_municipality = data.get('permanent_municipality')
        personal_info.permanent_zip_code = data.get('permanent_zip_code')
        personal_info.permanent_barangay = data.get('permanent_barangay')
        personal_info.permanent_house_no_street_village = data.get('permanent_house_no_street_village')

        # Contact Information
        personal_info.cellphone_number = data['cellphone_number']
        personal_info.landline_number = data.get('landline_number')

        # Government IDs
        personal_info.tin = data.get('tin')
        personal_info.sss_gsis_number = data.get('sss_gsis_number')
        personal_info.pag_ibig_number = data.get('pag_ibig_number')
        personal_info.phil_health_no = data.get('phil_health_no')

        # Disabilities
        disabilities = data.get('disabilities', {})
        personal_info.disability = ", ".join(
            [key for key, value in disabilities.items() if value]
        ) if disabilities else None

        # Employment Details
        personal_info.employment_status = data['employment_status']
        personal_info.is_looking_for_work = data.get('is_looking_for_work', False)
        personal_info.since_when_looking_for_work = since_when_looking_for_work
        personal_info.is_willing_to_work_immediately = data.get('is_willing_to_work_immediately', False)
        personal_info.is_ofw = data.get('is_ofw', False)
        personal_info.ofw_country = data.get('ofw_country')
        personal_info.is_former_ofw = data.get('is_former_ofw', False)
        personal_info.former_ofw_country = data.get('former_ofw_country')
        personal_info.former_ofw_country_date_return = former_ofw_country_date_return
        personal_info.is_4ps_beneficiary = data.get('is_4ps_beneficiary', False)
        personal_info._4ps_household_id_no = data.get('_4ps_household_id_no')

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "message": message,
        }), 200 if personal_info.id else 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
            
# # GET PERSONAL INFO DETAILS OF JOBSEEKER OR STUDENT
# @user_application_form.route('/get-jobseeker-student-personal-information', methods=['GET'])
# # @auth.login_required
# def get_jobseeker_student_personal_info():
#     try:
#         # Check if user exists
#         uid = 4 # for testing
#         user = User.query.get(uid)
#         if not user:
#             return jsonify({"error": "User not found"}), 404

#         # Retrieve personal information for the user
#         personal_info = PersonalInformation.query.filter_by(user_id=uid).first()
#         if not personal_info:
#             return jsonify({"error": "Personal information not found"}), 404

#         # Parse disabilities into a dictionary
#         disabilities = {}
#         if personal_info.disability:
#             disability_list = [item.strip() for item in personal_info.disability.split(",")]
#             disabilities = {
#                 "visual": "visual" in disability_list,
#                 "hearing": "hearing" in disability_list,
#                 "speech": "speech" in disability_list,
#                 "physical": "physical" in disability_list
#             }

#         # Return the personal information
#         return jsonify({
#             "personal_info": {
#                 "first_name": personal_info.first_name,
#                 "middle_name": personal_info.middle_name,
#                 "last_name": personal_info.last_name,
#                 "suffix": personal_info.suffix,
#                 "sex": personal_info.sex,
#                 "date_of_birth": personal_info.date_of_birth.strftime('%Y-%m-%d'),
#                 "place_of_birth": personal_info.place_of_birth,
#                 "civil_status": personal_info.civil_status,
#                 "height": personal_info.height,
#                 "weight": personal_info.weight,
#                 "religion": personal_info.religion,
#                 "temporary_country": personal_info.temporary_country,
#                 "temporary_province": personal_info.temporary_province,
#                 "temporary_municipality": personal_info.temporary_municipality,
#                 "temporary_zip_code": personal_info.temporary_zip_code,
#                 "temporary_barangay": personal_info.temporary_barangay,
#                 "temporary_house_no_street_village": personal_info.temporary_house_no_street_village,
#                 "permanent_country": personal_info.permanent_country,
#                 "permanent_province": personal_info.permanent_province,
#                 "permanent_municipality": personal_info.permanent_municipality,
#                 "permanent_zip_code": personal_info.permanent_zip_code,
#                 "permanent_barangay": personal_info.permanent_barangay,
#                 "permanent_house_no_street_village": personal_info.permanent_house_no_street_village,
#                 "cellphone_number": personal_info.cellphone_number,
#                 "landline_number": personal_info.landline_number,
#                 "tin": personal_info.tin,
#                 "sss_gsis_number": personal_info.sss_gsis_number,
#                 "pag_ibig_number": personal_info.pag_ibig_number,
#                 "phil_health_no": personal_info.phil_health_no,
#                 "disabilities": disabilities,  # Updated to match frontend format
#                 "employment_status": personal_info.employment_status,
#                 "is_looking_for_work": personal_info.is_looking_for_work,
#                 "since_when_looking_for_work": personal_info.since_when_looking_for_work.strftime('%Y-%m-%d') if personal_info.since_when_looking_for_work else None,
#                 "is_willing_to_work_immediately": personal_info.is_willing_to_work_immediately,
#                 "is_ofw": personal_info.is_ofw,
#                 "ofw_country": personal_info.ofw_country,
#                 "is_former_ofw": personal_info.is_former_ofw,
#                 "former_ofw_country": personal_info.former_ofw_country,
#                 "former_ofw_country_date_return": personal_info.former_ofw_country_date_return.strftime('%Y-%m-%d') if personal_info.former_ofw_country_date_return else None,
#                 "is_4ps_beneficiary": personal_info.is_4ps_beneficiary,
#                 "_4ps_household_id_no": personal_info._4ps_household_id_no
#             }
#         }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ADD/UPDATE JOB PREFERENCE DATA
@user_application_form.route('/add-jobseeker-student-job-preference', methods=['POST'])
# @auth.login_required
def add_update_job_preference():
    try:
        # Parse JSON data
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Validate required fields
        required_fields = [
            'country', 'province', 'municipality', 
            'industry', 'preferred_occupation', 
            'salary_from', 'salary_to'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Validate salary range
        try:
            salary_from = float(data['salary_from'])
            salary_to = float(data['salary_to'])
            if salary_from < 0 or salary_to < 0:
                return jsonify({
                    "success": False,
                    "error": "Salary values must be non-negative."
                }), 400
            if salary_from > salary_to:
                return jsonify({
                    "success": False,
                    "error": "salary_from cannot be greater than salary_to."
                }), 400
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Invalid value for salary_from or salary_to. Must be a number."
            }), 400

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404

        # Check if a job preference already exists for the user
        job_preference = JobPreference.query.filter_by(user_id=uid).first()

        if job_preference:
            # Update existing job preference
            job_preference.country = data['country']
            job_preference.province = data['province']
            job_preference.municipality = data['municipality']
            job_preference.industry = data['industry']
            job_preference.preferred_occupation = data['preferred_occupation']
            job_preference.salary_from = salary_from
            job_preference.salary_to = salary_to
            message = "Job preference updated successfully"
        else:
            # Create a new job preference
            job_preference = JobPreference(
                user_id=uid,
                country=data['country'],
                province=data['province'],
                municipality=data['municipality'],
                industry=data['industry'],
                preferred_occupation=data['preferred_occupation'],
                salary_from=salary_from,
                salary_to=salary_to
            )
            db.session.add(job_preference)
            message = "Job preference added successfully"

        # Commit changes to the database
        db.session.commit()

        # Return success response
        return jsonify({
            "success": True,
            "message": message
        }), 200

    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
# ADD/UPDATE LANGUAGE PROFICIENCY
@user_application_form.route('/add-jobseeker-student-language-proficiency', methods=['POST'])
def add_language_proficiency():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            data = [data]
        
        uid = 4
        
        for entry in data:
            required_fields = ["language", "can_read", "can_write", "can_speak", "can_understand"]
            missing_fields = [field for field in required_fields if field not in entry]
            if missing_fields:
                return jsonify({"success": False, "error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
            
            boolean_fields = ["can_read", "can_write", "can_speak", "can_understand"]
            for field in boolean_fields:
                if not isinstance(entry[field], bool):
                    return jsonify({"success": False, "error": f"Invalid value for {field}. Must be a boolean (true/false)."}), 400
            
            user = User.query.get(uid)
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            language_proficiency = LanguageProficiency.query.filter_by(user_id=uid, language=entry['language']).first()
            
            if language_proficiency:
                language_proficiency.can_read = entry['can_read']
                language_proficiency.can_write = entry['can_write']
                language_proficiency.can_speak = entry['can_speak']
                language_proficiency.can_understand = entry['can_understand']
            else:
                new_language_proficiency = LanguageProficiency(
                    user_id=uid,
                    language=entry['language'],
                    can_read=entry['can_read'],
                    can_write=entry['can_write'],
                    can_speak=entry['can_speak'],
                    can_understand=entry['can_understand']
                )
                db.session.add(new_language_proficiency)
        
        db.session.commit()
        return jsonify({"success": True, "message": "All language proficiencies processed successfully"}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# # GET JOB PREFERENCE DATA
# @user_application_form.route('/get-jobseeker-student-job-preference', methods=['GET'])
# @auth.login_required
# def get_job_preference():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve job preference for the user
#         job_preference = JobPreference.query.filter_by(user_id=g.user.user_id).first()
#         if not job_preference:
#             return jsonify({"error": "Job preference not found"}), 404
        
#         # Return the job preference
#         return jsonify({
#             "job_preference": {
#                 "country": job_preference.country,
#                 "municipality": job_preference.municipality,
#                 "industry": job_preference.industry,
#                 "preferred_occupation": job_preference.preferred_occupation,
#                 "salary_from": job_preference.salary_from,
#                 "salary_to": job_preference.salary_to
#             }
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # GET LAUNGUAGE PROFICIENCY DATA
# @user_application_form.route('/get-jobseeker-student-language-proficiency', methods=['GET'])
# @auth.login_required
# def get_language_proficiency():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all language proficiencies for the user
#         language_proficiencies = LanguageProficiency.query.filter_by(user_id=g.user.user_id).all()
#         if not language_proficiencies:
#             return jsonify({"error": "Language proficiency not found"}), 404
        
#         # Format the response
#         proficiency_list = []
#         for proficiency in language_proficiencies:
#             proficiency_list.append({
#                 "language": proficiency.language,
#                 "can_read": proficiency.can_read,
#                 "can_write": proficiency.can_write,
#                 "can_speak": proficiency.can_speak,
#                 "can_understand": proficiency.can_understand
#             })
        
#         # Return the language proficiencies
#         return jsonify({
#             "language_proficiencies": proficiency_list
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ADD EDUCATIONAL BACKGROUND
@user_application_form.route('/add-jobseeker-student-educational-background', methods=['POST'])
# @auth.login_required
def add_educational_background():
    try:
        # Parse JSON data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check for required fields
        required_fields = (
            "school_name", "date_from", "degree_or_qualification",
            "field_of_study", "program_duration"
        )
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Parse date_from
        try:
            date_from = datetime.strptime(data['date_from'], '%Y-%m-%d').date()
            if date_from > datetime.now().date():
                return jsonify({"error": "Invalid date_from. Date cannot be in the future."}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format for date_from. Use YYYY-MM-DD."}), 400

        # Parse date_to (optional field)
        date_to = None
        if 'date_to' in data and data['date_to']:
            try:
                date_to = datetime.strptime(data['date_to'], '%Y-%m-%d').date()
                if date_to > datetime.now().date():
                    return jsonify({"error": "Invalid date_to. Date cannot be in the future."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for date_to. Use YYYY-MM-DD."}), 400

        # Convert program_duration to integer
        try:
            program_duration = int(data['program_duration'])
            if program_duration <= 0:
                return jsonify({"error": "Invalid value for program_duration. Must be a positive integer."}), 400
        except ValueError:
            return jsonify({"error": "Invalid value for program_duration. Must be an integer."}), 400

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if educational background already exists for the user and school
        educational_background = EducationalBackground.query.filter_by(
            user_id=uid, school_name=data['school_name']
        ).first()

        # Create or update educational background
        if educational_background:
            message = "Educational background updated successfully"
        else:
            educational_background = EducationalBackground(user_id=uid)
            db.session.add(educational_background)
            message = "Educational background added successfully"

        # Add or update fields
        educational_background.school_name = data['school_name']
        educational_background.date_from = date_from
        educational_background.date_to = date_to
        educational_background.degree_or_qualification = data['degree_or_qualification']
        educational_background.field_of_study = data['field_of_study']
        educational_background.program_duration = program_duration

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "message": message,
        }), 200 if educational_background.id else 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# # GET EDUCATIONAL BACKGROUND DATA
# @user_application_form.route('/get-jobseeker-student-educational-background', methods=['GET'])
# @auth.login_required
# def get_educational_background():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all educational backgrounds for the user
#         educational_backgrounds = EducationalBackground.query.filter_by(user_id=g.user.user_id).all()
#         if not educational_backgrounds:
#             return jsonify({"error": "Educational background not found"}), 404
        
#         # Format the response
#         background_list = []
#         for background in educational_backgrounds:
#             background_list.append({
#                 "school_name": background.school_name,
#                 "date_from": background.date_from.strftime('%Y-%m-%d'),
#                 "date_to": background.date_to.strftime('%Y-%m-%d') if background.date_to else None,
#                 "degree_or_qualification": background.degree_or_qualification,
#                 "field_of_study": background.field_of_study,
#                 "program_duration": background.program_duration
#             })
        
#         # Return the educational backgrounds
#         return jsonify({
#             "educational_backgrounds": background_list
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ADD OTHER TRAINING DATA
@user_application_form.route('/add-jobseeker-student-other-training', methods=['POST'])
# @auth.login_required
def add_other_training():
    try:
        # Parse JSON data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check for required fields
        required_fields = (
            "course_name", "start_date", "training_institution", "hours_of_training"
        )
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Parse start_date
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if start_date > datetime.now().date():
                return jsonify({"error": "Invalid start_date. Date cannot be in the future."}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format for start_date. Use YYYY-MM-DD."}), 400

        # Parse end_date (optional field)
        end_date = None
        if 'end_date' in data and data['end_date']:
            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                if end_date > datetime.now().date():
                    return jsonify({"error": "Invalid end_date. Date cannot be in the future."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for end_date. Use YYYY-MM-DD."}), 400

        # Convert hours_of_training to integer
        try:
            hours_of_training = int(data['hours_of_training'])
            if hours_of_training <= 0:
                return jsonify({"error": "Invalid value for hours_of_training. Must be a positive integer."}), 400
        except ValueError:
            return jsonify({"error": "Invalid value for hours_of_training. Must be an integer."}), 400

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if training already exists for the user and course
        existing_training = OtherTraining.query.filter_by(
            user_id=uid, course_name=data['course_name']
        ).first()

        # Create or update training
        if existing_training:
            message = "Training updated successfully"
        else:
            existing_training = OtherTraining(user_id=uid)
            db.session.add(existing_training)
            message = "Training added successfully"

        # Add or update fields
        existing_training.course_name = data['course_name']
        existing_training.start_date = start_date
        existing_training.end_date = end_date
        existing_training.training_institution = data['training_institution']
        existing_training.certificates_received = data.get('certificates_received')
        existing_training.hours_of_training = hours_of_training
        existing_training.skills_acquired = data.get('skills_acquired')
        existing_training.credential_id = data.get('credential_id')
        existing_training.credential_url = data.get('credential_url')

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "message": message,
        }), 200 if existing_training.id else 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# # GET OTHER TRAINING DATA
# @user_application_form.route('/get-jobseeker-student-other-training', methods=['GET'])
# @auth.login_required
# def get_other_training():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all training for the user
#         trainings = OtherTraining.query.filter_by(user_id=g.user.user_id).all()
#         if not trainings:
#             return jsonify({"error": "No training found for this user"}), 404
        
#         # Format the response
#         training_list = []
#         for training in trainings:
#             training_list.append({
#                 "course_name": training.course_name,
#                 "start_date": training.start_date.strftime('%Y-%m-%d'),
#                 "end_date": training.end_date.strftime('%Y-%m-%d') if training.end_date else None,
#                 "training_institution": training.training_institution,
#                 "certificates_received": training.certificates_received,
#                 "hours_of_training": training.hours_of_training,
#                 "skills_acquired": training.skills_acquired,
#                 "credential_id": training.credential_id,
#                 "credential_url": training.credential_url
#             })
        
#         # Return the training data
#         return jsonify({
#             "trainings": training_list
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# ADD PROFESSIONAL LICENSE DATA
@user_application_form.route('/add-jobseeker-student-professional-license', methods=['POST'])
# @auth.login_required
def add_professional_license():
    try:
        # Parse JSON data
        data = request.json
        if not data or not isinstance(data, list):
            return jsonify({
                "success": False,
                "error": "Invalid or missing JSON data"
                }), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({
                "success": False,
                "error": "User not found"
                }), 404

        for item in data:
            # Check for required fields
            required_fields = ("license", "name", "date")
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                success = False
                message =  f"Missing required fields: {', '.join(missing_fields)}"
                continue

            # Parse date
            try:
                date = datetime.strptime(item['date'], '%Y-%m-%d').date()
                if date > datetime.now().date():
                    success = False
                    message = "Invalid date. Date cannot be in the future."
                    continue
            except ValueError:
                success = False
                message = "Invalid date format for date. Use YYYY-MM-DD."
                continue

            # Parse valid_until (optional field)
            valid_until = None
            if 'valid_until' in item and item['valid_until']:
                try:
                    valid_until = datetime.strptime(item['valid_until'], '%Y-%m-%d').date()
                    if valid_until < datetime.now().date():
                        success = False
                        message = "Invalid valid_until. Date cannot be in the past."
                        continue
                except ValueError:
                    success = False
                    message = "Invalid date format for valid_until. Use YYYY-MM-DD."
                    continue

            # Parse rating (optional field)
            rating = None
            if 'rating' in item and item['rating'] is not None:
                try:
                    rating = int(item['rating'])
                    if rating < 0:
                        success = False
                        message = "Invalid value for rating. Must be a non-negative integer."
                        continue
                except ValueError:
                    success = False
                    message = "Invalid value for rating. Must be an integer."
                    continue

            # Check if the license already exists for the user
            existing_license = ProfessionalLicense.query.filter_by(
                user_id=uid, license=item['license']
            ).first()

            if existing_license:
                # Update existing license
                existing_license.name = item['name']
                existing_license.date = date
                existing_license.valid_until = valid_until
                existing_license.rating = rating
                success = True
                message = "Professional license updated successfully"
            else:
                # Create new license entry
                new_license = ProfessionalLicense(
                    user_id=uid,
                    license=item['license'],
                    name=item['name'],
                    date=date,
                    valid_until=valid_until,
                    rating=rating
                )
                success = True
                db.session.add(new_license)
                message = "Professional license added successfully"

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": success,
            "results": message
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# # GET PROFESSIONAL LICENSE DATA
# @user_application_form.route('/get-jobseeker-student-professional-license', methods=['GET'])
# @auth.login_required
# def get_professional_license():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all licenses for the user
#         licenses = ProfessionalLicense.query.filter_by(user_id=g.user.user_id).all()
#         if not licenses:
#             return jsonify([]), 200  # Return an empty array if no licenses exist
        
#         # Format the response to match the frontend's expected format
#         license_list = []
#         for license in licenses:
#             license_list.append({
#                 "type": license.license,  # Map `license` to `type`
#                 "name": license.name,
#                 "date": license.date.strftime('%Y-%m-%d'),  # Format date as string
#                 "rating": license.rating,  # Include rating (can be null)
#                 "validity": license.valid_until.strftime('%Y-%m-%d') if license.valid_until else None  # Handle null validity
#             })
        
#         # Return the license data
#         return jsonify(license_list), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ADD WORK EXPERIECE DATA
@user_application_form.route('/add-jobseeker-student-work-experience', methods=['POST'])
# @auth.login_required
def add_work_experience():
    try:
        # Parse JSON data
        data = request.json
        if not data or not isinstance(data, list):
            return jsonify({"error": "Invalid or missing JSON data. Expected a list of work experiences."}), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404


        for item in data:
            # Check for required fields
            required_fields = ("company_name", "position", "employment_status", "date_start")
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                    success= False
                    message = f"Missing required fields: {', '.join(missing_fields)}"

            # Parse date_start
            try:
                date_start = datetime.strptime(item['date_start'], '%Y-%m-%d').date()
                if date_start > datetime.now().date():
                        success = False
                        message = "Invalid date_start. Date cannot be in the future."
            except ValueError:
                    success= False
                    message =  "Invalid date format for date_start. Use YYYY-MM-DD."

            # Parse date_end (optional field)
            date_end = None
            if 'date_end' in item and item['date_end']:
                try:
                    date_end = datetime.strptime(item['date_end'], '%Y-%m-%d').date()
                    if date_end < date_start:
                            success= False
                            message = "Invalid date_end. End date cannot be before start date."
                except ValueError:
                        success = False
                        message = "Invalid date format for date_end. Use YYYY-MM-DD."

            # Check if work experience already exists for the user
            existing_experience = WorkExperience.query.filter_by(
                user_id=uid,
                company_name=item['company_name'],
                position=item['position']
            ).first()

            if existing_experience:
                # Update existing work experience
                existing_experience.company_address = item.get('company_address')
                existing_experience.employment_status = item['employment_status']
                existing_experience.date_start = date_start
                existing_experience.date_end = date_end
                message = "Work experience updated successfully"
                success = True
            else:
                # Create new work experience entry
                new_experience = WorkExperience(
                    user_id=uid,
                    company_name=item['company_name'],
                    company_address=item.get('company_address'),
                    position=item['position'],
                    employment_status=item['employment_status'],
                    date_start=date_start,
                    date_end=date_end
                )
                db.session.add(new_experience)
                success = True
                message = "Work experience added successfully"

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": success,
            "message": message
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# # GET WORK EXPERIENCE DATA
# @user_application_form.route('/get-jobseeker-student-work-experience', methods=['GET'])
# @auth.login_required
# def get_work_experience():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all work experiences for the user
#         work_experiences = WorkExperience.query.filter_by(user_id=g.user.user_id).all()
#         if not work_experiences:
#             return jsonify({"error": "Work experience not found"}), 404
        
#         # Format the response
#         experience_list = []
#         for experience in work_experiences:
#             experience_list.append({
#                 "company_name": experience.company_name,
#                 "company_address": experience.company_address,
#                 "position": experience.position,
#                 "employment_status": experience.employment_status,
#                 "date_start": experience.date_start.strftime('%Y-%m-%d'),
#                 "date_end": experience.date_end.strftime('%Y-%m-%d') if experience.date_end else None
#             })
        
#         # Return the work experiences
#         return jsonify({
#             "work_experiences": experience_list
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# ADD OTHER SKILLS DATA
@user_application_form.route('/add-jobseeker-student-other-skills', methods=['POST'])
# @auth.login_required
def add_other_skills():
    try:
        # Parse JSON data
        data = request.json
        if not isinstance(data, list):
            return jsonify({"error": "Invalid input format. Expected a list of skills."}), 400

        # Hardcoded user ID for testing (replace with g.user.user_id when using authentication)
        uid = 4

        # Check if user exists
        user = User.query.get(uid)
        if not user:
            return jsonify({"error": "User not found"}), 404

        results = []  # To store results for each skill

        for skill_name in data:
            # Validate skill name
            if not skill_name or not isinstance(skill_name, str):
                results.append({
                    "entry": skill_name,
                    "error": "Invalid skill name. Must be a non-empty string."
                })
                continue

            # Check if the skill already exists for the user
            existing_skill = OtherSkills.query.filter_by(
                user_id=uid,
                skills=skill_name
            ).first()

            if existing_skill:
                # Update existing skill (if needed, though skills are usually static)
                existing_skill.skills = skill_name
                message = f"Skill '{skill_name}' updated successfully"
            else:
                # Create new skill entry
                new_skill = OtherSkills(
                    user_id=uid,
                    skills=skill_name
                )
                db.session.add(new_skill)
                message = f"Skill '{skill_name}' added successfully"

            results.append({
                "entry": skill_name,
                "message": message
            })

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "results": results
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# # GETTING THE OTHER SKILLS DATA
# @user_application_form.route('/get-jobseeker-student-other-skills', methods=['GET'])
# @auth.login_required
# def get_other_skills():
#     try:
#         # Check if user exists
#         user = User.query.get(g.user.user_id)
#         if not user:
#             return jsonify({"error": "User not found"}), 404
        
#         # Retrieve all skills for the user
#         skills = OtherSkills.query.filter_by(user_id=g.user.user_id).all()
#         if not skills:
#             return jsonify({"error": "No skills found for this user"}), 404
        
#         # Format the response
#         skills_list = [{"skills": skill.skills} for skill in skills]
        
#         # Return the skills
#         return jsonify({
#             "skills": skills_list
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# GETTING ALL THE DATA FOR REVIEW
@user_application_form.route('/get-jobseeker-student-all-data', methods=['GET'])
# @auth.login_required
def get_all_data():
    try:
        user_id = 4 # For testing

        # Fetch all data using the generic helper function
        personal_info = get_user_data(PersonalInformation, user_id)
        job_preference = get_user_data(JobPreference, user_id)
        language_proficiency = get_user_data(LanguageProficiency, user_id)
        educational_background = get_user_data(EducationalBackground, user_id)
        other_training = get_user_data(OtherTraining, user_id)
        professional_license = get_user_data(ProfessionalLicense, user_id)
        work_experience = get_user_data(WorkExperience, user_id)
        other_skills = get_user_data(OtherSkills, user_id)

        # Format the response
        return jsonify({
            "personal_information": exclude_fields(personal_info),
            "job_preference": exclude_fields(job_preference),
            "language_proficiency": exclude_fields(language_proficiency),
            "educational_background": exclude_fields(educational_background),
            "other_training": exclude_fields(other_training),
            "professional_license": exclude_fields(professional_license),
            "work_experience": exclude_fields(work_experience),
            "other_skills": exclude_fields(other_skills)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# Routes for ACADEME TABLE
# ---------------------------------------------------------------------------------------------------------------------------------------------------------

# Route to add or update Academe Personal Information
@user_application_form.route('/add-academe-personal-information', methods=['POST'])
# @auth.login_required
def add_or_update_academe_personal_info():
    try:
        uid = 7 # for testing

        # Parse JSON data
        data = request.json

        user = User.query.filter_by(user_id=uid).first()
        print("user type : ",user.user_type)
        if user.user_type != "ACADEME":
            return jsonify({"error": "User is not ACADEME"}), 400

        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if not uid:
            return jsonify({"error": "user_id is required"}), 400

        # Check if personal information already exists for the user
        academe_info = AcademePersonalInformation.query.filter_by(user_id=uid).first()

        # Create or update personal information
        if academe_info:
            message = "Academe personal information updated successfully"
        else:
            academe_info = AcademePersonalInformation(user_id=uid)
            db.session.add(academe_info)
            message = "Academe personal information added successfully"

        # Update fields
        academe_info.prefix = data.get('prefix', academe_info.prefix)
        academe_info.first_name = data.get('first_name', academe_info.first_name)
        academe_info.middle_name = data.get('middle_name', academe_info.middle_name)
        academe_info.last_name = data.get('last_name', academe_info.last_name)
        academe_info.suffix = data.get('suffix', academe_info.suffix)
        academe_info.institution_name = data.get('institution_name', academe_info.institution_name)
        academe_info.institution_type = data.get('institution_type', academe_info.institution_type)
        academe_info.email = data.get('company_email', academe_info.email)
        academe_info.employer_position = data.get('employer_position', academe_info.employer_position)
        academe_info.employer_id_number = data.get('employer_id_number', academe_info.employer_id_number)
        academe_info.temporary_country = data.get('country', academe_info.temporary_country)
        academe_info.temporary_province = data.get('province', academe_info.temporary_province)
        academe_info.temporary_municipality = data.get('municipality', academe_info.temporary_municipality)
        academe_info.temporary_zip_code = data.get('zipcode', academe_info.temporary_zip_code)
        academe_info.temporary_barangay = data.get('barangay', academe_info.temporary_barangay)
        academe_info.temporary_house_no_street_village = data.get('housestreet', academe_info.temporary_house_no_street_village)
        academe_info.permanent_country = data.get('permanent_country', academe_info.permanent_country)
        academe_info.permanent_province = data.get('permanent_province', academe_info.permanent_province)
        academe_info.permanent_municipality = data.get('permanent_municipality', academe_info.permanent_municipality)
        academe_info.permanent_zip_code = data.get('permanent_zip_code', academe_info.permanent_zip_code)
        academe_info.permanent_barangay = data.get('permanent_barangay', academe_info.permanent_barangay)
        academe_info.permanent_house_no_street_village = data.get('permanent_house_no_street_village', academe_info.permanent_house_no_street_village)
        academe_info.cellphone_number = data.get('cellphone_number', academe_info.cellphone_number)
        academe_info.landline_number = data.get('landline_number', academe_info.landline_number)
        academe_info.valid_id_url = data.get('valid_id_url', academe_info.valid_id_url)

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "message": message,
        }), 201 if not academe_info.id else 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Route to get Academe Personal Information
@user_application_form.route('/get-academe-personal-information', methods=['GET'])
# @auth.login_required
def get_academe_personal_info():
    try:
        uid = 7 # For testing
        # Retrieve personal information for the user
        academe_info = get_user_data(AcademePersonalInformation, uid)

        if not academe_info:
            return jsonify({"error": "Academe personal information not found"}), 404
        
        def exclude_fields(data_list):
            filtered_data = []
            for item in data_list:
                item_dict = item.to_dict()
                # Remove 'id' and 'user_id' fields
                item_dict.pop('id', None)
                item_dict.pop('user_id', None)
                filtered_data.append(item_dict)
            return filtered_data
        
        # Return the personal information
        return jsonify({
            "personal_information": exclude_fields(academe_info)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# Routes for EMPLOYER
# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# Route to add or update Employer Personal Information
@user_application_form.route('/add-employer-personal-information', methods=['POST'])
# @auth.login_required
def add_or_update_employer_personal_info():
    try:
        uid = 8 # For testing
        # Parse JSON data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate user type
        user = User.query.filter_by(user_id=uid).first()
        if not user or user.user_type != "EMPLOYER":
            return jsonify({"error": "User is not EMPLOYER"}), 400

        # Check if personal information already exists for the user
        employer_info = EmployerPersonalInformation.query.filter_by(user_id=uid).first()
        if employer_info:
            message = "Employer personal information updated successfully"
        else:
            employer_info = EmployerPersonalInformation(user_id=uid)
            db.session.add(employer_info)
            message = "Employer personal information added successfully"

        # Update fields
        employer_info.prefix = data.get('prefix', employer_info.prefix)
        employer_info.first_name = data.get('first_name', employer_info.first_name)
        employer_info.middle_name = data.get('middle_name', employer_info.middle_name)
        employer_info.last_name = data.get('last_name', employer_info.last_name)
        employer_info.suffix = data.get('suffix', employer_info.suffix)
        employer_info.company_name = data.get('company', employer_info.company_name)
        employer_info.company_type = data.get('company_type', employer_info.company_type)
        employer_info.company_classification = data.get('company_classification', employer_info.company_classification)
        employer_info.company_industry = data.get('company_industry', employer_info.company_industry)
        employer_info.company_workforce = data.get('company_workforce', employer_info.company_workforce)
        employer_info.email = data.get('company_email', employer_info.email)
        employer_info.employer_position = data.get('employer_position', employer_info.employer_position)
        employer_info.employer_id_number = data.get('employer_id_number', employer_info.employer_id_number)
        employer_info.temporary_country = data.get('temporary_country', employer_info.temporary_country)
        employer_info.temporary_province = data.get('temporary_province', employer_info.temporary_province)
        employer_info.temporary_municipality = data.get('temporary_municipality', employer_info.temporary_municipality)
        employer_info.temporary_zip_code = data.get('temporary_zip_code', employer_info.temporary_zip_code)
        employer_info.temporary_barangay = data.get('temporary_barangay', employer_info.temporary_barangay)
        employer_info.temporary_house_no_street_village = data.get('temporary_house_no_street_village', employer_info.temporary_house_no_street_village)
        employer_info.permanent_country = data.get('permanent_country', employer_info.permanent_country)
        employer_info.permanent_province = data.get('permanent_province', employer_info.permanent_province)
        employer_info.permanent_municipality = data.get('permanent_municipality', employer_info.permanent_municipality)
        employer_info.permanent_zip_code = data.get('permanent_zip_code', employer_info.permanent_zip_code)
        employer_info.permanent_barangay = data.get('permanent_barangay', employer_info.permanent_barangay)
        employer_info.permanent_house_no_street_village = data.get('permanent_house_no_street_village', employer_info.permanent_house_no_street_village)
        employer_info.cellphone_number = data.get('cellphone_number', employer_info.cellphone_number)
        employer_info.landline_number = data.get('landline_number', employer_info.landline_number)
        employer_info.valid_id_url = data.get('valid_id_url', employer_info.valid_id_url)

        # Commit changes to the database
        db.session.commit()

        # Return the response
        return jsonify({
            "success": True,
            "message": message,
        }), 201 if not employer_info.id else 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Route to get EMPLOYER Personal Information 
@user_application_form.route('/get-employer-personal-information', methods=['GET'])
# @auth.login_required
def get_employer_personal_info():
    try:
        uid = 8  # For testing
        # Retrieve personal information for the user
        employer_info = get_user_data(EmployerPersonalInformation, uid)
        if not employer_info:
            return jsonify({"error": "Employer personal information not found"}), 404

        # Return the personal information
        return jsonify({
            "personal_information": exclude_fields(employer_info)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_application_form.route('/get-user-info', methods=['GET'])
# @auth.login_required
def get_personal_info():
    try:
        # Hardcoded user ID for testing purposes
        uid = 4
        

        # Check if uid is None (though it's hardcoded here, this is good practice)
        if uid is None:
            return jsonify({"error": "Missing user_id"}), 400
        
        # Query the database for the user
        user = User.query.filter_by(user_id=uid).first()

        # if user not found return 404
        if user is None:
            return jsonify({"error": "User not found"}), 404
        
        if user.user_type == "STUDENT" or user.user_type == "JOBSEEKER":

            personal_information_data = get_user_data(PersonalInformation, uid)
            get_job_preference = get_user_data(JobPreference, uid)
            language_proficiency = get_user_data(LanguageProficiency, uid)
            educational_background = get_user_data(EducationalBackground, uid)
            other_training = get_user_data(OtherTraining, uid)
            professional_license = get_user_data(ProfessionalLicense, uid)
            work_experience = get_user_data(WorkExperience, uid)
            other_skills = get_user_data(OtherSkills, uid)

            # change disability format
            personal_information = exclude_fields(personal_information_data)
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

            return jsonify({
            "personal_information": personal_information,
            "job_preference": exclude_fields(get_job_preference),
            "language_proficiency": exclude_fields(language_proficiency),
            "educational_background": exclude_fields(educational_background),
            "other_training": exclude_fields(other_training),
            "professional_license": exclude_fields(professional_license),
            "work_experience": exclude_fields(work_experience),
            "other_skills": exclude_fields(other_skills)
        }), 200

        if user.user_type == "EMPLOYER":
            employer = get_user_data(EmployerPersonalInformation, uid)
            return jsonify({
            "personal_information": exclude_fields(employer)
        }), 200

        if user.user_type == "ACADEME":
            academe = get_user_data(AcademePersonalInformation, uid)
            return jsonify({
            "personal_information": exclude_fields(academe)
        }), 200

    except Exception as e:
        # Log the error for debugging purposes (you can replace print with a logging library in production)
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500