from flask import g, Blueprint, request, jsonify
from app import db
from flask_httpauth import HTTPBasicAuth
from app.models import User, PersonalInformation, JobPreference, LanguageProficiency, EducationalBackground, WorkExperience, OtherSkills, ProfessionalLicense, OtherTraining
from datetime import datetime

auth = HTTPBasicAuth()

user_application_form = Blueprint("user_application_form", __name__)

@auth.verify_password
def verify_password(username_or_token, password):
    # Try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # If token authentication fails, try username/password authentication
        user = User.query.filter_by(username=username_or_token).first()
        hash_password = user.password
        if not user or not user.verify_password(password, hash_password):
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
            "first_name", "last_name", "sex", "date_of_birth", 
            "place_of_birth", "civil_status", "cell_phone_no",
            "employment_status", "height", "weight", 
            "religion"
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

        # Parse looking_for_a_work_since (optional field)
        looking_for_a_work_since = None
        if 'looking_for_a_work_since' in data and data['looking_for_a_work_since']:
            try:
                looking_for_a_work_since = datetime.strptime(data['looking_for_a_work_since'], '%Y-%m-%d').date()
                if looking_for_a_work_since > datetime.now().date():
                    return jsonify({"error": "Invalid date for looking_for_a_work_since. Date cannot be in the future."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for looking_for_a_work_since. Use YYYY-MM-DD."}), 400

        # Parse ofw_date_return (optional field)
        ofw_date_return = None
        if 'ofw_date_return' in data and data['ofw_date_return']:
            try:
                ofw_date_return = datetime.strptime(data['ofw_date_return'], '%Y-%m-%d').date()
                if ofw_date_return < datetime.now().date():
                    return jsonify({"error": "Invalid date for ofw_date_return. Future dates are not allowed."}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format for ofw_date_return. Use YYYY-MM-DD."}), 400

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

        # Add or update
        personal_info.first_name = data['first_name']
        personal_info.middle_name = data.get('middle_name', None)
        personal_info.last_name = data['last_name']
        personal_info.sex = data['sex']
        personal_info.suffix = data['suffix']
        personal_info.date_of_birth = date_of_birth
        personal_info.place_of_birth = data['place_of_birth']
        personal_info.civil_status = data['civil_status']
        personal_info.height = height
        personal_info.weight = weight
        personal_info.religion = data['religion']

        # Temporary Address
        personal_info.temporary_country = data.get('country', None)
        personal_info.temporary_province = data.get('province', None)
        personal_info.temporary_municipality = data.get('municipality', None)
        personal_info.temporary_zip_code = data.get('zipcode', None)
        personal_info.temporary_barangay = data.get('barangay', None)
        personal_info.temporary_house_no_street_village = data.get('housestreet', None)

        # Permanent Address
        personal_info.permanent_country = data.get('permanent_country', None)
        personal_info.permanent_province = data.get('permanent_province', None)
        personal_info.permanent_municipality = data.get('permanent_municipality', None)
        personal_info.permanent_zip_code = data.get('permanent_zipcode', None)
        personal_info.permanent_barangay = data.get('permanent_barangay', None)
        personal_info.permanent_house_no_street_village = data.get('permanent_housestreet', None)

        # Contact Information
        personal_info.cellphone_number = data['cell_phone_no']
        personal_info.landline_number = data.get('landlineno', None)

        # Government IDs
        personal_info.tin = data.get('tin', None)
        personal_info.sss_gsis_number = data.get('sss_and_gsis_no', None)
        personal_info.pag_ibig_number = data.get('pagibig_no', None)
        personal_info.phil_health_no = data.get('phil_health_no', None)

        # Disabilities
        disabilities = data.get('disabilities', {})
        personal_info.disability = ", ".join(
            [key for key, value in disabilities.items() if value]
        ) if disabilities else None

        # Employment Details
        personal_info.employment_status = data['employment_status']
        personal_info.is_looking_for_work = data.get('looking_for_a_work') == "YES"
        personal_info.since_when_looking_for_work = looking_for_a_work_since
        personal_info.is_willing_to_work_immediately = data.get('willing_to_work_immediately') == "YES"
        personal_info.is_ofw = data.get('an_ofw') == "YES"
        personal_info.ofw_country = data.get('ofw_country', None)
        personal_info.is_former_ofw = data.get('former_ofw') == "YES"
        personal_info.former_ofw_country = data.get('former_ofw_country', None)
        personal_info.former_ofw_country_date_return = ofw_date_return
        personal_info.is_4ps_beneficiary = data.get('four_ps_beneficiary') == "YES"
        personal_info._4ps_household_id_no = data.get('household_id', None)

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
        
# GET PERSONAL INFO DETAILS OF JOBSEEKER OR STUDENT
@user_application_form.route('/get-jobseeker-student-personal-information', methods=['GET'])
@auth.login_required
def get_personal_info():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Retrieve personal information for the user
        personal_info = PersonalInformation.query.filter_by(user_id=g.user.user_id).first()
        if not personal_info:
            return jsonify({"error": "Personal information not found"}), 404

        # Parse disabilities into a dictionary
        disabilities = {}
        if personal_info.disability:
            disability_list = [item.strip() for item in personal_info.disability.split(",")]
            disabilities = {
                "visual": "visual" in disability_list,
                "hearing": "hearing" in disability_list,
                "speech": "speech" in disability_list,
                "physical": "physical" in disability_list
            }

        # Return the personal information
        return jsonify({
            "personal_info": {
                "first_name": personal_info.first_name,
                "middle_name": personal_info.middle_name,
                "last_name": personal_info.last_name,
                "suffix": personal_info.suffix,
                "sex": personal_info.sex,
                "date_of_birth": personal_info.date_of_birth.strftime('%Y-%m-%d'),
                "place_of_birth": personal_info.place_of_birth,
                "civil_status": personal_info.civil_status,
                "height": personal_info.height,
                "weight": personal_info.weight,
                "religion": personal_info.religion,
                "temporary_country": personal_info.temporary_country,
                "temporary_province": personal_info.temporary_province,
                "temporary_municipality": personal_info.temporary_municipality,
                "temporary_zip_code": personal_info.temporary_zip_code,
                "temporary_barangay": personal_info.temporary_barangay,
                "temporary_house_no_street_village": personal_info.temporary_house_no_street_village,
                "permanent_country": personal_info.permanent_country,
                "permanent_province": personal_info.permanent_province,
                "permanent_municipality": personal_info.permanent_municipality,
                "permanent_zip_code": personal_info.permanent_zip_code,
                "permanent_barangay": personal_info.permanent_barangay,
                "permanent_house_no_street_village": personal_info.permanent_house_no_street_village,
                "cellphone_number": personal_info.cellphone_number,
                "landline_number": personal_info.landline_number,
                "tin": personal_info.tin,
                "sss_gsis_number": personal_info.sss_gsis_number,
                "pag_ibig_number": personal_info.pag_ibig_number,
                "phil_health_no": personal_info.phil_health_no,
                "disabilities": disabilities,  # Updated to match frontend format
                "employment_status": personal_info.employment_status,
                "is_looking_for_work": personal_info.is_looking_for_work,
                "since_when_looking_for_work": personal_info.since_when_looking_for_work.strftime('%Y-%m-%d') if personal_info.since_when_looking_for_work else None,
                "is_willing_to_work_immediately": personal_info.is_willing_to_work_immediately,
                "is_ofw": personal_info.is_ofw,
                "ofw_country": personal_info.ofw_country,
                "is_former_ofw": personal_info.is_former_ofw,
                "former_ofw_country": personal_info.former_ofw_country,
                "former_ofw_country_date_return": personal_info.former_ofw_country_date_return.strftime('%Y-%m-%d') if personal_info.former_ofw_country_date_return else None,
                "is_4ps_beneficiary": personal_info.is_4ps_beneficiary,
                "_4ps_household_id_no": personal_info._4ps_household_id_no
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADD/UPDATE JOB PREFERENCE DATA
@user_application_form.route('/add-jobseeker-student-job-preference', methods=['POST'])
# @auth.login_required
def add_update_job_preference():
    try:

        data = request.json

        uid = 4 # of testing

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
                }), 400

        # Validate required fields
        required_fields = ['country', 'province', 'municipality', 'industry', 'preferredOccupation', 'expectedSalaryRangeFrom', 'expectedSalaryRangeTo']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
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
            job_preference.preferred_occupation = data['preferredOccupation']
            job_preference.salary_from = data['expectedSalaryRangeFrom']
            job_preference.salary_to = data['expectedSalaryRangeTo']
        else:
            # Create a new job preference
            job_preference = JobPreference(
                user_id=uid,
                country=data['country'],
                province = data['province'],
                municipality=data['municipality'],
                industry=data['industry'],
                preferred_occupation=data['preferredOccupation'],
                salary_from=data['expectedSalaryRangeFrom'],
                salary_to=data['expectedSalaryRangeTo']
            )
            db.session.add(job_preference)

        # Commit changes to the database
        db.session.commit()

        # Return success response
        return jsonify({
            "success": True,
            "message": "Job preference added/updated successfully"
        }), 200

    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
            }), 500    

# GET JOB PREFERENCE DATA
@user_application_form.route('/get-jobseeker-student-job-preference', methods=['GET'])
@auth.login_required
def get_job_preference():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve job preference for the user
        job_preference = JobPreference.query.filter_by(user_id=g.user.user_id).first()
        if not job_preference:
            return jsonify({"error": "Job preference not found"}), 404
        
        # Return the job preference
        return jsonify({
            "job_preference": {
                "country": job_preference.country,
                "municipality": job_preference.municipality,
                "industry": job_preference.industry,
                "preferred_occupation": job_preference.preferred_occupation,
                "salary_from": job_preference.salary_from,
                "salary_to": job_preference.salary_to
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to add language proficiency for a user
@user_application_form.route('/add-jobseeker-student-language-proficiency', methods=['POST'])
# @auth.login_required
def add_language_proficiency():
    try:
        # Parse JSON data
        data = request.get_json()
        if not isinstance(data, list):
            data = [data]  # Ensure data is always a list
        
        uid = 4  # For testing (replace with actual user ID later)
        
        for entry in data:
            # Check for required fields
            required_fields = ["name", "read", "write", "speak", "understand"]
            if not all(k in entry for k in required_fields):
                return jsonify({"error": f"Missing required fields in entry: {entry}"}), 400
            
            # Check if user exists
            user = User.query.get(uid)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if language proficiency already exists for the user and language
            language_proficiency = LanguageProficiency.query.filter_by(
                user_id=uid, language=entry['name']
            ).first()
            
            if language_proficiency:
                # Update existing language proficiency
                language_proficiency.can_read = entry['read']
                language_proficiency.can_write = entry['write']
                language_proficiency.can_speak = entry['speak']
                language_proficiency.can_understand = entry['understand']
                message = f"Language proficiency for {entry['name']} updated successfully"
            else:
                # Create new language proficiency entry
                new_language_proficiency = LanguageProficiency(
                    user_id=uid,
                    language=entry['name'],
                    can_read=entry['read'],
                    can_write=entry['write'],
                    can_speak=entry['speak'],
                    can_understand=entry['understand']
                )
                db.session.add(new_language_proficiency)
                message = f"Language proficiency for {entry['name']} added successfully"
        
        # Commit changes to the database
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "All language proficiencies processed successfully",
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET LAUNGUAGE PROFICIENCY DATA
@user_application_form.route('/get-jobseeker-student-language-proficiency', methods=['GET'])
@auth.login_required
def get_language_proficiency():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all language proficiencies for the user
        language_proficiencies = LanguageProficiency.query.filter_by(user_id=g.user.user_id).all()
        if not language_proficiencies:
            return jsonify({"error": "Language proficiency not found"}), 404
        
        # Format the response
        proficiency_list = []
        for proficiency in language_proficiencies:
            proficiency_list.append({
                "language": proficiency.language,
                "can_read": proficiency.can_read,
                "can_write": proficiency.can_write,
                "can_speak": proficiency.can_speak,
                "can_understand": proficiency.can_understand
            })
        
        # Return the language proficiencies
        return jsonify({
            "language_proficiencies": proficiency_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADD EDUCATIONAL BACKGROUND
@user_application_form.route('/add-jobseeker-student-educational-background', methods=['POST'])
# @auth.login_required
def add_educational_background():
    try:
        uid = 4 # for testing
        # Parse JSON data
        data = request.get_json()
        if not isinstance(data, list):
            data = [data]  # Ensure data is always a list
        
        user_id = uid  # Get the authenticated user's ID
        
        results = []  # To store results for each entry
        
        for entry in data:
            # Map frontend field names to backend field names
            mapped_entry = {
                "school_name": entry.get("schoolName"),
                "date_from": entry.get("dateFrom"),
                "date_to": entry.get("dateTo"),  # Optional
                "degree_or_qualification": entry.get("degreeQualification"),
                "field_of_study": entry.get("fieldOfStudy"),
                "program_duration": entry.get("programDuration"),
            }
            
            # Check for required fields
            required_fields = (
                "school_name", "date_from", "degree_or_qualification", 
                "field_of_study", "program_duration"
            )
            if not all(mapped_entry[field] for field in required_fields):
                results.append({
                    "entry": entry,
                    "error": "Missing required fields"
                })
                continue
            
            # Check if user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if educational background already exists for the user and school
            educational_background = EducationalBackground.query.filter_by(
                user_id=user_id, school_name=mapped_entry['school_name']
            ).first()
            
            if educational_background:
                # Update existing educational background
                educational_background.date_from = mapped_entry['date_from']
                educational_background.date_to = mapped_entry['date_to']
                educational_background.degree_or_qualification = mapped_entry['degree_or_qualification']
                educational_background.field_of_study = mapped_entry['field_of_study']
                educational_background.program_duration = mapped_entry['program_duration']
                message = f"Educational background updated successfully"
            else:
                # Create new educational background entry
                new_educational_background = EducationalBackground(
                    user_id=user_id,
                    school_name=mapped_entry['school_name'],
                    date_from=mapped_entry['date_from'],
                    date_to=mapped_entry['date_to'],
                    degree_or_qualification=mapped_entry['degree_or_qualification'],
                    field_of_study=mapped_entry['field_of_study'],
                    program_duration=mapped_entry['program_duration'],
                )
                db.session.add(new_educational_background)
                message = f"Educational background added successfully"
            
            results.append({
                "entry": entry,
                "message": message
            })
        
        # Commit changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "results": results
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET EDUCATIONAL BACKGROUND DATA
@user_application_form.route('/get-jobseeker-student-educational-background', methods=['GET'])
@auth.login_required
def get_educational_background():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all educational backgrounds for the user
        educational_backgrounds = EducationalBackground.query.filter_by(user_id=g.user.user_id).all()
        if not educational_backgrounds:
            return jsonify({"error": "Educational background not found"}), 404
        
        # Format the response
        background_list = []
        for background in educational_backgrounds:
            background_list.append({
                "school_name": background.school_name,
                "date_from": background.date_from.strftime('%Y-%m-%d'),
                "date_to": background.date_to.strftime('%Y-%m-%d') if background.date_to else None,
                "degree_or_qualification": background.degree_or_qualification,
                "field_of_study": background.field_of_study,
                "program_duration": background.program_duration
            })
        
        # Return the educational backgrounds
        return jsonify({
            "educational_backgrounds": background_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADD OTHER TRAINING DATA
@user_application_form.route('/add-jobseeker-student-other-training', methods=['POST'])
# @auth.login_required
def add_other_training():
    try:
        # Parse JSON data
        data = request.get_json()
        if not isinstance(data, list):
            data = [data]  # Ensure data is always a list
        
        user_id = 4  # Get the authenticated user's ID
        
        for entry in data:
            # Map frontend field names to backend field names
            mapped_entry = {
                "course_name": entry.get("courseName"),
                "start_date": entry.get("dateStart"),
                "end_date": entry.get("dateEnd"),  # Optional
                "training_institution": entry.get("trainingInstitution"),
                "certificates_received": entry.get("certificatesReceived"),  # Optional
                "hours_of_training": entry.get("hoursOfTraining"),
                "skills_acquired": entry.get("skillsAcquired"),  # Optional
                "credential_id": entry.get("credentialID"),  # Optional
                "credential_url": entry.get("credentialURL")  # Optional
            }
            
            # Check for required fields
            required_fields = (
                "course_name", "start_date", "training_institution", "hours_of_training"
            )
            if not all(mapped_entry[field] for field in required_fields):
                return jsonify({
                    "success": False,
                    "error": "Missing required fields"
                }), 400
            
            # Check if user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if the training already exists for the user
            existing_training = OtherTraining.query.filter_by(
                user_id=user_id, course_name=mapped_entry['course_name']
            ).first()
            
            if existing_training:
                # Update existing training
                existing_training.start_date = mapped_entry['start_date']
                existing_training.end_date = mapped_entry['end_date']
                existing_training.training_institution = mapped_entry['training_institution']
                existing_training.certificates_received = mapped_entry['certificates_received']
                existing_training.hours_of_training = mapped_entry['hours_of_training']
                existing_training.skills_acquired = mapped_entry['skills_acquired']
                existing_training.credential_id = mapped_entry['credential_id']
                existing_training.credential_url = mapped_entry['credential_url']
                message = f"Training updated successfully"
            else:
                # Create new training entry
                new_training = OtherTraining(
                    user_id=user_id,
                    course_name=mapped_entry['course_name'],
                    start_date=mapped_entry['start_date'],
                    end_date=mapped_entry['end_date'],
                    training_institution=mapped_entry['training_institution'],
                    certificates_received=mapped_entry['certificates_received'],
                    hours_of_training=mapped_entry['hours_of_training'],
                    skills_acquired=mapped_entry['skills_acquired'],
                    credential_id=mapped_entry['credential_id'],
                    credential_url=mapped_entry['credential_url']
                )
                db.session.add(new_training)
                message = f"Training added successfully"
            
        
        # Commit changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": message
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET OTHER TRAINING DATA
@user_application_form.route('/get-jobseeker-student-other-training', methods=['GET'])
@auth.login_required
def get_other_training():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all training for the user
        trainings = OtherTraining.query.filter_by(user_id=g.user.user_id).all()
        if not trainings:
            return jsonify({"error": "No training found for this user"}), 404
        
        # Format the response
        training_list = []
        for training in trainings:
            training_list.append({
                "course_name": training.course_name,
                "start_date": training.start_date.strftime('%Y-%m-%d'),
                "end_date": training.end_date.strftime('%Y-%m-%d') if training.end_date else None,
                "training_institution": training.training_institution,
                "certificates_received": training.certificates_received,
                "hours_of_training": training.hours_of_training,
                "skills_acquired": training.skills_acquired,
                "credential_id": training.credential_id,
                "credential_url": training.credential_url
            })
        
        # Return the training data
        return jsonify({
            "trainings": training_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ADD PROFESSIONAL LICENSE DATA
@user_application_form.route('/add-jobseeker-student-professional-license', methods=['POST'])
@auth.login_required
def add_professional_license():
    try:
        data = request.form
        
        # Check for required fields
        required_fields = ("license", "name", "date")
        if not data or not all(k in data for k in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if the license already exists for the user
        existing_license = ProfessionalLicense.query.filter_by(
            user_id=g.user.user_id, 
            license=data['license']
        ).first()
        
        if existing_license:
            # Update existing license
            existing_license.name = data['name']
            existing_license.date = data['date']
            db.session.commit()
            message = "Professional license updated successfully"
        else:
            # Create new license entry
            new_license = ProfessionalLicense(
                user_id=g.user.user_id,
                license=data['license'],
                name=data['name'],
                date=data['date']
            )
            db.session.add(new_license)
            db.session.commit()
            message = "Professional license added successfully"
        
        # Return the response
        return jsonify({
            "success": True,
            "message": message,
            "license": {
                "license": data['license'],
                "name": data['name'],
                "date": data['date']
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# GET PROFESSIONAL LICENSE DATA
@user_application_form.route('/get-jobseeker-student-professional-license', methods=['GET'])
@auth.login_required
def get_professional_license():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all licenses for the user
        licenses = ProfessionalLicense.query.filter_by(user_id=g.user.user_id).all()
        if not licenses:
            return jsonify({"error": "No professional licenses found for this user"}), 404
        
        # Format the response
        license_list = []
        for license in licenses:
            license_list.append({
                "license": license.license,
                "name": license.name,
                "date": license.date.strftime('%Y-%m-%d')
            })
        
        # Return the license data
        return jsonify({
            "licenses": license_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADD WORK EXPERIECE DATA
@user_application_form.route('/add-jobseeker-student-work-experience', methods=['POST'])
# @auth.login_required
def add_work_experience():
    try:
        # Parse JSON data
        data = request.get_json()
        if not isinstance(data, list):
            data = [data]  # Ensure data is always a list
        
        user_id = 4  # Get the authenticated user's ID (replace with g.user.user_id in production)
        
        for entry in data:
            # Map frontend field names to backend field names
            mapped_entry = {
                "company_name": entry.get("companyName"),
                "company_address": entry.get("companyAddress"),  # Optional
                "position": entry.get("position"),
                "employment_status": entry.get("employmentStatus"),
                "date_start": entry.get("dateStart"),
                "date_end": entry.get("dateEnd")  # Optional
            }
            
            # Check for required fields
            required_fields = ("company_name", "position", "employment_status", "date_start")
            if not all(mapped_entry[field] for field in required_fields):
                return jsonify({
                    "success": False,
                    "error": f"Missing required fields in entry: {entry}"
                }), 400
            
            # Check if user exists
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if work experience already exists for the user
            existing_experience = WorkExperience.query.filter_by(
                user_id=user_id,
                company_name=mapped_entry['company_name'],
                position=mapped_entry['position']
            ).first()
            
            if existing_experience:
                # Update existing work experience
                existing_experience.company_address = mapped_entry['company_address']
                existing_experience.employment_status = mapped_entry['employment_status']
                existing_experience.date_start = mapped_entry['date_start']
                existing_experience.date_end = mapped_entry['date_end']
                message = f"Work experience updated successfully"
            else:
                # Create new work experience entry
                new_experience = WorkExperience(
                    user_id=user_id,
                    company_name=mapped_entry['company_name'],
                    company_address=mapped_entry['company_address'],
                    position=mapped_entry['position'],
                    employment_status=mapped_entry['employment_status'],
                    date_start=mapped_entry['date_start'],
                    date_end=mapped_entry['date_end']
                )
                db.session.add(new_experience)
                message = f"Work experience added successfully"
        
        # Commit changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": message
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GET WORK EXPERIENCE DATA
@user_application_form.route('/get-jobseeker-student-work-experience', methods=['GET'])
@auth.login_required
def get_work_experience():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all work experiences for the user
        work_experiences = WorkExperience.query.filter_by(user_id=g.user.user_id).all()
        if not work_experiences:
            return jsonify({"error": "Work experience not found"}), 404
        
        # Format the response
        experience_list = []
        for experience in work_experiences:
            experience_list.append({
                "company_name": experience.company_name,
                "company_address": experience.company_address,
                "position": experience.position,
                "employment_status": experience.employment_status,
                "date_start": experience.date_start.strftime('%Y-%m-%d'),
                "date_end": experience.date_end.strftime('%Y-%m-%d') if experience.date_end else None
            })
        
        # Return the work experiences
        return jsonify({
            "work_experiences": experience_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ADD OTHER SKILLS DATA
@user_application_form.route('/add-jobseeker-student-other-skills', methods=['POST'])
# @auth.login_required
def add_other_skills():
    try:
        # Parse JSON data
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({
                "success": False,
                "error": "Invalid input format. Expected a list of skills."
            }), 400
        
        user_id = 4  # Replace with g.user.user_id in production
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        for skill_name in data:
            # Check if the skill already exists for the user
            existing_skill = OtherSkills.query.filter_by(
                user_id=user_id, 
                skills=skill_name
            ).first()
            
            if existing_skill:
                # Update existing skill (if needed, though skills are usually static)
                existing_skill.skills = skill_name
            else:
                # Create new skill entry
                new_skill = OtherSkills(
                    user_id=user_id,
                    skills=skill_name
                )
                db.session.add(new_skill)
        
        # Commit changes to the database
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Skills processed successfully"
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# GETTING THE OTHER SKILLS DATA
@user_application_form.route('/get-jobseeker-student-other-skills', methods=['GET'])
@auth.login_required
def get_other_skills():
    try:
        # Check if user exists
        user = User.query.get(g.user.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Retrieve all skills for the user
        skills = OtherSkills.query.filter_by(user_id=g.user.user_id).all()
        if not skills:
            return jsonify({"error": "No skills found for this user"}), 404
        
        # Format the response
        skills_list = [{"skills": skill.skills} for skill in skills]
        
        # Return the skills
        return jsonify({
            "skills": skills_list
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_user_data(model, user_id):
    """Fetch all records of a specific model for a user."""
    return model.query.filter_by(user_id=user_id).all()

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
            "personal_information": [pi.to_dict() for pi in personal_info],
            "job_preference": [jp.to_dict() for jp in job_preference],
            "language_proficiency": [lp.to_dict() for lp in language_proficiency],
            "educational_background": [eb.to_dict() for eb in educational_background],
            "other_training": [ot.to_dict() for ot in other_training],
            "professional_license": [pl.to_dict() for pl in professional_license],
            "work_experience": [we.to_dict() for we in work_experience],
            "other_skills": [os.to_dict() for os in other_skills]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500