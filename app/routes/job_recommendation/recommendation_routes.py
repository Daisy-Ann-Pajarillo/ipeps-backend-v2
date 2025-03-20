from flask import g, Blueprint, request, jsonify
import json
from app import db
from flask_httpauth import HTTPBasicAuth
from .job_matching import run_job_matching
from app.models import User, PersonalInformation, JobPreference, LanguageProficiency, EducationalBackground, WorkExperience, OtherSkills, ProfessionalLicense, OtherTraining
from app.utils import get_user_data, exclude_fields, convert_dates, get_employer_all_jobpostings

auth = HTTPBasicAuth()

recommendation = Blueprint("recommendation", __name__)

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

@recommendation.route('/recommend/job-posting', methods=['GET'])
@auth.login_required
def recommend_job_posting():

    uid = g.user.user_id

    if uid is None:
        return jsonify({"error": "Missing user_id"}), 400
    
    # Query the database for the user
    user = User.query.filter_by(user_id=uid).first()

    if user is None:
        return jsonify({"error": "User not found"}), 404

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
        user_profile = json.dumps({
            "personal_information": convert_dates(personal_information),
            "job_preference": convert_dates(job_preference),
            "language_proficiency": convert_dates(language_proficiency),
            "educational_background": convert_dates(educational_background),
            "other_training": convert_dates(other_training),
            "professional_license": convert_dates(professional_license),
            "work_experience": convert_dates(work_experience),
            "other_skills": convert_dates(other_skills)
        })

        return run_job_matching(user_profile, get_employer_all_jobpostings(), top_n=5, return_json=True)
    
# @recommendation.route('/recommend/training-posting', methods=['GET'])
# @auth.login_required
# def recommend_training_posting():
#     uid = g.user.user_id

#     if uid is None:
#         return jsonify({"error": "Missing user_id"}), 400
    
#     # Query the database for the user
#     user = User.query.filter_by(user_id=uid).first()

#     if user is None:
#         return jsonify({"error": "User not found"}), 404

#     def fetch_data(model):
#         return exclude_fields(get_user_data(model, uid) or [])
    
#     if user.user_type in ["STUDENT", "JOBSEEKER"]:
#         personal_information = fetch_data(PersonalInformation)
#         job_preference = fetch_data(JobPreference)
#         language_proficiency = fetch_data(LanguageProficiency)
#         educational_background = fetch_data(EducationalBackground)
#         other_training = fetch_data(OtherTraining)
#         professional_license = fetch_data(ProfessionalLicense)
#         work_experience = fetch_data(WorkExperience)
#         other_skills = fetch_data(OtherSkills)
#             # Transform disability format
#         for item in personal_information:
#             disability_str = item.get("disability", "")
#             if disability_str:
#                 disabilities = [d.strip() for d in disability_str.split(",")]
#                 item["disability"] = {
#                     "visual": "visual" in disabilities,
#                     "hearing": "hearing" in disabilities,
#                     "speech": "speech" in disabilities,
#                     "physical": "physical" in disabilities,
#                 }
#         user_profile = json.dumps({
#             "personal_information": convert_dates(personal_information),
#             "job_preference": convert_dates(job_preference),
#             "language_proficiency": convert_dates(language_proficiency),
#             "educational_background": convert_dates(educational_background),
#             "other_training": convert_dates(other_training),
#             "professional_license": convert_dates(professional_license),
#             "work_experience": convert_dates(work_experience),
#             "other_skills": convert_dates(other_skills)
#         })