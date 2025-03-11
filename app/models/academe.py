from datetime import datetime
from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

class AcademeGraduateReport(BaseModel):
    __tablename__ = 'academe_graduate_reports'

    graduate_report_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    degree_or_qualification = db.Column(db.String(100), nullable=False)
    education_level = db.Column(db.String(50), nullable=False)
    field_of_study = db.Column(db.String(100), nullable=False)
    major = db.Column(db.String(100), nullable=True) 
    year = db.Column(db.Integer, nullable=False)
    number_of_enrollees = db.Column(db.Integer, nullable=False)
    number_of_graduates = db.Column(db.Integer, nullable=False)
    start_year = db.Column(db.Integer, nullable=False)
    end_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship('User', back_populates='academe_graduate_reports')

class AcademeEnrollmentReport(BaseModel):
    __tablename__ = 'academe_enrollment_reports'

    enrollment_report_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    degree_or_qualification = db.Column(db.String(100), nullable=False)
    education_level = db.Column(db.String(50), nullable=False)
    field_of_study = db.Column(db.String(100), nullable=False)
    major = db.Column(db.String(100), nullable=True)
    number_of_enrollees = db.Column(db.Integer, nullable=False)
    start_year = db.Column(db.Integer, nullable=False)
    end_year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship('User', back_populates='academe_enrollment_reports')