from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

class StudentJobseekerSavedJobs(BaseModel):
    __tablename__ = 'jobseeker_student_saved_jobs'

    saved_job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_jobpost_id = db.Column(db.Integer, db.ForeignKey('employer_job_postings.employer_jobpost_id'), nullable=False)
    status = db.Column(db.Enum('null', 'pending', 'approved', 'declined', 'hired', name='status_enum'), nullable=False, default='null')

    user = relationship('User', back_populates='jobseeker_student_saved_jobs')
    user_saved_job = relationship('EmployerJobPosting', back_populates='saved_jobs')