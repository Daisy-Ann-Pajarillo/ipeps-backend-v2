from .base import BaseModel
from .user_application import  PersonalInformation, JobPreference, LanguageProficiency, EducationalBackground, WorkExperience, OtherSkills, ProfessionalLicense, OtherTraining, AcademePersonalInformation, EmployerPersonalInformation
from .user import User
from .employer import EmployerJobPosting, EmployerTrainingPosting, EmployerScholarshipPosting
from .student_jobseeker import StudentJobseekerSavedJobs, StudentJobseekerApplyJobs