<p align="center"> <img src="image.png" alt="Logo" width="400" >
</p>

<h1 align="center">Iloilo Province Employment Portal and Services</h1>

<p align="center"> IPEPS Backend Documentation </p>

## Project Folder Structure

```
/ipeps-backend
├── app/                                       # Core application package
│   ├── models/                                # SQLAlchemy database models
│   │   ├── __init__.py                        # Initializes the models module
│   │   ├── academe.py                         # Models for academe users
│   │   ├── admin.py                           # Models for admin users
│   │   ├── base.py                            # Base model class for shared logic
│   │   ├── employer.py                        # Models for employer users
│   │   ├── student_jobseeker.py               # Models for students and jobseekers
│   │   ├── user_application.py                # Models for user application form
│   │   └── user.py                            # users model
│   ├── routes/                                # Flask route handlers (API endpoints)
│   │   ├── __init__.py                        # Initializes the routes module
│   │   ├── academe.py                         # Routes for academe
│   │   ├── admin.py                           # Admin routes
│   │   ├── employer.py                        # Employer routes
│   │   ├── login_register.py                  # Authentication routes
│   │   ├── student_jobseeker.py               # Student and jobseeker routes
│   │   ├── user_application.py                # user application form routes
│   │   └── recommendations/                   # Recommendation system endpoints
│   │       ├── job_reco_model/                # ML model files for job recommendations
│   │       ├── nltk_data/                     # NLTK data for NLP tasks
│   │       ├── scholarship_reco_model/        # ML model files for scholarship recommendations
│   │       ├── training_reco_model/           # ML model files for training recommendations
│   │       └── recommendation_routes.py       # Routes for handling recommendation requests
│   ├── utils/                                 # Utility/helper functions
│   │   ├── __init__.py                        # Initializes the utils module
│   │   ├── employer_helper.py                 # Helpers for employer operations
│   │   └── user_app_form_helper.py            # Helpers for application form logic
│   ├── __init__.py                            # Application factory and app instance
│   └── config.py                              # Configuration settings
├── .env                                       # environment variables
├── .gitignore                                 # Git ignore rules for the project
├── application.py                             # Entry point for starting the Flask app
├── migrate.bat                                # Windows batch script for DB migration
├── README.md                                  # Project documentation and usage guide
├── requirements.txt                           # Python dependencies
├── runtime.txt                                # Python runtime version for deployment
├── start.bat                                  # Windows script to run the app
├── start.ps1                                  # PowerShell script to run the app
├── start.sh                                   # Unix shell script to run the app
└── wsgi.py                                    # WSGI entry point for production servers
```

---

## Installation

### Requirements

- Python 3.13.1
- PostgreSQL 17.2
- VS Code
- pgAdmin for DB management
- Postman for API testing

### Set up the environment

1. **Clone the repository**

   ```bash
   git clone https://github.com/edge405/ipeps-backend.git
   cd ipeps-backend
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate        # Mac/Linux
   venv/Scripts/activate           # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**

   - Create a `.env` file in the `ipeps-backend/` directory.
   - In **pgAdmin**, create a database named `restfulapiflask`.
   - Set the **DATABASE_URL** in environment variables:
     - **Name:** `DATABASE_URL`
     - **Value:** `postgresql://username:password@localhost/restfulapiflask`

5. **Create Secret Key**

   Go to your system's **environment variables** and create a new variable:

   - **Name:** `SECRET_KEY`
   - **Value:** `!w-j29e#h&**eewo6!!33z_i#c_1%%c_dol55*8%%6(@io!0z+`

     > _You can use the provided value or generate your own secure key._

6. **Run migrations**

   ```bash
    ./migrate.bat
   ```

7. **Start the app**
   ```bash
   ./start.bat      # for Windows
   ./start.sh       # for Mac/Linux
   ```

<!-- ---

## API Reference

Below are the available API endpoints categorized by user roles and functionality. Use Postman to test the endpoints. Make sure you’re authenticated where required.

1. **USER APPLICATION FORM**
   /api/get-user-info - getting user personal info
   /api/check-personal-information-status - CHECK IF THE USER FILLED UP THEIR PERSONAL INFORMATION

   - **JOBSEEKER-STUDENT**
     /api/add-jobseeker-student-personal-information - add personal information
     /api/add-jobseeker-student-job-preference - add job preference
     /api/add-jobseeker-student-language-proficiency - add language proficiency
     /api/add-jobseeker-student-educational-background - add educational background
     /api/add-jobseeker-student-professional-license - add professional license
     /api/add-jobseeker-student-work-experience - add work experience
     /api/add-jobseeker-student-other-skills - add other skills
     /api/add-jobseeker-student-other-training - add other training
     /api/get-jobseeker-student-all-data - getting jobseeker or student all data for review
     /api/get-user-info - getting the user information
   - **ACADEME**
     /api/add-academe-personal-information - adding academe personal information
     /api/get-academe-personal-information - getting academe personal information for review
   - **EMPLOYER**
     /api/add-employer-personal-information - adding employer personal information
     /api/get-employer-personal-information - getting employer personal information for review

