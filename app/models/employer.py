from datetime import datetime
from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel


class EmployerJobPosting(BaseModel):
    __tablename__ = 'employer_job_postings'

    id = db.Column(db.Integer, primary_key=True)
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

    user = relationship('User', back_populates='employer_job_postings')