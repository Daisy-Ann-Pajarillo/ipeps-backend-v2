# scholarship_matcher.py - Specialized for scholarship recommendation
import json
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

nltk.data.path.insert(0, './nltk_data')

class ScholarshipMatcher:
    def __init__(self, debug=True):
        """Initialize the scholarship matcher with specialized text processing tools"""
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt', quiet=True)
        nltk.download('wordnet', quiet=True)
        
        self.debug = debug
        self.stemmer = SnowballStemmer("english")
        
        # Define domain-specific stopwords for scholarships
        self.domain_stopwords = [
            'scholarship', 'program', 'application', 'apply', 'candidate', 'opportunity',
            'eligibility', 'eligible', 'requirements', 'qualifications', 'qualified',
            'please', 'submit', 'resume', 'application', 'student', 'university',
            'college', 'academic', 'degree', 'funding', 'award', 'grant', 'financial'
        ]
        
        # Custom TF-IDF vectorizer with enhanced parameters
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),  # Capture contextual phrases
            max_features=7500,   # Capture more features
            stop_words='english',
            min_df=2,            # Require terms to appear in at least 2 documents
            use_idf=True,
            sublinear_tf=True    # Apply sublinear scaling
        )
        
        # Define skill/field categories for semantic clustering
        self.field_clusters = {
            'culinary_arts': ['chef', 'culinary', 'cooking', 'food', 'cuisine', 'hospitality', 
                             'restaurant', 'kitchen', 'catering', 'gastronomy', 'baking'],
            'technology': ['programming', 'software', 'development', 'computer science', 'IT',
                          'coding', 'web development', 'data science', 'artificial intelligence'],
            'medical': ['medicine', 'healthcare', 'nursing', 'medical', 'physician', 'doctor',
                       'clinical', 'patient care', 'hospital', 'pharmacy', 'dental'],
            'business': ['business', 'management', 'administration', 'marketing', 'finance',
                        'accounting', 'economics', 'entrepreneurship', 'MBA'],
            'engineering': ['engineering', 'mechanical', 'electrical', 'civil', 'chemical',
                           'aerospace', 'architecture', 'design', 'construction'],
            'arts_humanities': ['arts', 'humanities', 'design', 'creative', 'music', 'theater',
                              'literature', 'philosophy', 'history', 'language', 'culture'],
            'education': ['teaching', 'education', 'pedagogy', 'curriculum', 'classroom',
                         'instruction', 'learning', 'school', 'teacher', 'educational'],
            'social_sciences': ['psychology', 'sociology', 'anthropology', 'political science',
                               'economics', 'geography', 'urban planning']
        }
        
        # Initialize scholarship-specific weighting parameters
        self.time_to_expiry_importance = 0.08  # Higher weight for expiring soon scholarships
        self.max_deadline_boost = 1.6          # Maximum boost for urgent deadlines
        
        # Section importance weights tailored for scholarships
        self.section_weights = {
            'scholarship_title': 3.0,
            'skills': 3.0,
            'requirements': 2.5,
            'description': 1.5,
            'sponsor': 1.0
        }
        
        # Qualification rarity index (will be populated during processing)
        self.qualification_rarity_index = {}
        
    def extract_key_terms(self, text):
        """Extract potential skill and qualification terms from text"""
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        
        # Remove punctuation and stopwords
        stop_words = set(stopwords.words('english')).union(self.domain_stopwords)
        filtered_tokens = [w for w in tokens if w not in stop_words and w not in string.punctuation]
        
        # Extract n-grams as potential skills/qualifications
        unigrams = filtered_tokens
        bigrams = [' '.join(bg) for bg in ngrams(filtered_tokens, 2)]
        trigrams = [' '.join(tg) for tg in ngrams(filtered_tokens, 3)]
        
        # Combine all potential terms
        all_terms = unigrams + bigrams + trigrams
        
        return all_terms
        
    def build_qualification_rarity_index(self, scholarship_descriptions):
        """Build an index of qualification term rarity across scholarship postings"""
        # Extract all potential terms from all scholarship descriptions
        all_terms = []
        for desc in scholarship_descriptions:
            terms = self.extract_key_terms(desc)
            all_terms.extend(terms)
        
        # Count term frequencies
        term_counts = Counter(all_terms)
        
        # Calculate inverse frequency (rarity) for each term
        total_scholarships = len(scholarship_descriptions)
        for term, count in term_counts.items():
            # More rare terms get higher weights
            self.qualification_rarity_index[term] = np.log(total_scholarships / (count + 1)) + 1
    
    def get_field_cluster_weight(self, term):
        """Get the field cluster weight for a term"""
        for cluster, terms in self.field_clusters.items():
            if any(field_term in term for field_term in terms):
                return 1.3  # Boost terms that are part of a field cluster
        return 1.0
    
    # In the calculate_deadline_weight method, add string cleaning to remove whitespace
    def calculate_deadline_weight(self, scholarship_data):
        """Calculate urgency weight based on scholarship deadline"""
        # Default weight
        deadline_weight = 1.0
        
        # Check for expiration date
        try:
            expiration_date = scholarship_data.get('expiration_date', '')
            
            if expiration_date:
                # Try to parse the date - handle multiple formats
                try:
                    # Remove any 'Expires: ' prefix
                    if 'Expires: ' in expiration_date:
                        expiration_date = expiration_date.replace('Expires: ', '')
                    
                    # Clean the string by removing whitespace (including newlines)
                    expiration_date = expiration_date.strip()
                    
                    # Parse date
                    date_obj = datetime.strptime(expiration_date, '%Y-%m-%d')
                    
                    # Calculate days until expiration
                    days_until_expiry = (date_obj - datetime.now()).days
                    
                    # If deadline is approaching, increase weight (inverse relationship)
                    if days_until_expiry > 0:
                        # Exponential function gives higher weight to closer deadlines
                        # Max boost for deadlines within 30 days
                        deadline_weight = self.max_deadline_boost * np.exp(-days_until_expiry / 30)
                        # Ensure the weight is at least 1.0
                        deadline_weight = max(1.0, deadline_weight)
                except Exception as e:
                    if self.debug:
                        print(f"Error parsing expiration date: {str(e)}")
        
        except Exception as e:
            if self.debug:
                print(f"Error calculating deadline weight: {str(e)}")
            
        return deadline_weight

    def calculate_academic_field_match(self, profile_data, term):
        """Calculate weight based on academic field match"""
        field_weight = 1.0
        
        try:
            education = profile_data.get('educational_background', [])
            
            for edu in education:
                field = edu.get('field_of_study', '').lower()
                
                # Check if the term is in the field of study
                if term.lower() in field:
                    field_weight = 1.5  # Boost if term matches student's field
                    break
                
                # Check if term is related to the field via our clusters
                for cluster, field_terms in self.field_clusters.items():
                    if any(field_term in field for field_term in field_terms) and any(field_term in term for field_term in field_terms):
                        field_weight = 1.3  # Smaller boost for related fields
                        break
        
        except Exception as e:
            if self.debug:
                print(f"Error calculating academic field match: {str(e)}")
        
        return field_weight

    def calculate_section_weight(self, term, section):
        """Calculate weight based on term position in scholarship document"""
        for section_name, weight in self.section_weights.items():
            if section_name in section.lower():
                return weight
        return 1.0

    def preprocess_text(self, text):
        """Enhanced text preprocessing for scholarship matching"""
        # Convert to lowercase string
        text = str(text).lower()
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        
        # Remove domain-specific stopwords
        words = text.split()
        filtered_words = [word for word in words if word not in self.domain_stopwords]
        text = ' '.join(filtered_words)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Apply stemming
        stemmed_words = [self.stemmer.stem(word) for word in text.split()]
        
        return ' '.join(stemmed_words)
    
    def extract_profile_features(self, profile_data):
        """Extract weighted features from profile with scholarship-specific weighting"""
        try:
            # Create structured feature sections for scholarship-focused weighting
            feature_sections = {}
            
            # Education (weight: 3.5x) - highest priority for scholarships
            education = profile_data.get('educational_background', [])
            education_text = " ".join([
                f"{edu.get('degree_or_qualification', '')} {edu.get('field_of_study', '')} {edu.get('training_institution', '')}"
                for edu in education
            ])
            feature_sections['education'] = education_text
            
            # Skills (weight: 3.0x)
            skills = profile_data.get('other_skills', [])
            skills_text = " ".join([
                skill.get('skills', '') for skill in skills
            ])
            feature_sections['skills'] = skills_text
            
            # Work Experience (weight: 2.5x) - less weight than education for scholarships
            work_exp = profile_data.get('work_experience', [])
            work_text = " ".join([
                f"{exp.get('position', '')} {exp.get('company_name', '')}"
                for exp in work_exp
            ])
            feature_sections['work_experience'] = work_text
            
            # Training (weight: 3.0x) - important for specialized scholarships
            training = profile_data.get('other_training', [])
            training_text = " ".join([
                f"{t.get('course_name', '')} {t.get('skills_acquired', '')}"
                for t in training
            ])
            feature_sections['training'] = training_text
            
            # Certifications (weight: 2.5x) - can be important for eligibility
            # This assumes certifications are somewhere in profile data
            certs = []
            # Try to extract from educational background
            for edu in education:
                if "certificate" in edu.get('degree_or_qualification', '').lower():
                    certs.append(edu.get('degree_or_qualification', ''))
            
            # Try to extract from other training
            for training in profile_data.get('other_training', []):
                if "certificate" in training.get('course_name', '').lower():
                    certs.append(training.get('course_name', ''))
            
            cert_text = " ".join(certs)
            feature_sections['certifications'] = cert_text
            
            # Preprocess each section
            processed_sections = {
                section: self.preprocess_text(text)
                for section, text in feature_sections.items()
            }
            
            # Apply section weights specific to scholarship matching
            weighted_sections = {
                'education': processed_sections['education'] * int(3.5),
                'skills': processed_sections['skills'] * int(3.0),
                'work_experience': processed_sections['work_experience'] * int(2.5),
                'training': processed_sections['training'] * int(3.0),
                'certifications': processed_sections.get('certifications', '') * int(2.5)
            }
            
            # Combine all weighted sections
            combined_text = " ".join(weighted_sections.values())
            
            return combined_text
            
        except Exception as e:
            print(f"Error extracting profile features: {str(e)}")
            raise
    
    def process_scholarship_postings(self, scholarship_posts):
        """Process scholarship posts with section-based weighting"""
        processed_scholarships = {}
        
        for title, description in scholarship_posts.items():
            # Split description into sections
            sections = {}
            
            # Extract scholarship title section
            sections['scholarship_title'] = title
            
            # Try to extract other sections
            section_pattern = r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)'
            matches = re.findall(section_pattern, description, re.DOTALL)
            
            for section_name, content in matches:
                sections[section_name.lower()] = content.strip()
            
            # If no sections found, use the whole description
            if not matches:
                sections['description'] = description
            
            # Process each section
            processed_sections = {
                section: self.preprocess_text(text)
                for section, text in sections.items()
            }
            
            # Apply section weights
            weighted_text = ""
            for section, text in processed_sections.items():
                weight = self.section_weights.get(section, 1.0)
                # Convert float to int before multiplying with text
                weighted_text += f" {text * int(weight)}"
            
            processed_scholarships[title] = weighted_text.strip()
        
        return processed_scholarships
    
    def generate_eligibility_gap_vector(self, profile_features, scholarship_features, feature_names):
        """Generate an eligibility gap vector to penalize missing critical requirements"""
        # Extract profile terms
        profile_terms = set(profile_features.split())
        
        # Initialize eligibility gap vector
        eligibility_gap_vector = np.zeros(len(feature_names))
        
        # Count missing requirements for each scholarship
        for scholarship_idx, scholarship_text in enumerate(scholarship_features):
            scholarship_terms = set(scholarship_text.split())
            
            # Find potential requirement terms in scholarship that are not in profile
            missing_requirements = scholarship_terms - profile_terms
            
            # Calculate penalty for missing requirements
            for term_idx, term in enumerate(feature_names):
                if term in missing_requirements:
                    # Higher penalty for rarer requirements
                    rarity_factor = self.qualification_rarity_index.get(term, 1.0)
                    eligibility_gap_vector[term_idx] += rarity_factor * 0.1
        
        return eligibility_gap_vector
    
    def get_recommendations(self, profile_data, scholarship_posts, top_n=5):
        """Get scholarship recommendations with tailored enhancement factors"""
        try:
            # Process profile with scholarship-focused feature extraction
            profile_features = self.extract_profile_features(profile_data)
            
            # Process scholarship posts with section-based weighting
            processed_scholarships = self.process_scholarship_postings(scholarship_posts)
            
            # Build qualification rarity index
            self.build_qualification_rarity_index(list(processed_scholarships.values()))
            
            # Combine all texts for vectorization
            all_texts = list(processed_scholarships.values()) + [profile_features]
            
            # Create TF-IDF matrix
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Get feature names for semantic analysis
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Generate eligibility gap vector
            eligibility_gap_vector = self.generate_eligibility_gap_vector(
                profile_features, 
                list(processed_scholarships.values()),
                feature_names
            )
            
            # Apply field clustering and deadline weighting
            profile_vector = tfidf_matrix[-1:].toarray()[0]
            scholarship_vectors = tfidf_matrix[:-1].toarray()
            
            # Initialize match scores array
            match_scores = np.zeros(len(scholarship_vectors))
            
            # Get original sections for deadline weighting
            scholarship_sections = {}
            for title, description in scholarship_posts.items():
                scholarship_sections[title] = re.findall(r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)', description, re.DOTALL)
            
            # Calculate enhanced similarity with scholarship-specific factors
            scholarship_titles = list(processed_scholarships.keys())
            for i, scholarship_vector in enumerate(scholarship_vectors):
                # Current scholarship title
                scholarship_title = scholarship_titles[i]
                
                # Basic cosine similarity
                dot_product = np.dot(profile_vector, scholarship_vector)
                profile_norm = np.linalg.norm(profile_vector)
                scholarship_norm = np.linalg.norm(scholarship_vector)
                
                if profile_norm > 0 and scholarship_norm > 0:
                    base_similarity = dot_product / (profile_norm * scholarship_norm)
                else:
                    base_similarity = 0
                
                # Apply eligibility gap penalty - MODERATE IMPACT
                eligibility_gap_penalty = np.sum(eligibility_gap_vector) * 0.05
                
                # Apply field matching boost
                field_match_boost = 1.0
                boost_count = 0
                
                for term_idx, term in enumerate(feature_names):
                    if scholarship_vector[term_idx] > 0 and profile_vector[term_idx] > 0:
                        # Apply field cluster weight
                        cluster_boost = self.get_field_cluster_weight(term) - 1.0
                        
                        # Apply academic field match weight
                        field_match = self.calculate_academic_field_match(profile_data, term) - 1.0
                        
                        # Add boosts to the total
                        field_match_boost += cluster_boost + field_match
                        boost_count += 1
                
                # Normalize field match boost by the number of matching terms
                if boost_count > 0:
                    field_match_boost = 1.0 + (field_match_boost - 1.0) / boost_count
                    field_match_boost = min(1.6, field_match_boost)  # Cap the boost
                
                # Apply deadline urgency boost
                # Extract expiration date from scholarship sections
                expiration_data = None
                for section_name, content in scholarship_sections.get(scholarship_title, []):
                    if section_name == "EXPIRATION_DATE":
                        expiration_data = content
                        break
                
                deadline_boost = self.calculate_deadline_weight({"expiration_date": expiration_data}) if expiration_data else 1.0
                
                # Calculate final match score
                base_score = base_similarity * 100  # Scale to percentage-like values
                boosted_score = base_score * field_match_boost * deadline_boost  # Apply boosts
                final_score = boosted_score - (eligibility_gap_penalty * base_score / 10)  # Apply penalty
                
                match_scores[i] = final_score
            
            # Create scholarship-score pairs
            scholarship_titles = list(processed_scholarships.keys())
            scholarship_scores = list(zip(scholarship_titles, match_scores))
            
            # Sort by score and get top recommendations
            recommendations = sorted(scholarship_scores, key=lambda x: x[1], reverse=True)[:top_n]
            
            # Format recommendations with detailed scores
            detailed_recommendations = []
            for scholarship_title, score in recommendations:
                # Ensure scores are positive and capped at 100
                match_percentage = min(100, max(0, score))
                recommendation = {
                    'scholarship_title': scholarship_title,
                    'match_score': match_percentage,
                    'scholarship_description': scholarship_posts[scholarship_title]
                }
                detailed_recommendations.append(recommendation)
                
                if self.debug:
                    print(f"\nScholarship: {scholarship_title}")
                    print(f"Match Score: {match_percentage:.1f}%")
            
            return detailed_recommendations
            
        except Exception as e:
            print(f"Error getting scholarship recommendations: {str(e)}")
            raise

    def transform_scholarship_postings(input_json, return_id_map=False):
        # Initialize the output dictionary
        transformed_scholarships = {}
        # Initialize scholarship_id mapping dictionary
        scholarship_id_map = {}
        
        # Process each scholarship posting
        for scholarship in input_json.get('scholarship_postings', []):
            scholarship_title = scholarship.get('scholarship_title', 'Unknown Scholarship')
            scholarship_id = scholarship.get('scholarship_id')
            
            # Create a structured scholarship description with clear sections
            description_parts = {}
            
            # Add SCHOLARSHIP_TITLE section (for title-based weighting)
            description_parts['scholarship_title'] = scholarship_title
            
            # Add the base scholarship description
            if scholarship.get('scholarship_description'):
                description_parts['description'] = scholarship.get('scholarship_description')
            
            # Add scholarship details
            scholarship_details = []
            scholarship_details.append(f"Scholarship: {scholarship_title}")
            
            if scholarship.get('status'):
                scholarship_details.append(f"Status: {scholarship.get('status')}")
            
            # Add scholarship details to a dedicated section
            description_parts['scholarship_details'] = "\n".join(scholarship_details)
            
            # Add employer information as a separate section
            employer = scholarship.get('employer', {})
            employer_parts = []
            
            if employer.get('company_name'):
                employer_parts.append(f"Organization: {employer.get('company_name')}")
            
            if employer.get('company_description'):
                employer_parts.append(f"Organization Description: {employer.get('company_description')}")
                
            if employer.get('address'):
                employer_parts.append(f"Location: {employer.get('address')}")
                
            if employer.get('email'):
                employer_parts.append(f"Contact: {employer.get('email')}")
                
            if employer.get('website'):
                employer_parts.append(f"Website: {employer.get('website')}")
            
            if employer_parts:
                description_parts['sponsor'] = "\n".join(employer_parts)
            
            # Extract posting date for recency calculations
            created_date = scholarship.get('created_at', '')
            if created_date:
                try:
                    # Handle ISO format or simple date format
                    if 'T' in created_date:
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(created_date, '%Y-%m-%d')
                    description_parts['posting_date'] = f"Posted: {date_obj.strftime('%Y-%m-%d')}"
                except (ValueError, TypeError):
                    # If date parsing fails, just use the string as-is
                    description_parts['posting_date'] = f"Posted: {created_date[:10]}"
            
            # Add expiration date if available
            expiration_date = scholarship.get('expiration_date', '')
            if expiration_date:
                try:
                    # Handle ISO format or simple date format
                    if 'T' in expiration_date:
                        date_obj = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(expiration_date, '%Y-%m-%d')
                    description_parts['expiration_date'] = f"Expires: {date_obj.strftime('%Y-%m-%d')}"
                except (ValueError, TypeError):
                    # If date parsing fails, just use the string as-is
                    description_parts['expiration_date'] = f"Expires: {expiration_date[:10]}"
            
            # Extract requirements and eligibility criteria from description
            # This is a simple extraction - in a real scenario would need more sophisticated NLP
            description_text = scholarship.get('scholarship_description', '')
            
            # Extract potential requirements using keywords
            requirements = []
            requirement_keywords = ["require", "must have", "eligible", "qualification", "criteria"]
            sentences = re.split(r'[.!?]+', description_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in requirement_keywords):
                    requirements.append(f"- {sentence}")
            
            # Add extracted requirements to a dedicated section
            if requirements:
                description_parts['requirements'] = "REQUIREMENTS/ELIGIBILITY:\n" + "\n".join(requirements)
            
            # Extract key skills from description
            skills_section = []
            skill_keywords = ["skill", "proficiency", "expertise", "experience with", "knowledge of"]
            
            for sentence in sentences:
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in skill_keywords):
                    skills_section.append(f"- {sentence}")
            
            # Add skills to a dedicated section
            if skills_section:
                description_parts['skills'] = "SKILLS/EXPERIENCE:\n" + "\n".join(skills_section)
            
            # Build the final structured description
            full_description = ""
            section_order = ['scholarship_title', 'description', 'scholarship_details', 'skills', 
                            'requirements', 'sponsor', 'posting_date', 'expiration_date']
            
            for section in section_order:
                if section in description_parts:
                    # Add section header for better parsing in the matcher
                    if section != 'scholarship_title':  # Don't add a header for the title
                        full_description += f"\n\n[SECTION:{section.upper()}]\n"
                    full_description += description_parts[section]
            
            # Add to the transformed scholarships dictionary
            # If there are duplicate scholarship titles, make them unique by appending creation timestamp
            unique_scholarship_title = scholarship_title
            if scholarship_title in transformed_scholarships:
                unique_id = scholarship.get('created_at', '')[:10]  # Get date part of timestamp
                unique_scholarship_title = f"{scholarship_title} ({unique_id})"
            
            transformed_scholarships[unique_scholarship_title] = full_description.strip()
            
            # Store the mapping between the (possibly modified) scholarship title and the scholarship_id
            if scholarship_id is not None:
                scholarship_id_map[unique_scholarship_title] = scholarship_id
        
        if return_id_map:
            return transformed_scholarships, scholarship_id_map
        else:
            return transformed_scholarships

    # Helper function to extract sections from transformed scholarship descriptions
    def extract_scholarship_sections(scholarship_description):
        """Extract structured sections from a scholarship description for section-based analysis"""
        sections = {}
        
        # Extract sections using regex pattern matching
        section_pattern = r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)'
        matches = re.findall(section_pattern, scholarship_description, re.DOTALL)
        
        # Process each found section
        for section_name, content in matches:
            sections[section_name.lower()] = content.strip()
        
        # Extract the scholarship title (which appears before any section markers)
        title_match = re.match(r'^(.*?)(?=\[SECTION:|$)', scholarship_description, re.DOTALL)
        if title_match:
            sections['scholarship_title'] = title_match.group(1).strip()
        
        return sections

    # run_scholarship_matching.py - Orchestration script for scholarship matching
    import json

    # Load the scholarship postings
    def load_scholarship_postings(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    # Load profile data
    def load_profile(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    def format_recommendations_for_frontend(recommendations, original_scholarship_postings_json):
        # Create a lookup dictionary for the original scholarship postings using scholarship_id
        scholarship_lookup = {}
        for scholarship in original_scholarship_postings_json.get('scholarship_postings', []):
            scholarship_id = scholarship.get('scholarship_id')
            if scholarship_id is not None:
                scholarship_lookup[scholarship_id] = scholarship
        
        # Format the response
        formatted_response = {
            "success": True,
            "recommendations": []
        }
        
        for rec in recommendations:
            # Extract the scholarship_id from the recommendation
            scholarship_id = rec.get('scholarship_id')
            match_score = rec['match_score']
            
            # Find the original scholarship posting using scholarship_id
            if scholarship_id in scholarship_lookup:
                # Create a recommendation object with the match score and original posting
                recommendation = {
                    "match_score": round(match_score, 2),
                    "scholarship_posting": scholarship_lookup[scholarship_id],
                    "eligibility_factors": ScholarshipMatcher.generate_eligibility_explanation(rec)
                }
                formatted_response["recommendations"].append(recommendation)
        
        return formatted_response

    # New function to generate human-readable explanation of recommendation factors
    def generate_eligibility_explanation(recommendation):
        """Generate human-readable explanation for why this scholarship was recommended"""
        # This would normally use data from the matcher, but we'll simulate it
        match_score = recommendation['match_score']
        
        # Generate different explanations based on the match score
        if match_score > 85:
            return {
                "primary_factors": [
                    "Strong eligibility match with your profile",
                    "Academic background directly aligned with scholarship focus",
                    "Skills and qualifications meet all requirements"
                ],
                "eligibility_level": "Excellent Match",
                "deadline_approaching": recommendation.get('deadline_approaching', False)
            }
        elif match_score > 70:
            return {
                "primary_factors": [
                    "Good overall match with eligibility criteria",
                    "Academic background relevant to scholarship",
                    "Most key requirements satisfied by your profile"
                ],
                "eligibility_level": "Good Match",
                "deadline_approaching": recommendation.get('deadline_approaching', False)
            }
        else:
            return {
                "primary_factors": [
                    "Partial match with eligibility requirements",
                    "Some relevant academic or skill background",
                    "Potential development opportunity in your field"
                ],
                "eligibility_level": "Potential Match",
                "deadline_approaching": recommendation.get('deadline_approaching', False)
            }

    # Main function to run the scholarship matching process
    def run_scholarship_matching(profile_data, scholarship_postings_data, top_n=5, return_json=False):
        # Load data
        
        # Transform scholarship postings to the required format, passing scholarship_id
        transformed_scholarships, scholarship_id_map = ScholarshipMatcher.transform_scholarship_postings(scholarship_postings_data, return_id_map=True)
        
        # Initialize the scholarship matcher
        matcher = ScholarshipMatcher(debug=True)
        
        # Get recommendations
        recommendations = matcher.get_recommendations(profile_data, transformed_scholarships, top_n)
        
        # Add scholarship_id to each recommendation using the scholarship_id_map
        for rec in recommendations:
            scholarship_title = rec['scholarship_title']
            rec['scholarship_id'] = scholarship_id_map.get(scholarship_title)
            
            # Check if deadline is approaching (within 30 days)
            for scholarship in scholarship_postings_data.get('scholarship_postings', []):
                if scholarship.get('scholarship_id') == rec['scholarship_id']:
                    try:
                        from datetime import datetime
                        expiry_date = scholarship.get('expiration_date')
                        if expiry_date:
                            date_obj = datetime.strptime(expiry_date, '%Y-%m-%d')
                            days_until_expiry = (date_obj - datetime.now()).days
                            rec['deadline_approaching'] = days_until_expiry <= 30
                    except Exception:
                        rec['deadline_approaching'] = False
        
        # Return the appropriate format
        if return_json:
            return ScholarshipMatcher.format_recommendations_for_frontend(recommendations, scholarship_postings_data)
        else:
            return recommendations