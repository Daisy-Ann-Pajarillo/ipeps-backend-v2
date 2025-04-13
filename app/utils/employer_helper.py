from app import db
from app.models import User, EmployerJobPosting, EmployerTrainingPosting, EmployerScholarshipPosting, EmployerPersonalInformation
from datetime import datetime
from flask import jsonify
import json


# Helper function to update expired job postings
def update_expired_job_postings():
    """
    Update status of job postings that have passed their expiration date.
    """
    try:
        # Find all active job postings that have expired
        current_time = datetime.utcnow()
        expired_jobs = EmployerJobPosting.query.filter(
            EmployerJobPosting.expiration_date < current_time,
            EmployerJobPosting.status != 'expired'
        ).all()
        
        # Update their status to 'expired'
        for job in expired_jobs:
            job.status = 'expired'
        
        # Commit changes if any jobs were updated
        if expired_jobs:
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        print(f"Error updating expired job postings: {str(e)}")

# Helper function to update expired training postings
def update_expired_training_postings():
    """
    Update status of training postings that have passed their expiration date.
    """
    try:
        # Find all active training postings that have expired
        current_time = datetime.utcnow()
        expired_trainings = EmployerTrainingPosting.query.filter(
            EmployerTrainingPosting.expiration_date < current_time,
            EmployerTrainingPosting.status != 'expired'
        ).all()
        
        # Update their status to 'expired'
        for training in expired_trainings:
            training.status = 'expired'
        
        # Commit changes if any trainings were updated
        if expired_trainings:
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        print(f"Error updating expired training postings: {str(e)}")

# Helper function to update expired scholarship postings
def update_expired_scholarship_postings():
    """
    Update status of scholarship postings that have passed their expiration date.
    """
    try:
        # Find all active scholarship postings that have expired
        current_time = datetime.utcnow()
        expired_scholarships = EmployerScholarshipPosting.query.filter(
            EmployerScholarshipPosting.expiration_date < current_time,
            EmployerScholarshipPosting.status != 'expired'
        ).all()
        
        # Update their status to 'expired'
        for scholarship in expired_scholarships:
            scholarship.status = 'expired'
        
        # Commit changes if any scholarships were updated
        if expired_scholarships:
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        print(f"Error updating expired scholarship postings: {str(e)}")

def get_employer_all_jobpostings():
    try:
        # Update expired job postings first
        update_expired_job_postings()
        
        # Query all job postings that are not expired (status is not 'expired')
        job_postings = (EmployerJobPosting.query
                        .filter(EmployerJobPosting.status != 'expired')
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
            
            result.append(job_data)
            
        return json.dumps({
            "job_postings": result
        })
        
    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

def get_employer_all_trainingpostings():
    try:
        # Update expired training postings first
        update_expired_training_postings()
        
        # Query all training postings that are not expired (status is not 'expired')
        training_postings = (EmployerTrainingPosting.query
                            .filter(EmployerTrainingPosting.status != 'expired')
                            .all())
        
        if not training_postings:
            return {"message": "No active training postings found"}, 404  # Return dictionary
        
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
            
            result.append(training_data)
        
        return {"training_postings": result}, 200  # Return dictionary
        
    except Exception as e:
        # Handle unexpected errors
        return {"error": str(e)}, 500  # Return dictionary

def get_employer_all_scholarshippostings():
    try:
        # Update expired scholarship postings first
        update_expired_scholarship_postings()
        
        # Query all scholarship postings that are not expired (status is not 'expired')
        scholarship_postings = (EmployerScholarshipPosting.query
                                .filter(EmployerScholarshipPosting.status != 'expired')
                                .all())
        
        if not scholarship_postings:
            return {"message": "No active scholarship postings found"}, 404  # Return dictionary
        
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
            
            # Create a dictionary with scholarship posting and employer details based on actual model fields
            scholarship_data = {
                "scholarship_id": scholarship.employer_scholarshippost_id,
                "scholarship_title": scholarship.scholarship_title,
                "scholarship_description": scholarship.scholarship_description,
                "slots": scholarship.slots,
                "occupied_slots": scholarship.occupied_slots,
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
            result.append(scholarship_data)
        
        return {"scholarship_postings": result}, 200  # Return dictionary
    
    except Exception as e:
        # Handle unexpected errors
        return {"error": str(e)}, 500  # Return dictionary