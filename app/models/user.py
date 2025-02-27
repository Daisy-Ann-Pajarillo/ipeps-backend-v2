from datetime import datetime
from sqlalchemy.orm import relationship
from app import db
import bcrypt
from flask_jwt_extended import create_access_token, decode_token
from app.models import BaseModel

# User table
class User(BaseModel):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.Text, nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    access_level = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships of jobseeker and student table
    jobseeker_student_personal_information = relationship('PersonalInformation', uselist=False, back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_job_preference = relationship('JobPreference', uselist=False, back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_language_proficiency = db.relationship('LanguageProficiency', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_educational_background = db.relationship('EducationalBackground', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_other_training = db.relationship('OtherTraining', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_professional_license = db.relationship('ProfessionalLicense', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_work_experience = db.relationship('WorkExperience', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_other_skills = db.relationship('OtherSkills', back_populates='user', cascade="all, delete-orphan")
    # Relationships of academe
    academe_personal_information = db.relationship('AcademePersonalInformation', back_populates='user', cascade="all, delete-orphan")
    # Relationships of employer
    employer_personal_information = db.relationship('EmployerPersonalInformation', back_populates='user', cascade="all, delete-orphan")
    employer_job_postings = db.relationship('EmployerJobPosting', back_populates='user', cascade="all, delete-orphan")
    employer_training_postings = db.relationship('EmployerTrainingPosting', back_populates='user', cascade="all, delete-orphan")
    employer_scholarship_postings = db.relationship('EmployerScholarshipPosting', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_saved_jobs = db.relationship('StudentJobseekerSavedJobs', back_populates='user', cascade="all, delete-orphan")
    # Relationships of jobseeker and student
    jobseeker_student_saved_trainings = db.relationship('StudentJobseekerSavedTrainings', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_apply_jobs = db.relationship('StudentJobseekerApplyJobs', back_populates='user', cascade="all, delete-orphan")
    jobseeker_student_saved_scholarships = db.relationship('StudentJobseekerSavedScholarships', back_populates='user', cascade="all, delete-orphan")

    def verify_password(self, password):
        """Verify if the provided password matches the stored hashed password."""
        print("self password: ",self.password)
        print("password: ", password)
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt and return the hashed password as a string."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        """
        Verify a JWT token and return the corresponding user_id.
        If the token is invalid or expired, return None.
        """
        try:
            decoded_token = decode_token(token)
            user_id = decoded_token.get("sub")
            user_type = decoded_token.get("user_type")

            print("user_type:", user_type)
            print("user_id:", user_id)

            return User.query.get(user_id) if user_id else None
        except Exception:
            return None

    def generate_auth_token(self, expires_delta=None):
        """
        Generate a JWT token for the user.
        The token contains the user's ID as the subject (`sub`).
        """
        additional_claims = {"user_type": self.user_type}
        return create_access_token(
            identity=str(self.user_id), 
            expires_delta=expires_delta, 
            additional_claims=additional_claims
            )