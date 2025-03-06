from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

# jobseeker_student_personal_information table
class PersonalInformation(BaseModel):
    __tablename__ = 'jobseeker_student_personal_information'

    personal_info_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    prefix = db.Column(db.String(50), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(10), nullable=True)
    sex = db.Column(db.String(10), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    place_of_birth = db.Column(db.String(100), nullable=False)
    civil_status = db.Column(db.String(20), nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    religion = db.Column(db.String(255), nullable=False)
    temporary_country = db.Column(db.String(100), nullable=False)
    temporary_province = db.Column(db.String(100), nullable=True)
    temporary_municipality = db.Column(db.String(100), nullable=True)
    temporary_zip_code = db.Column(db.String(10), nullable=True)
    temporary_barangay = db.Column(db.String(100), nullable=True)
    temporary_house_no_street_village = db.Column(db.String(255), nullable=True)
    permanent_country = db.Column(db.String(100), nullable=True)
    permanent_province = db.Column(db.String(100), nullable=True)
    permanent_municipality = db.Column(db.String(100), nullable=True)
    permanent_zip_code = db.Column(db.String(10), nullable=True)
    permanent_barangay = db.Column(db.String(100), nullable=True)
    permanent_house_no_street_village = db.Column(db.String(255), nullable=True)
    cellphone_number = db.Column(db.String(20), nullable=False) 
    landline_number = db.Column(db.String(20), nullable=True) 
    tin = db.Column(db.String(20), nullable=True)
    sss_gsis_number = db.Column(db.String(20), nullable=True)
    pag_ibig_number = db.Column(db.String(20), nullable=True)
    phil_health_no = db.Column(db.String(20), nullable=True)
    disability = db.Column(db.String(100), nullable=True)
    employment_status = db.Column(db.String(50), nullable=False)
    is_looking_for_work = db.Column(db.Boolean, nullable=False, default=False)
    since_when_looking_for_work = db.Column(db.Date, nullable=True)
    is_willing_to_work_immediately = db.Column(db.Boolean, nullable=False, default=False)
    is_ofw = db.Column(db.Boolean, nullable=False, default=False)
    ofw_country = db.Column(db.String(100), nullable=True)
    is_former_ofw = db.Column(db.Boolean, nullable=False, default=False)
    former_ofw_country = db.Column(db.String(100), nullable=True)
    former_ofw_country_date_return = db.Column(db.Date, nullable=True)
    is_4ps_beneficiary = db.Column(db.Boolean, nullable=False, default=False)
    _4ps_household_id_no = db.Column(db.String(50), nullable=True)
    valid_id_url = db.Column(db.String(255), nullable=True)
    # Relationship
    user = relationship('User', back_populates='jobseeker_student_personal_information')


# jobseeker_student_job_preference table
class JobPreference(BaseModel):
    __tablename__ = 'jobseeker_student_job_preference'

    job_preference_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    province = db.Column(db.String(100), nullable=False)
    municipality = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    preferred_occupation = db.Column(db.String(100), nullable=False)
    salary_from = db.Column(db.Float, nullable=False)
    salary_to = db.Column(db.Float, nullable=False)

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_job_preference')


# jobseeker_student_language_proficiency table
class LanguageProficiency(BaseModel):
    __tablename__ = 'jobseeker_student_language_proficiency'

    language_proficiency_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    can_read = db.Column(db.Boolean, nullable=False, default=False)
    can_write = db.Column(db.Boolean, nullable=False, default=False)
    can_speak = db.Column(db.Boolean, nullable=False, default=False)
    can_understand = db.Column(db.Boolean, nullable=False, default=False)

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_language_proficiency')

# jobseeker_student_educational_background table
class EducationalBackground(BaseModel):
    __tablename__ = 'jobseeker_student_educational_background'

    educational_background_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    school_name = db.Column(db.String(255), nullable=False)
    date_from = db.Column(db.Date, nullable=False)
    date_to = db.Column(db.Date, nullable=True)  # Nullable for ongoing studies
    degree_or_qualification = db.Column(db.String(255), nullable=False)
    field_of_study = db.Column(db.String(255), nullable=False)
    program_duration = db.Column(db.Integer, nullable=False)  # In years

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_educational_background')

# jobseeker_student_other_training table
class OtherTraining(BaseModel):
    __tablename__ = 'jobseeker_student_other_training'

    other_training_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)  # Nullable for ongoing training
    training_institution = db.Column(db.String(255), nullable=False)
    certificates_received = db.Column(db.String(255), nullable=True)
    hours_of_training = db.Column(db.Integer, nullable=False)
    skills_acquired = db.Column(db.Text, nullable=True)
    credential_id = db.Column(db.String(255), nullable=True)
    credential_url = db.Column(db.String(500), nullable=True)

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_other_training')

# jobseeker_student_professional_license table
class ProfessionalLicense(BaseModel):
    __tablename__ = 'jobseeker_student_professional_license'

    professional_license_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    license = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=True)
    rating = db.Column(db.Integer, nullable=True)

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_professional_license')

