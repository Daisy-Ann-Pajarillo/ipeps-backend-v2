# run_job_matching.py - Updated to use API endpoints instead of JSON files
import requests
from job_matcher import NoveltyEnhancedJobMatcher
from transform_jobs import transform_job_postings

# Fetch job postings from API
def fetch_job_postings(api_endpoint):
    try:
        response = requests.get(api_endpoint)
        response.raise_for_status()  # Raise exception for non-200 responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching job postings: {str(e)}")
        raise

# Fetch profile data from API
def fetch_profile(api_endpoint):
    try:
        response = requests.get(api_endpoint)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching profile data: {str(e)}")
        raise

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
def run_job_matching(profile_api_endpoint, job_postings_api_endpoint, top_n=5, return_json=False):
    # Fetch data from APIs
    profile_data = fetch_profile(profile_api_endpoint)
    job_postings_json = fetch_job_postings(job_postings_api_endpoint)
    
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

# Function to send recommendations to API endpoint
def send_recommendations(recommendations, output_api_endpoint):
    try:
        response = requests.post(output_api_endpoint, json=recommendations)
        response.raise_for_status()
        print(f"Recommendations successfully sent to {output_api_endpoint}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending recommendations: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Replace with your actual API endpoints
    profile_api_endpoint = "https://api.example.com/profile"
    job_postings_api_endpoint = "https://api.example.com/jobs"
    # output_api_endpoint = "https://api.example.com/recommendations"
    
    # Get top 3 recommendations in JSON format for the frontend
    recommendations_json = run_job_matching(
        profile_api_endpoint, 
        job_postings_api_endpoint,
        top_n=3,
        return_json=True
    )
    
    # Commented out: sending recommendations to API endpoint
    # response = send_recommendations(recommendations_json, output_api_endpoint)
    # print("\nAPI Response:")
    # print(response)
    
    # Instead, just print the JSON structure
    print("\nRecommendations JSON:")
    print(recommendations_json)