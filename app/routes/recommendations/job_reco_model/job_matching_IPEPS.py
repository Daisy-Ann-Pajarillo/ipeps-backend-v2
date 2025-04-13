# job_matcher.py - Enhanced with Novelty Features
import json
import json
import re
from datetime import datetime
import nltk
from nltk.stem import SnowballStemmer
from nltk.corpus import stopwords
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import Counter
from datetime import datetime
import string
from nltk.tokenize import word_tokenize
from nltk.util import ngrams

class JobMatcher:
    def __init__(self, debug=True):
        """Initialize the enhanced job matcher with advanced text processing tools"""
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt', quiet=True)
        nltk.download('wordnet', quiet=True)
        
        self.debug = debug
        self.stemmer = SnowballStemmer("english")
        
        # Define domain-specific stopwords (novel feature)
        self.domain_stopwords = [
            'job', 'position', 'work', 'experience', 'skills', 'requirements',
            'responsibilities', 'qualifications', 'apply', 'candidate', 'employment',
            'company', 'organization', 'we offer', 'required', 'preferred',
            'please', 'submit', 'resume', 'application'
        ]
        
        # Custom TF-IDF vectorizer with enhanced parameters
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),  # Increased to capture more contextual phrases
            max_features=7500,   # Increased to capture more features
            stop_words='english',
            min_df=2,            # Require terms to appear in at least 2 documents
            use_idf=True,
            sublinear_tf=True    # Apply sublinear scaling to reduce impact of high frequencies
        )
        
        # Define skill categories for semantic clustering (novel feature)
        self.skill_clusters = {
            'programming': ['python', 'java', 'javascript', 'c++', 'ruby', 'php', 'go', 'swift', 
                           'typescript', 'react', 'angular', 'vue', 'node', 'django', 'flask', 
                           'spring', 'laravel', 'coding', 'development', 'software'],
            'data_science': ['machine learning', 'data analysis', 'statistics', 'r', 'python', 
                            'tensorflow', 'pytorch', 'sklearn', 'pandas', 'numpy', 'data mining',
                            'big data', 'analytics', 'data visualization', 'tableau', 'power bi'],
            'design': ['ui', 'ux', 'user interface', 'user experience', 'graphic design', 
                      'photoshop', 'illustrator', 'figma', 'sketch', 'adobe', 'creative'],
            'business': ['marketing', 'sales', 'management', 'business development', 'strategy',
                        'leadership', 'project management', 'product management', 'mba'],
            'soft_skills': ['communication', 'teamwork', 'collaboration', 'problem solving', 
                          'critical thinking', 'time management', 'organization'],
            'networking_fundamentals': [
                'tcp/ip', 'osi model', 'subnetting', 'ipv4', 'ipv6', 'dns', 'dhcp',
                'nat', 'wan', 'lan', 'vlan', 'routing', 'switching', 'network topology'
            ],
            'cisco_technologies': [
                'cisco ios', 'cisco cli', 'ccna', 'ccnp', 'eigrp', 'ospf', 'bgp', 
                'stp', 'vlan trunking', 'acl', 'vpn', 'mpls', 'sd-wan'
            ],
            'network_security': [
                'firewalls', 'vpn', 'acl', 'ids', 'ips', 'security protocols', 
                'zero trust', 'ssl/tls', 'authentication', 'encryption', 'penetration testing'
            ],
            'network_troubleshooting': [
                'wireshark', 'packet tracer', 'gns3', 'ping', 'traceroute', 
                'netstat', 'nmap', 'network diagnostics', 'latency analysis', 'qos'
    ]
        }
        
        # Initialize recency weighting parameters (novel feature)
        self.time_decay_lambda = 0.05  # Controls the decay rate
        self.max_recency_boost = 1.5   # Maximum boost for very recent experience
        
        # Position importance weights (novel feature)
        self.position_weights = {
            'job_title': 3.0,
            'skills': 2.5,
            'requirements': 2.0,
            'description': 1.0,
            'company': 0.8
        }
        
        # Skill rarity index (will be populated during processing)
        self.skill_rarity_index = {}
        
    def extract_key_terms(self, text):
        """Extract potential skill terms from text (novel feature)"""
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        
        # Remove punctuation and stopwords
        stop_words = set(stopwords.words('english')).union(self.domain_stopwords)
        filtered_tokens = [w for w in tokens if w not in stop_words and w not in string.punctuation]
        
        # Extract unigrams, bigrams and trigrams as potential skills
        unigrams = filtered_tokens
        bigrams = [' '.join(bg) for bg in ngrams(filtered_tokens, 2)]
        trigrams = [' '.join(tg) for tg in ngrams(filtered_tokens, 3)]
        
        # Combine all potential skill terms
        all_terms = unigrams + bigrams + trigrams
        
        return all_terms
        
    def build_skill_rarity_index(self, job_descriptions):
        """Build an index of skill term rarity across job postings (novel feature)"""
        # Extract all potential skill terms from all job descriptions
        all_job_terms = []
        for desc in job_descriptions:
            terms = self.extract_key_terms(desc)
            all_job_terms.extend(terms)
        
        # Count term frequencies
        term_counts = Counter(all_job_terms)
        
        # Calculate inverse frequency (rarity) for each term
        total_jobs = len(job_descriptions)
        for term, count in term_counts.items():
            # More rare terms get higher weights
            self.skill_rarity_index[term] = np.log(total_jobs / (count + 1)) + 1
    
    def get_semantic_cluster_weight(self, term):
        """Get the semantic cluster weight for a term (novel feature)"""
        for cluster, terms in self.skill_clusters.items():
            if any(skill_term in term for skill_term in terms):
                return 1.2  # Boost terms that are part of a skill cluster
        return 1.0
    
    def calculate_recency_weight(self, term, profile_data):
        """Calculate recency weight based on work experience (novel feature)"""
        # Default weight
        recency_weight = 1.0
        
        # Check work experience for this term
        try:
            work_exp = profile_data.get('work_experience', [])
            
            # Initialize variables to track the most recent mention
            most_recent_date = None
            
            for exp in work_exp:
                # Check if the term appears in the position or description
                position = exp.get('position', '').lower()
                company = exp.get('company_name', '').lower()
                
                if term in position or term in company:
                    # Parse the end date
                    end_date = exp.get('end_date', None)
                    
                    # If still current, use today's date
                    if end_date is None or end_date.lower() == 'present':
                        end_date = datetime.now().strftime('%Y-%m-%d')
                    
                    # Try to parse the date
                    try:
                        date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                        
                        # Update most recent date if this is more recent
                        if most_recent_date is None or date_obj > most_recent_date:
                            most_recent_date = date_obj
                    except:
                        # If date parsing fails, continue to the next experience
                        continue
            
            # Calculate recency weight if we found a date
            if most_recent_date:
                days_since = (datetime.now() - most_recent_date).days
                recency_weight = self.max_recency_boost * np.exp(-self.time_decay_lambda * days_since/365.0)
                # Ensure the weight is at least 1.0
                recency_weight = max(1.0, recency_weight)
        
        except Exception as e:
            if self.debug:
                print(f"Error calculating recency weight: {str(e)}")
            recency_weight = 1.0
            
        return recency_weight

    def calculate_position_weight(self, term, section):
        """Calculate weight based on term position in document (novel feature)"""
        for section_name, weight in self.position_weights.items():
            if section_name in section.lower():
                return weight
        return 1.0

    def preprocess_text(self, text):
        """Enhanced text preprocessing (improved from original)"""
        # Convert to lowercase string
        text = str(text).lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        # Remove domain-specific stopwords (novel feature)
        words = text.split()
        filtered_words = [word for word in words if word not in self.domain_stopwords]
        text = ' '.join(filtered_words)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Apply stemming
        stemmed_words = [self.stemmer.stem(word) for word in text.split()]
        
        return ' '.join(stemmed_words)
    
    def extract_profile_features(self, profile_data):
        """Extract weighted features from profile with enhanced weighting (novel feature)"""
        try:
            # Create structured feature sections for position-based weighting
            feature_sections = {}
            
            # Education (weight: 2.5x) - increased from original
            education = profile_data.get('educational_background', [])
            education_text = " ".join([
                f"{edu['degree_or_qualification']} {edu['field_of_study']}"
                for edu in education
            ])
            feature_sections['education'] = education_text
            
            # Skills (weight: 4x) - increased from original
            skills = profile_data.get('other_skills', [])
            skills_text = " ".join([
                skill['skills'] for skill in skills
            ])
            feature_sections['skills'] = skills_text
            
            # Work Experience (weight: 3.5x) - increased from original
            work_exp = profile_data.get('work_experience', [])
            work_text = " ".join([
                f"{exp['position']} {exp['company_name']}"
                for exp in work_exp
            ])
            feature_sections['work_experience'] = work_text
            
            # Training (weight: 2.5x) - increased from original
            training = profile_data.get('other_training', [])
            training_text = " ".join([
                f"{t['course_name']} {t['skills_acquired']}"
                for t in training
            ])
            feature_sections['training'] = training_text
            
            # Preprocess each section
            processed_sections = {
                section: self.preprocess_text(text)
                for section, text in feature_sections.items()
            }
            

            # Apply section weights
            weighted_sections = {
                'education': processed_sections['education'] * int(2.5),
                'skills': processed_sections['skills'] * int(4.0),
                'work_experience': processed_sections['work_experience'] * int(3.5),
                'training': processed_sections['training'] * int(2.5)
            }
            
            # Combine all weighted sections
            combined_text = " ".join(weighted_sections.values())
            
            return combined_text
            
        except Exception as e:
            print(f"Error extracting profile features: {str(e)}")
            raise
    
    def process_job_postings(self, job_posts):
        """Process job posts with section-based weighting (novel feature)"""
        processed_jobs = {}
        
        for title, description in job_posts.items():
            # Split description into sections (if possible)
            sections = {}
            
            # Extract job title section
            sections['job_title'] = title
            
            # Basic section extraction (very simplified)
            if "Requirements:" in description:
                parts = description.split("Requirements:")
                sections['description'] = parts[0]
                sections['requirements'] = "Requirements:" + parts[1]
            else:
                sections['description'] = description
            
            # Process each section
            processed_sections = {
                section: self.preprocess_text(text)
                for section, text in sections.items()
            }
            
            # Apply section weights
            weighted_text = ""
            for section, text in processed_sections.items():
                weight = self.position_weights.get(section, 1.0)
                # Convert float to int before multiplying with text
                weighted_text += f" {text * int(weight)}"
            
            processed_jobs[title] = weighted_text.strip()
        
        return processed_jobs
    
    def generate_skill_gap_vector(self, profile_features, job_features, feature_names):
        """Generate a skill gap vector to penalize missing critical skills (novel feature)"""
        # Extract profile and job terms
        profile_terms = set(profile_features.split())
        
        # Initialize skill gap vector
        skill_gap_vector = np.zeros(len(feature_names))
        
        # Count missing skills for each job
        for job_idx, job_text in enumerate(job_features):
            job_terms = set(job_text.split())
            
            # Find potential skill terms in job that are not in profile
            missing_skills = job_terms - profile_terms
            
            # Calculate penalty for missing skills
            for term_idx, term in enumerate(feature_names):
                if term in missing_skills:
                    # Higher penalty for rarer skills
                    rarity_factor = self.skill_rarity_index.get(term, 1.0)
                    skill_gap_vector[term_idx] += rarity_factor * 0.1
        
        return skill_gap_vector
    
    def get_recommendations(self, profile_data, job_posts, top_n=5):
        """Get job recommendations with novelty enhancements"""
        try:
            # Process profile with enhanced feature extraction
            profile_features = self.extract_profile_features(profile_data)
            
            # Process job posts with section-based weighting
            processed_jobs = self.process_job_postings(job_posts)
            
            # Build skill rarity index (novel feature)
            self.build_skill_rarity_index(list(processed_jobs.values()))
            
            # Combine all texts for vectorization
            all_texts = list(processed_jobs.values()) + [profile_features]
            
            # Create TF-IDF matrix with enhanced vectorizer
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Get feature names for semantic analysis
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Generate skill gap vector (novel feature)
            skill_gap_vector = self.generate_skill_gap_vector(
                profile_features, 
                list(processed_jobs.values()),
                feature_names
            )
            
            # Apply semantic clustering and recency weighting (novel feature)
            profile_vector = tfidf_matrix[-1:].toarray()[0]
            job_vectors = tfidf_matrix[:-1].toarray()
            
            # Initialize match scores array
            match_scores = np.zeros(len(job_vectors))
            
            # Calculate enhanced similarity with multiple factors
            for i, job_vector in enumerate(job_vectors):
                # Basic cosine similarity
                dot_product = np.dot(profile_vector, job_vector)
                profile_norm = np.linalg.norm(profile_vector)
                job_norm = np.linalg.norm(job_vector)
                
                if profile_norm > 0 and job_norm > 0:
                    base_similarity = dot_product / (profile_norm * job_norm)
                else:
                    base_similarity = 0
                
                # Apply skill gap penalty (novel feature) - REDUCED IMPACT
                # Changed from 0.1 to 0.02 to reduce the penalty
                skill_gap_penalty = np.sum(skill_gap_vector) * 0.02
                
                # Apply semantic clustering boost (novel feature)
                semantic_boost = 1.0
                boost_count = 0
                
                for term_idx, term in enumerate(feature_names):
                    if job_vector[term_idx] > 0 and profile_vector[term_idx] > 0:
                        # Apply cluster weight
                        cluster_boost = self.get_semantic_cluster_weight(term) - 1.0
                        
                        # Apply recency weight
                        recency_boost = self.calculate_recency_weight(term, profile_data) - 1.0
                        
                        # Add boosts to the total
                        semantic_boost += cluster_boost + recency_boost
                        boost_count += 1
                
                # Normalize semantic boost by the number of matching terms
                if boost_count > 0:
                    semantic_boost = 1.0 + (semantic_boost - 1.0) / boost_count
                    semantic_boost = min(1.5, semantic_boost)  # Cap the boost
                
                # Calculate final match score
                # Adjust the formula to ensure positive scores
                # Base similarity is typically between 0 and 1
                # Apply a positive scaling factor to make scores more meaningful
                base_score = base_similarity * 100  # Scale to percentage-like values
                boosted_score = base_score * semantic_boost  # Apply semantic boost
                final_score = boosted_score - (skill_gap_penalty * base_score / 10)  # Apply reduced penalty
                
                match_scores[i] = final_score
            
            # Create job-score pairs
            job_titles = list(processed_jobs.keys())
            job_scores = list(zip(job_titles, match_scores))
            
            # Sort by score and get top recommendations
            recommendations = sorted(job_scores, key=lambda x: x[1], reverse=True)[:top_n]
            
            # Format recommendations with detailed scores
            detailed_recommendations = []
            for job_title, score in recommendations:
                # Ensure scores are positive and capped at 100
                match_percentage = min(100, max(0, score))
                recommendation = {
                    'job_title': job_title,
                    'match_score': match_percentage,
                    'job_description': job_posts[job_title]
                }
                detailed_recommendations.append(recommendation)
                
                if self.debug:
                    print(f"\nJob: {job_title}")
                    print(f"Match Score: {match_percentage:.1f}%")
            
            return detailed_recommendations
            
        except Exception as e:
            print(f"Error getting recommendations: {str(e)}")
            raise



