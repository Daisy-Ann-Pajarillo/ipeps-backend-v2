from datetime import datetime
from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

class EmployerJobPosting(BaseModel):
    __tablename__ = 'employer_job_postings'

    employer_jobpost_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    job_title = db.Column(db.String(255), nullable=False)
    job_type = db.Column(db.String(100), nullable=False)
    experience_level = db.Column(db.String(100))
    job_description = db.Column(db.Text, nullable=False)
    estimated_salary_from = db.Column(db.Float)
    estimated_salary_to = db.Column(db.Float)
    no_of_vacancies = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    city_municipality = db.Column(db.String(100), nullable=False)
    other_skills = db.Column(db.Text)
    course_name = db.Column(db.String(255))
    training_institution = db.Column(db.String(255))
    certificate_received = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending')
    remarks = db.Column(db.Text, nullable=True)
    expiration_date = db.Column(db.DateTime)

    user = relationship('User', back_populates='employer_job_postings')
    saved_jobs = db.relationship('StudentJobseekerSavedJobs', back_populates='user_saved_job', cascade="all, delete-orphan")
    apply_jobs = db.relationship('StudentJobseekerApplyJobs', back_populates='user_apply_job', cascade="all, delete-orphan")

class EmployerTrainingPosting(BaseModel):
    __tablename__ = 'employer_training_postings'

    employer_trainingpost_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    training_title = db.Column(db.String(255), nullable=False)
    training_description = db.Column(db.Text, nullable=False)
    slots = db.Column(db.Integer, nullable=False, default=10)
    occupied_slots = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    expiration_date = db.Column(db.DateTime)

    user = relationship('User', back_populates='employer_training_postings')
    saved_trainings = db.relationship('StudentJobseekerSavedTrainings', back_populates='user_saved_trainings', cascade="all, delete-orphan")
    apply_trainings = db.relationship('StudentJobseekerApplyTrainings', back_populates='user_apply_trainings', cascade="all, delete-orphan")

class EmployerScholarshipPosting(BaseModel):
    __tablename__ = "employer_scholarship_postings"

    employer_scholarshippost_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    scholarship_title  = db.Column(db.String(255), nullable=False)
    scholarship_description = db.Column(db.Text, nullable=False)
    slots = db.Column(db.Integer, nullable=False, default=10)
    occupied_slots = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='pending')
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    expiration_date = db.Column(db.DateTime)

    user = relationship('User', back_populates='employer_scholarship_postings')
    saved_scholarships = db.relationship('StudentJobseekerSavedScholarships', back_populates='user_saved_scholarships', cascade="all, delete-orphan")
    apply_scholarships = db.relationship('StudentJobseekerApplyScholarships', back_populates='user_apply_scholarships', cascade="all, delete-orphan")

class EmployerCompanyInformation(BaseModel):
    __tablename__ = 'employer_company_information'

    employer_companyinfo_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=False)
    company_email = db.Column(db.String(100), nullable=False)
    company_website = db.Column(db.String(100))
    company_industry = db.Column(db.String(100), nullable=False)
    company_type = db.Column(db.String(100), nullable=False)
    company_total_workforce = db.Column(db.String(100), nullable=False)
    company_country = db.Column(db.String(100), nullable=False)
    company_address = db.Column(db.String(255), nullable=False)
    company_house_no_street = db.Column(db.String(255), nullable=False)
    company_postal_code = db.Column(db.String(20), nullable=False)
    logo_image_path = db.Column(db.String(255))
    business_permit_path = db.Column(db.String(255))
    bir_form_path = db.Column(db.String(255))
    poea_file_path = db.Column(db.String(255))
    philhealth_file_path = db.Column(db.String(255))
    dole_certificate_path = db.Column(db.String(255))
    admin_remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = relationship('User', back_populates='employer_company_information')