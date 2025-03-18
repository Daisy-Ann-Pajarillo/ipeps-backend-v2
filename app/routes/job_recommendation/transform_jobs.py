# transform_jobs.py - Enhanced for novelty-based recommendation system
import json
import re
from datetime import datetime

def transform_job_postings(input_json):
    # Initialize the output dictionary
    transformed_jobs = {}
    
    # Process each job posting
    for job in input_json.get('job_postings', []):
        job_title = job.get('job_title', 'Unknown Position')
        
        # Create a structured job description with clear sections
        description_parts = {}
        
        # Add JOB_TITLE section (for position-based weighting)
        description_parts['job_title'] = job_title
        
        # Add the base job description
        if job.get('job_description'):
            description_parts['description'] = job.get('job_description')
        
        # Add position details
        position_details = []
        position_details.append(f"Position: {job_title}")
        
        if job.get('job_type'):
            position_details.append(f"Type: {job.get('job_type')}")
        
        if job.get('experience_level'):
            position_details.append(f"Experience Level: {job.get('experience_level')}")
        
        if job.get('estimated_salary_from') and job.get('estimated_salary_to'):
            position_details.append(f"Salary Range: ${job.get('estimated_salary_from')} - ${job.get('estimated_salary_to')}")
        
        if job.get('no_of_vacancies'):
            position_details.append(f"Vacancies: {job.get('no_of_vacancies')}")
        
        # Add position details to a dedicated section
        description_parts['position_details'] = "\n".join(position_details)
        
        # Add location as a separate section
        location_parts = []
        if job.get('city_municipality'):
            location_parts.append(job.get('city_municipality'))
        if job.get('country'):
            location_parts.append(job.get('country'))
        
        if location_parts:
            description_parts['location'] = f"Location: {', '.join(location_parts)}"
        
        # Extract and structure requirements as a dedicated section
        requirements = []
        
        if job.get('certificate_received'):
            requirements.append(f"- Certificate/Degree: {job.get('certificate_received')}")
        
        if job.get('course_name'):
            requirements.append(f"- Degree/Qualification in {job.get('course_name')}")
        
        if job.get('training_institution'):
            requirements.append(f"- Education from institutions like {job.get('training_institution')}")
        
        # Create a dedicated SKILLS section for better matching
        skills_section = []
        if job.get('other_skills'):
            skills = job.get('other_skills').split(',')
            for skill in skills:
                skill = skill.strip()
                if skill:
                    skills_section.append(f"- {skill}")
        
        # Add requirements to a dedicated section
        if requirements:
            description_parts['requirements'] = "REQUIREMENTS:\n" + "\n".join(requirements)
        
        # Add skills to a dedicated section
        if skills_section:
            description_parts['skills'] = "SKILLS:\n" + "\n".join(skills_section)
        
        # Extract posting date for recency calculations
        created_date = job.get('created_at', '')
        if created_date:
            try:
                date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                description_parts['posting_date'] = f"Posted: {date_obj.strftime('%Y-%m-%d')}"
            except (ValueError, TypeError):
                # If date parsing fails, just use the string as-is
                description_parts['posting_date'] = f"Posted: {created_date[:10]}"
        
        # Add company information if available
        if job.get('company_name'):
            description_parts['company'] = f"Company: {job.get('company_name')}"
        
        # Build the final structured description
        full_description = ""
        section_order = ['job_title', 'description', 'position_details', 'skills', 
                         'requirements', 'location', 'company', 'posting_date']
        
        for section in section_order:
            if section in description_parts:
                # Add section header for better parsing in the matcher
                if section != 'job_title':  # Don't add a header for the title
                    full_description += f"\n\n[SECTION:{section.upper()}]\n"
                full_description += description_parts[section]
        
        # Add to the transformed jobs dictionary
        # If there are duplicate job titles, make them unique by appending creation timestamp
        if job_title in transformed_jobs:
            unique_id = job.get('created_at', '')[:10]  # Get date part of timestamp
            job_title = f"{job_title} ({unique_id})"
        
        transformed_jobs[job_title] = full_description.strip()
    
    return transformed_jobs

# Helper function to extract sections from transformed job descriptions
def extract_job_sections(job_description):
    """Extract structured sections from a job description for section-based analysis"""
    sections = {}
    
    # Extract sections using regex pattern matching
    section_pattern = r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)'
    matches = re.findall(section_pattern, job_description, re.DOTALL)
    
    # Process each found section
    for section_name, content in matches:
        sections[section_name.lower()] = content.strip()
    
    # Extract the job title (which appears before any section markers)
    title_match = re.match(r'^(.*?)(?=\[SECTION:|$)', job_description, re.DOTALL)
    if title_match:
        sections['job_title'] = title_match.group(1).strip()
    
    return sections

    # Sample input JSON    
input_json = {
    "job_postings": [
        {
            "certificate_received": "Bachelor's Degree",
            "city_municipality": "San Francisco",
            "country": "USA",
            "course_name": "Computer Science",
            "created_at": "2025-02-24T03:40:39.645031",
            "estimated_salary_from": 70000.0,
            "estimated_salary_to": 90000.0,
            "experience_level": "Mid-level",
            "job_description": "Develop scalable web applications.",
            "job_title": "Software Engineer",
            "job_type": "Full-time",
            "no_of_vacancies": 2,
            "other_skills": "Python, Flask, SQL",
            "status": "pending",
            "training_institution": "University of California",
            "updated_at": "2025-02-24T03:40:39.645031"
        }
    ],
    "success": True
}
    
# Transform the job postings
transformed_jobs = transform_job_postings(input_json)