2. **REGISTER**

   - **Get Token and Create account**
     /api/token - for login
     /api/create-user - for creating a user

3. **STUDENT JOBSEEKER DASHBOARD**

   - **APPLY**
     - **JOB**
       /api/apply-job - applying job
       /api/get-applied-jobs - getting all applied jobs
       /api/check-already-applied - check if it already applied to the job
     - **SCHOLARSHIP**
       /api/apply-scholarships - applying scholarship
       /api/get-applied-scholarships - getting all applied scholarships
       /api/check-scholarship-status - check if it already applied to the scholarship
     - **TRAINING**
       /api/apply-training - applying training
       /api/get-applied-trainings - getting all applied trainings
       /api/check-training-status - check if it already applied to the training
   - **SAVE**
     - **JOB**
       /api/saved-jobs - saving the jobs
       /api/get-saved-jobs - get all saved jobs
       /api/check-already-saved - checking if it already saved the job
     - **SCHOLARSHIP**
       /api/save-scholarship - saving the scholarships
       /api/get-saved-scholarships - getting all saved scholarships
       /api/check-scholarship-status - checking if it already saved the scholarship
     - **TRAINING**
       /api/save-training - saving the trainings
       /api/get-saved-trainings - get all saved trainings
       /api/check-training-status - checking if it already saved the training

4. **EMPLOYER DASHBOARD**

   - **POSTINGS**
     - **JOB**
       /api/job-postings - add job posting
       /api/get-job-postings - get job posting
       /api/job-posting/<job_posting_id> - update job posting
       /api/job-posting/<job_posting_id> - delete job posting
       /api/all-job-postings - get all job posting of one employer
     - **TRAINING**
       /api/training-posting - add training posting
       /api/get-training-postings - get training posting
       /api/training-posting/<training_posting_id> - update training posting
       /api/training-posting/<training_posting_id> - delete training posting
       /api/all-training-postings - get all training posting of one employer
     - **SCHOLARSHIPS**
       /api/scholarship-posting - add scholarship posting
       /api/get-scholarship-postings - get scholarship posting
       /api/scholarship-posting/<scholarship_posting_id> - ipdate training posting
       /api/scholarship-posting/<scholarship_posting_id> - delete sholarship posting
       /api/all-scholarship-postings - get all scholarship posting of one employer
   - **MANAGE STUDENT JOBSEEKER APPLICATIONS**
     /api/approved-applicants - getting all approved by admin applicants

5. **RECOMMENDATIONS**

   - **JOB**
     /api/recommend/job-posting
   - **TRAINING**
     /api/recommend/training-posting
   - **SCHOLARSHIP**
     /api/recommend/scholarship-posting

6. **ACADEME DASHBOARD**

   - **GRADUATE REPORTS**
     /api/add-graduate-reports - adding graduate reports
     /api/get-graduate-reports - getting all graduate reports
     /api/graduate-reports/<graduate_report_id> - edit graduate reports
     /api/graduate-reports/<graduate_report_id> - delete graduate reports
     /api/graduate-reports/summary - graduate report summary
   - **ENROLLMENT REPORTS**
     /api/add-enrollment-reports - adding enrollment reports
     /api/get-enrollment-reports - getting all enrollment reports
     /api/enrollment-reports/<enrollment_id> - get enrollment report by id
     /api/enrollment-reports/<enrollment_id> - edit enrollment report
     /api/enrollment-reports/<enrollment_id> - delete enrollment report
     /api/enrollment-reports/summary - enrollment report summary

7. **ADMIN DASHBOARD**
   - **MANAGE USERS**
     - **MANAGE EMPLOYER POSTING**
       /api/update-posting-status - approving employer posting
       /api/public/all-postings - getting all employers posting
       /api/update-remarks - add remarks to the employer postings
     - **USER APPLICATION APPROVAL**
       /api/update-job-status - approving user applied jobs
       /api/update-scholarship-status - approving user applied scholarships
       /api/update-training-status - approving user applied trainings
   - **MANAGE STUDENT JOBSEEKER APPLIED**
     - **USERS APPLICATION**
       /api/get-all-users-applied-jobs - getting all user and their applied jobs
       /api/get-all-users-applied-scholarships - getting all user and their applied scholarships
       /api/get-all-users-applied-trainings - getting all user and their applied trainings
     - **GET USERS**
       /api/all-users - getting all the users
       /api/admin/get-user-info/<user_id> - get user information by id
   - **COMPANY DETAILS**
     /api/get-employer-details - getting all employer and their company details -->