def transform_job_postings(input_json, return_id_map=False):
    # Initialize the output dictionary
    transformed_jobs = {}
    # Initialize job_id mapping dictionary
    job_id_map = {}
    
    # Process each job posting
    for job in input_json.get('job_postings', []):
        job_title = job.get('job_title', 'Unknown Position')
        job_id = job.get('job_id')
        
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
        unique_job_title = job_title
        if job_title in transformed_jobs:
            unique_id = job.get('created_at', '')[:10]  # Get date part of timestamp
            unique_job_title = f"{job_title} ({unique_id})"
        
        transformed_jobs[unique_job_title] = full_description.strip()
        
        # Store the mapping between the (possibly modified) job title and the job_id
        if job_id is not None:
            job_id_map[unique_job_title] = job_id
    
    if return_id_map:
        return transformed_jobs, job_id_map
    else:
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

# Load the job postings in new format
def load_job_postings(filename):
    with open(filename, 'r') as f:
        return json.load(f)

# Load profile data
def load_profile(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def format_recommendations_for_frontend(recommendations, original_job_postings_json):
    # Create a lookup dictionary for the original job postings using job_id
    job_lookup = {}
    for job in original_job_postings_json.get('job_postings', []):
        job_id = job.get('job_id')
        if job_id is not None:
            job_lookup[job_id] = job
    
    # Format the response
    formatted_response = {
        "success": True,
        "recommendations": []
    }
    
    for rec in recommendations:
        # Extract the job_id from the recommendation
        job_id = rec.get('job_id')
        match_score = rec['match_score']
        
        # Find the original job posting using job_id
        if job_id in job_lookup:
            # Create a recommendation object with the match score and original posting
            recommendation = {
                "match_score": round(match_score, 2),
                "job_posting": job_lookup[job_id],
                "novelty_factors": generate_novelty_explanation(rec)
            }
            formatted_response["recommendations"].append(recommendation)
    
    return formatted_response

# New function to generate human-readable explanation of recommendation factors
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
def run_job_matching(profile_file, job_postings_file, top_n=5, return_json=False):
    # Load data
    profile_data = load_profile(profile_file)
    job_postings_json = load_job_postings(job_postings_file)
    
    # Transform job postings to the required format, passing job_id
    transformed_jobs, job_id_map = transform_job_postings(job_postings_json, return_id_map=True)
    
    # Initialize the novelty-enhanced job matcher
    matcher = JobMatcher(debug=True)
    
    # Get recommendations
    recommendations = matcher.get_recommendations(profile_data, transformed_jobs, top_n)
    
    # Add job_id to each recommendation using the job_id_map
    for rec in recommendations:
        job_title = rec['job_title']
        rec['job_id'] = job_id_map.get(job_title)
    
    # Return the appropriate format
    if return_json:
        return format_recommendations_for_frontend(recommendations, job_postings_json)
    else:
        return recommendations

# Function to save recommendations to a JSON file
def save_recommendations_json(recommendations, output_file):
    with open(output_file, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"Recommendations saved to {output_file}")

# Example usage
if __name__ == "__main__":
    # Replace with your actual file paths
    profile_file = r"C:\Users\Renz\Desktop\rec_sys\JSON Files\profile_data2.JSON"
    job_postings_file = r"C:\Users\Renz\Desktop\rec_sys\JSON Files\job_postings2.JSON"
    output_file = r"C:\Users\Renz\Desktop\rec_sys\recommendations.json"
    
    # Get top 3 recommendations in JSON format for the frontend
    recommendations_json = run_job_matching(
        profile_file, 
        job_postings_file,
        top_n=3,
        return_json=True
    )
    
    # Save the recommendations to a file
    save_recommendations_json(recommendations_json, output_file)
    
    # Print the JSON structure
    print("\nJSON Output for Frontend:")
    print(json.dumps(recommendations_json, indent=2))