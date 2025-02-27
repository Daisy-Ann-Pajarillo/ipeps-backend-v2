from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

class StudentJobseekerSavedJobs(BaseModel):
    __tablename__ = 'jobseeker_student_saved_jobs'

    saved_job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_jobpost_id = db.Column(db.Integer, db.ForeignKey('employer_job_postings.employer_jobpost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'hired', name='status_enum_jobs'), nullable=False, default='pending')

    user = relationship('User', back_populates='jobseeker_student_saved_jobs')
    user_saved_job = relationship('EmployerJobPosting', back_populates='saved_jobs')

class StudentJobseekerSavedTrainings(BaseModel):
    __tablename__ = 'jobseeker_student_saved_trainings'

    saved_training_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_trainingpost_id = db.Column(db.Integer, db.ForeignKey('employer_training_postings.employer_trainingpost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'trained', name='status_enum_training'), nullable=False, default='pending')

    user = relationship('User', back_populates='jobseeker_student_saved_trainings')
    user_saved_training = relationship('EmployerTrainingPosting', back_populates='saved_trainings')

class StudentJobseekerSavedScholarships(BaseModel):
    __tablename__ = 'jobseeker_student_saved_scholarships'

    saved_scholarship_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_trainingpost_id = db.Column(db.Integer, db.ForeignKey('employer_training_postings.employer_trainingpost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'trained', name='status_enum_scholarship'), nullable=False, default='pending')

    user = relationship('User', back_populates='jobseeker_student_saved_scholarships')
# -----

# Later for Scholarship Training

# -----

class StudentJobseekerApplyJobs(BaseModel):
    __tablename__ = 'jobseeker_student_apply_jobs'

    apply_job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_jobpost_id = db.Column(db.Integer, db.ForeignKey('employer_job_postings.employer_jobpost_id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'approved', 'declined', 'applied', name='status_enum_apply'), 
        nullable=False, default='pending'
        )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = relationship('User', back_populates='jobseeker_student_apply_jobs')
    user_apply_job = relationship('EmployerJobPosting', back_populates='apply_jobs')