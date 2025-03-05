from app import db
from app.models import EmployerJobPosting, EmployerTrainingPosting
from datetime import datetime

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