# jobseeker_student_work_experience table
class WorkExperience(BaseModel):
    __tablename__ = 'jobseeker_student_work_experience'

    work_experience_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    company_address = db.Column(db.String(500), nullable=True)
    position = db.Column(db.String(255), nullable=False)
    employment_status = db.Column(db.String(50), nullable=False)  # e.g., Full-time, Part-time, Contract
    date_start = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=True)  # Nullable for ongoing employment

    # Relationship
    user = relationship('User', back_populates='jobseeker_student_work_experience')

# jobseeker_student_other_skills table
class OtherSkills(BaseModel):
    __tablename__ = 'jobseeker_student_other_skills'

    other_skills_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    skills = db.Column(db.String(255), nullable=False)

    user = relationship('User', back_populates='jobseeker_student_other_skills')

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# this is for academe personal information
class AcademePersonalInformation(BaseModel):
    __tablename__ = "academe_personal_information"

    academe_personal_info_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    prefix = db.Column(db.String(10), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(10), nullable=True)
    institution_name = db.Column(db.String(255), nullable=False)
    institution_type = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    employer_position = db.Column(db.String(100), nullable=False)
    employer_id_number = db.Column(db.String(100), nullable=False)
    temporary_country = db.Column(db.String(100), nullable=True)
    temporary_province = db.Column(db.String(100), nullable=True)
    temporary_municipality = db.Column(db.String(100), nullable=True)
    temporary_zip_code = db.Column(db.String(10), nullable=True)
    temporary_barangay = db.Column(db.String(100), nullable=True)
    temporary_house_no_street_village = db.Column(db.String(255), nullable=True)
    permanent_country = db.Column(db.String(100), nullable=True)
    permanent_province = db.Column(db.String(100), nullable=True)
    permanent_municipality = db.Column(db.String(100), nullable=True)
    permanent_zip_code = db.Column(db.String(10), nullable=True)
    permanent_barangay = db.Column(db.String(100), nullable=True)
    permanent_house_no_street_village = db.Column(db.String(255), nullable=True)
    cellphone_number = db.Column(db.String(20), nullable=False) 
    landline_number = db.Column(db.String(20), nullable=True) 
    valid_id_url = db.Column(db.String(255), nullable=True)

    user = relationship('User', back_populates='academe_personal_information')

# ---------------------------------------------------------------------------------------------------------------------------------------------------------
# this is for employer personal information
class EmployerPersonalInformation(BaseModel):
    __tablename__ = "employer_personal_information"

    employer_personal_info_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    prefix = db.Column(db.String(10), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    suffix = db.Column(db.String(10), nullable=True)
    company_name = db.Column(db.String(255), nullable=False)
    company_type = db.Column(db.String(50), nullable=False)
    company_classification = db.Column(db.String(50), nullable=False)
    company_industry = db.Column(db.String(50), nullable=False)
    company_workforce = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    employer_position = db.Column(db.String(100), nullable=False)
    employer_id_number = db.Column(db.String(100), nullable=False)
    temporary_country = db.Column(db.String(100), nullable=True)
    temporary_province = db.Column(db.String(100), nullable=True)
    temporary_municipality = db.Column(db.String(100), nullable=True)
    temporary_zip_code = db.Column(db.String(10), nullable=True)
    temporary_barangay = db.Column(db.String(100), nullable=True)
    temporary_house_no_street_village = db.Column(db.String(255), nullable=True)
    permanent_country = db.Column(db.String(100), nullable=True)
    permanent_province = db.Column(db.String(100), nullable=True)
    permanent_municipality = db.Column(db.String(100), nullable=True)
    permanent_zip_code = db.Column(db.String(10), nullable=True)
    permanent_barangay = db.Column(db.String(100), nullable=True)
    permanent_house_no_street_village = db.Column(db.String(255), nullable=True)
    cellphone_number = db.Column(db.String(20), nullable=False) 
    landline_number = db.Column(db.String(20), nullable=True) 
    valid_id_url = db.Column(db.String(255), nullable=True)

    user = relationship('User', back_populates='employer_personal_information')
