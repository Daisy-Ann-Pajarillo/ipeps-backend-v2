# run_job_matching.py - Updated to handle both JSON files and API endpoints
import requests
import json
import os
from .job_matcher import NoveltyEnhancedJobMatcher
from .transform_jobs import transform_job_postings

# Fetch data from API, local JSON file, or directly from a JSON object
def fetch_data(source):
    """
    Fetch data from an API endpoint, a local JSON file, or directly from a JSON object
    
    Args:
        source: Can be one of:
            - URL string starting with 'http' (API endpoint)
            - Path string to a local JSON file
            - Dictionary/JSON object already in memory
        
    Returns:
        dict: The JSON data
    """
    try:
        # If source is already a dictionary, return it directly
        if isinstance(source, dict):
            return source
            
        # If source is a string that looks like JSON, parse it
        if isinstance(source, str):
            if source.startswith('{') and source.endswith('}'):
                try:
                    return json.loads(source)
                except json.JSONDecodeError:
                    # Not valid JSON, continue with other methods
                    pass
                    
            if source.startswith('http'):
                # It's an API endpoint
                response = requests.get(source)
                response.raise_for_status()  # Raise exception for non-200 responses
                return response.json()
            else:
                # It's a local JSON file
                if not os.path.exists(source):
                    raise FileNotFoundError(f"JSON file not found: {source}")
                    
                with open(source, 'r') as file:
                    return json.load(file)
        
        # If we get here, the source is not a recognized format
        raise ValueError(f"Unrecognized data source format: {type(source)}")
    except (requests.exceptions.RequestException, FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        print(f"Error fetching data: {str(e)}")
        raise

# Format recommendations for frontend display
def format_recommendations_for_frontend(recommendations, original_job_postings_json):
    # Create a lookup dictionary for the original job postings
    job_lookup = {}
    for job in original_job_postings_json.get('job_postings', []):
        job_title = job.get('job_title')
        if job_title:
            # If multiple jobs have the same title, we'll just use the latest one
            job_lookup[job_title] = job
    
    # Format the response
    formatted_response = {
        "success": True,
        "recommendations": []
    }
    
    for rec in recommendations:
        job_title = rec['job_title']
        match_score = rec['match_score']
        
        # Extract the base job title if it contains a unique identifier
        base_title = job_title.split(' (')[0] if ' (' in job_title else job_title
        
        # Find the original job posting
        original_job = job_lookup.get(base_title)
        
        if original_job:
            # Create a recommendation object with the match score and original posting
            recommendation = {
                "match_score": round(match_score, 2),
                "job_posting": original_job,
                "novelty_factors": generate_novelty_explanation(rec)  # New feature
            }
            formatted_response["recommendations"].append(recommendation)
    
    return formatted_response

# Generate human-readable explanation of recommendation factors
def generate_novelty_explanation(recommendation):
    """Generate human-readable explanation for why this job was recommended"""
    # This would normally use data from the matcher, but we'll simulate it
    match_score = recommendation['match_score']
    
    # Generate different explanations based on the match score
    if match_score > 85:
        return {
            "primary_factors": [
                "Strong skills match with your profile",
                "Experience directly relevant to this position",
                "Technical skills closely aligned with requirements"
            ],
            "skill_alignment": "Very High",
            "recency_boost": True
        }
    elif match_score > 70:
        return {
            "primary_factors": [
                "Good overall match with your profile",
                "Most key skills present in your background",
                "Your experience partially aligns with requirements"
            ],
            "skill_alignment": "High",
            "recency_boost": False
        }
    else:
        return {
            "primary_factors": [
                "Some matching skills found in your profile",
                "Your background contains related experience",
                "Potential skill development opportunity"
            ],
            "skill_alignment": "Moderate",
            "recency_boost": False
        }

# Main function to run the job matching process
def run_job_matching(profile_source, job_postings_source, top_n=5, return_json=False):
    """
    Run the job matching process using profile and job posting data
    
    Args:
        profile_source: Profile data as one of:
            - API endpoint URL string
            - Path to JSON file string
            - Dictionary/JSON object already in memory
        job_postings_source: Job postings data as one of:
            - API endpoint URL string
            - Path to JSON file string
            - Dictionary/JSON object already in memory
        top_n (int): Number of top recommendations to return
        return_json (bool): Whether to return formatted JSON for frontend
        
    Returns:
        list or dict: List of recommendations or formatted JSON for frontend
    """
    try:
        # Fetch data from API, JSON file, or use directly if already an object
        profile_data = fetch_data(profile_source)
        job_postings_json = fetch_data(job_postings_source)
        
        # Transform job postings to the required format
        transformed_jobs = transform_job_postings(job_postings_json)
        
        # Initialize the novelty-enhanced job matcher
        matcher = NoveltyEnhancedJobMatcher(debug=True)
        
        # Get recommendations
        recommendations = matcher.get_recommendations(profile_data, transformed_jobs, top_n)
        
        # Return the appropriate format
        if return_json:
            return format_recommendations_for_frontend(recommendations, job_postings_json)
        else:
            return recommendations
    except Exception as e:
        print(f"Error in job matching process: {str(e)}")
        # Return an error response if something went wrong
        if return_json:
            return {
                "success": False,
                "error": str(e),
                "recommendations": []
            }
        else:
            raise

# Function to send recommendations to API endpoint
def send_recommendations(recommendations, output_destination):
    """
    Send recommendations to API endpoint or save to JSON file
    
    Args:
        recommendations (dict): Recommendations data
        output_destination (str): API endpoint or path to save JSON file
        
    Returns:
        dict or None: API response if endpoint, None if file
    """
    try:
        if output_destination.startswith('http'):
            # It's an API endpoint
            response = requests.post(output_destination, json=recommendations)
            response.raise_for_status()
            print(f"Recommendations successfully sent to {output_destination}")
            return response.json()
        else:
            # It's a local JSON file
            with open(output_destination, 'w') as file:
                json.dump(recommendations, file, indent=2)
            print(f"Recommendations successfully saved to {output_destination}")
            return None
    except (requests.exceptions.RequestException, IOError) as e:
        print(f"Error sending/saving recommendations: {str(e)}")
        raise