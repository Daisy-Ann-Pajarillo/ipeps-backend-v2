from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

# =======================v=============== MODEL FOR SAVING THE JOBS, TRAININGS, SCHOLARSHIPS ===================v=============================== #
class StudentJobseekerSavedJobs(BaseModel):
    __tablename__ = 'jobseeker_student_saved_jobs'

    saved_job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_jobpost_id = db.Column(db.Integer, db.ForeignKey('employer_job_postings.employer_jobpost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'hired', name='status_enum_saved_jobs'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = relationship('User', back_populates='jobseeker_student_saved_jobs')
    user_saved_job = relationship('EmployerJobPosting', back_populates='saved_jobs')

class StudentJobseekerSavedTrainings(BaseModel):
    __tablename__ = 'jobseeker_student_saved_trainings'

    saved_training_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_trainingpost_id = db.Column(db.Integer, db.ForeignKey('employer_training_postings.employer_trainingpost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'trained', name='status_enum_saved_trainings'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = relationship('User', back_populates='jobseeker_student_saved_trainings')
    user_saved_trainings = relationship('EmployerTrainingPosting', back_populates='saved_trainings')

class StudentJobseekerSavedScholarships(BaseModel):
    __tablename__ = 'jobseeker_student_saved_scholarships'

    saved_scholarship_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_scholarshippost_id = db.Column(db.Integer, db.ForeignKey('employer_scholarship_postings.employer_scholarshippost_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'declined', 'trained', name='status_enum_saved_scholarships'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = relationship('User', back_populates='jobseeker_student_saved_scholarships')
    user_saved_scholarships = relationship('EmployerScholarshipPosting', back_populates='saved_scholarships')
    

# =======================^=============== MODEL FOR SAVING THE JOBS, TRAININGS, SCHOLARSHIPS ===================^=============================== #

# =======================v=============== MODEL FOR APPLYING THE JOBS, TRAININGS, SCHOLARSHIPS ===================v=============================== #
class StudentJobseekerApplyJobs(BaseModel):
    __tablename__ = 'jobseeker_student_apply_jobs'

    apply_job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_jobpost_id = db.Column(db.Integer, db.ForeignKey('employer_job_postings.employer_jobpost_id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'approved', 'declined', 'applied', 'hired', name='status_enum_apply_jobs'), 
        nullable=False, default='pending'
        )
    employer_remarks = db.Column(db.Text, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = relationship('User', back_populates='jobseeker_student_apply_jobs')
    user_apply_job = relationship('EmployerJobPosting', back_populates='apply_jobs')

class StudentJobseekerApplyScholarships(BaseModel):
    __tablename__ = 'jobseeker_student_apply_scholarships'

    apply_scholarship_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_scholarshippost_id = db.Column(db.Integer, db.ForeignKey('employer_scholarship_postings.employer_scholarshippost_id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'approved', 'declined', 'applied', 'hired', name='status_enum_apply_scholarships'), 
        nullable=False, default='pending'
        )
    employer_remarks = db.Column(db.Text, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    user = relationship('User', back_populates='jobseeker_student_apply_scholarships')
    user_apply_scholarships = relationship('EmployerScholarshipPosting', back_populates='apply_scholarships')

class StudentJobseekerApplyTrainings(BaseModel):
    __tablename__ = 'jobseeker_student_apply_trainings'

    apply_training_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    employer_trainingpost_id = db.Column(db.Integer, db.ForeignKey('employer_training_postings.employer_trainingpost_id'), nullable=False)
    status = db.Column(
        db.Enum('pending', 'approved', 'declined', 'applied', 'hired', name='status_enum_apply_trainings'), 
        nullable=False, default='pending'
        )
    employer_remarks = db.Column(db.Text, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = relationship('User', back_populates='jobseeker_student_apply_trainings')
    user_apply_trainings = relationship('EmployerTrainingPosting', back_populates='apply_trainings')
# =======================^=============== MODEL FOR APPLYING THE JOBS, TRAININGS, SCHOLARSHIPS ===================^=============================== #
