# training_matcher.py - Enhanced for training recommendation system
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

class TrainingMatcher:
    def __init__(self, debug=True):
        """Initialize the enhanced training matcher with advanced text processing tools"""
        nltk.download('stopwords', quiet=True)
        nltk.download('punkt', quiet=True)
        nltk.download('wordnet', quiet=True)
        
        self.debug = debug
        self.stemmer = SnowballStemmer("english")
        
        # Define domain-specific stopwords (adapted for training context)
        self.domain_stopwords = [
            'training', 'program', 'course', 'workshop', 'seminar', 'certificate',
            'skills', 'requirements', 'qualifications', 'apply', 'candidate', 
            'company', 'organization', 'we offer', 'required', 'preferred',
            'please', 'submit', 'application'
        ]
        
        # Custom TF-IDF vectorizer with enhanced parameters
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),  # Capture contextual phrases
            max_features=7500,   # Increased to capture more features
            stop_words='english',
            min_df=2,            # Require terms to appear in at least 2 documents
            use_idf=True,
            sublinear_tf=True    # Apply sublinear scaling to reduce impact of high frequencies
        )
        
        # Define skill categories for semantic clustering (adapted for training)
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
            'culinary': ['cooking', 'chef', 'cuisine', 'baking', 'pastry', 'food preparation',
                        'kitchen', 'restaurant', 'catering', 'menu planning', 'food service'],
            'languages': ['english', 'spanish', 'french', 'german', 'italian', 'russian',
                        'chinese', 'japanese', 'arabic', 'portuguese', 'translation', 'interpreter'],
            'soft_skills': ['communication', 'teamwork', 'collaboration', 'problem solving', 
                          'critical thinking', 'time management', 'organization'],
            'healthcare': ['nursing', 'medical', 'patient care', 'healthcare', 'clinical',
                          'therapy', 'healthcare management', 'medical coding', 'pharmacy']
        }
        
        # Initialize recency weighting parameters
        self.time_decay_lambda = 0.05  # Controls the decay rate
        self.max_recency_boost = 1.5   # Maximum boost for very recent experience
        
        # Section importance weights (adapted for training)
        self.section_weights = {
            'training_title': 3.0,
            'description': 2.5,
            'employer': 1.0,
            'training_details': 1.5
        }
        
        # Skill rarity index (will be populated during processing)
        self.skill_rarity_index = {}
        
        # New: Skill gap threshold for training recommendations
        self.skill_gap_threshold = 0.3
        
    def extract_key_terms(self, text):
        """Extract potential skill terms from text"""
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
        
    def build_skill_rarity_index(self, training_descriptions):
        """Build an index of skill term rarity across training postings"""
        # Extract all potential skill terms from all training descriptions
        all_training_terms = []
        for desc in training_descriptions:
            terms = self.extract_key_terms(desc)
            all_training_terms.extend(terms)
        
        # Count term frequencies
        term_counts = Counter(all_training_terms)
        
        # Calculate inverse frequency (rarity) for each term
        total_trainings = len(training_descriptions)
        for term, count in term_counts.items():
            # More rare terms get higher weights
            self.skill_rarity_index[term] = np.log(total_trainings / (count + 1)) + 1
    
    def get_semantic_cluster_weight(self, term):
        """Get the semantic cluster weight for a term"""
        for cluster, terms in self.skill_clusters.items():
            if any(skill_term in term for skill_term in terms):
                return 1.2  # Boost terms that are part of a skill cluster
        return 1.0
    
    def calculate_recency_weight(self, term, profile_data):
        """Calculate recency weight based on work experience"""
        # Default weight
        recency_weight = 1.0
        
        # Check work experience for this term
        try:
            work_exp = profile_data.get('work_experience', [])
            
            # Check training history as well (new for training matcher)
            other_training = profile_data.get('other_training', [])
            
            # Initialize variables to track the most recent mention
            most_recent_date = None
            
            # Check work experience
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
            
            # Check training history (new for training matcher)
            for training in other_training:
                course_name = training.get('course_name', '').lower()
                skills_acquired = training.get('skills_acquired', '').lower()
                
                if term in course_name or term in skills_acquired:
                    # Parse the completion date
                    completion_date = training.get('completion_date', None)
                    
                    if completion_date:
                        try:
                            date_obj = datetime.strptime(completion_date, '%Y-%m-%d')
                            
                            # Update most recent date if this is more recent
                            if most_recent_date is None or date_obj > most_recent_date:
                                most_recent_date = date_obj
                        except:
                            # If date parsing fails, continue to the next training
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

    def calculate_section_weight(self, term, section):
        """Calculate weight based on term position in document"""
        for section_name, weight in self.section_weights.items():
            if section_name in section.lower():
                return weight
        return 1.0

    def preprocess_text(self, text):
        """Enhanced text preprocessing"""
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
        """Extract weighted features from profile with enhanced weighting"""
        try:
            # Create structured feature sections for position-based weighting
            feature_sections = {}
            
            # Education (weight: 2.5x) 
            education = profile_data.get('educational_background', [])
            education_text = " ".join([
                f"{edu.get('degree_or_qualification', '')} {edu.get('field_of_study', '')}"
                for edu in education
            ])
            feature_sections['education'] = education_text
            
            # Skills (weight: 4x)
            skills = profile_data.get('other_skills', [])
            skills_text = " ".join([
                skill.get('skills', '') for skill in skills
            ])
            feature_sections['skills'] = skills_text
            
            # Work Experience (weight: 3.5x)
            work_exp = profile_data.get('work_experience', [])
            work_text = " ".join([
                f"{exp.get('position', '')} {exp.get('company_name', '')}"
                for exp in work_exp
            ])
            feature_sections['work_experience'] = work_text
            
            # Training (weight: 4.0x) - increased for training matcher
            training = profile_data.get('other_training', [])
            training_text = " ".join([
                f"{t.get('course_name', '')} {t.get('skills_acquired', '')}"
                for t in training
            ])
            feature_sections['training'] = training_text
            
            # Preprocess each section
            processed_sections = {
                section: self.preprocess_text(text)
                for section, text in feature_sections.items()
            }
            
            # Apply section weights (adjusted for training focus)
            weighted_sections = {
                'education': processed_sections['education'] * int(2.5),
                'skills': processed_sections['skills'] * int(4.0),
                'work_experience': processed_sections['work_experience'] * int(3.0),
                'training': processed_sections['training'] * int(4.0)  # Higher weight for training
            }
            
            # Combine all weighted sections
            combined_text = " ".join(weighted_sections.values())
            
            return combined_text
            
        except Exception as e:
            print(f"Error extracting profile features: {str(e)}")
            raise
    
    def process_training_postings(self, training_posts):
        """Process training posts with section-based weighting"""
        processed_trainings = {}
        
        for title, description in training_posts.items():
            # Split description into sections (if possible)
            sections = {}
            
            # Extract training title section
            sections['training_title'] = title
            
            # Basic section extraction using regex
            section_pattern = r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)'
            matches = re.findall(section_pattern, description, re.DOTALL)
            
            for section_name, content in matches:
                sections[section_name.lower()] = content.strip()
            
            # If no sections found, use the entire description
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
            
            processed_trainings[title] = weighted_text.strip()
        
        return processed_trainings
    
    def calculate_skill_gap_opportunity(self, profile_features, training_features, feature_names):
        """Calculate skill gap opportunity score for training recommendations"""
        # Extract profile and training terms
        profile_terms = set(profile_features.split())
        
        # Initialize skill gap opportunity scores
        skill_gap_scores = {}
        
        # For each training, identify skills the user doesn't have
        for training_title, training_text in training_features.items():
            training_terms = set(training_text.split())
            
            # Find potential skill terms in training that are not in profile
            new_skills = training_terms - profile_terms
            
            # Calculate opportunity score for training
            opportunity_score = 0
            relevant_skills = []
            
            for term in new_skills:
                # Higher score for rarer skills
                if term in feature_names:
                    rarity_factor = self.skill_rarity_index.get(term, 1.0)
                    cluster_weight = self.get_semantic_cluster_weight(term)
                    term_score = rarity_factor * cluster_weight
                    opportunity_score += term_score
                    
                    # Track relevant skills for explanation
                    if term_score > 1.2:  # Only include significant skills
                        relevant_skills.append(term)
            
            # Normalize by the number of new skills
            if len(new_skills) > 0:
                opportunity_score = opportunity_score / len(new_skills)
            
            skill_gap_scores[training_title] = {
                'score': opportunity_score,
                'new_skills': list(new_skills)[:5],  # Limit to top 5 skills
                'relevant_skills': relevant_skills[:3]  # Limit to top 3 relevant skills
            }
        
        return skill_gap_scores
    
    def get_recommendations(self, profile_data, training_posts, top_n=5):
        """Get training recommendations with novelty enhancements"""
        try:
            # Process profile with enhanced feature extraction
            profile_features = self.extract_profile_features(profile_data)
            
            # Process training posts with section-based weighting
            processed_trainings = self.process_training_postings(training_posts)
            
            # Build skill rarity index
            self.build_skill_rarity_index(list(processed_trainings.values()))
            
            # Combine all texts for vectorization
            all_texts = list(processed_trainings.values()) + [profile_features]
            
            # Create TF-IDF matrix with enhanced vectorizer
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Get feature names for semantic analysis
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Calculate skill gap opportunity (new for training recommendations)
            skill_gap_opportunities = self.calculate_skill_gap_opportunity(
                profile_features,
                {t: processed_trainings[t] for t in processed_trainings.keys()},
                feature_names
            )
            
            # Apply semantic clustering and recency weighting
            profile_vector = tfidf_matrix[-1:].toarray()[0]
            training_vectors = tfidf_matrix[:-1].toarray()
            
            # Initialize match scores array
            match_scores = np.zeros(len(training_vectors))
            
            # Get list of training titles for indexing
            training_titles = list(processed_trainings.keys())
            
            # Calculate enhanced similarity with multiple factors
            for i, training_vector in enumerate(training_vectors):
                # Basic cosine similarity
                dot_product = np.dot(profile_vector, training_vector)
                profile_norm = np.linalg.norm(profile_vector)
                training_norm = np.linalg.norm(training_vector)
                
                if profile_norm > 0 and training_norm > 0:
                    base_similarity = dot_product / (profile_norm * training_norm)
                else:
                    base_similarity = 0
                
                # Get current training title
                training_title = training_titles[i]
                
                # Apply skill gap opportunity boost (new for training)
                skill_gap_info = skill_gap_opportunities.get(training_title, {'score': 0})
                skill_gap_boost = skill_gap_info['score'] * self.skill_gap_threshold
                
                # Apply semantic clustering boost
                semantic_boost = 1.0
                boost_count = 0
                
                for term_idx, term in enumerate(feature_names):
                    if training_vector[term_idx] > 0 and profile_vector[term_idx] > 0:
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
                base_score = base_similarity * 100  # Scale to percentage-like values
                boosted_score = base_score * semantic_boost  # Apply semantic boost
                
                # Add skill gap opportunity boost - this is a key difference for training recommendations
                # We want to recommend trainings that fill skill gaps
                final_score = boosted_score + (skill_gap_boost * 10)  # Apply skill gap boost
                
                match_scores[i] = final_score
            
            # Create training-score pairs
            training_titles = list(processed_trainings.keys())
            training_scores = list(zip(training_titles, match_scores))
            
            # Sort by score and get top recommendations
            recommendations = sorted(training_scores, key=lambda x: x[1], reverse=True)[:top_n]
            
            # Format recommendations with detailed scores
            detailed_recommendations = []
            for training_title, score in recommendations:
                # Get skill gap information
                skill_gap_info = skill_gap_opportunities.get(training_title, {})
                
                # Ensure scores are positive and capped at 100
                match_percentage = min(100, max(0, score))
                recommendation = {
                    'training_title': training_title,
                    'match_score': match_percentage,
                    'training_description': training_posts[training_title],
                    'skill_gap_opportunity': skill_gap_info.get('score', 0),
                    'new_skills': skill_gap_info.get('new_skills', []),
                    'relevant_skills': skill_gap_info.get('relevant_skills', [])
                }
                detailed_recommendations.append(recommendation)
                
                if self.debug:
                    print(f"\nTraining: {training_title}")
                    print(f"Match Score: {match_percentage:.1f}%")
            
            return detailed_recommendations
            
        except Exception as e:
            print(f"Error getting recommendations: {str(e)}")
            raise
# # transform_training_postings.py - Transforms training postings for recommendation system
# import json
# import re
# from datetime import datetime

    def transform_training_postings(input_json, return_id_map=False):
        # Initialize the output dictionary
        transformed_trainings = {}
        # Initialize training_id mapping dictionary
        training_id_map = {}
        
        # Process each training posting
        for training in input_json.get('training_postings', []):
            training_title = training.get('training_title', 'Unknown Training')
            training_id = training.get('training_id')
            
            # Create a structured training description with clear sections
            description_parts = {}
            
            # Add TRAINING_TITLE section (for position-based weighting)
            description_parts['training_title'] = training_title
            
            # Add the base training description
            if training.get('training_description'):
                description_parts['description'] = training.get('training_description')
            
            # Add training details
            training_details = []
            training_details.append(f"Training: {training_title}")
            
            if training.get('status'):
                training_details.append(f"Status: {training.get('status')}")
            
            # Add training details to a dedicated section
            description_parts['training_details'] = "\n".join(training_details)
            
            # Extract employer information
            employer_info = []
            if training.get('employer'):
                employer = training.get('employer')
                
                if employer.get('company_name'):
                    employer_info.append(f"Company: {employer.get('company_name')}")
                
                if employer.get('company_description'):
                    employer_info.append(f"Company Description: {employer.get('company_description')}")
                
                if employer.get('email'):
                    employer_info.append(f"Contact: {employer.get('email')}")
                    
                if employer.get('contact_number'):
                    employer_info.append(f"Phone: {employer.get('contact_number')}")
                    
                if employer.get('website'):
                    employer_info.append(f"Website: {employer.get('website')}")
                    
                if employer.get('address'):
                    employer_info.append(f"Address: {employer.get('address')}")
            
            if employer_info:
                description_parts['employer'] = "\n".join(employer_info)
            
            # Extract posting date for recency calculations
            created_date = training.get('created_at', '')
            if created_date:
                try:
                    date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    description_parts['posting_date'] = f"Posted: {date_obj.strftime('%Y-%m-%d')}"
                except (ValueError, TypeError):
                    # If date parsing fails, just use the string as-is
                    description_parts['posting_date'] = f"Posted: {created_date[:10]}"
            
            # Extract expiration date
            expiration_date = training.get('expiration_date', '')
            if expiration_date:
                try:
                    date_obj = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
                    description_parts['expiration_date'] = f"Expires: {date_obj.strftime('%Y-%m-%d')}"
                except (ValueError, TypeError):
                    # If date parsing fails, just use the string as-is
                    description_parts['expiration_date'] = f"Expires: {expiration_date[:10]}"
            
            # Build the final structured description
            full_description = ""
            section_order = ['training_title', 'description', 'training_details', 
                            'employer', 'posting_date', 'expiration_date']
            
            for section in section_order:
                if section in description_parts:
                    # Add section header for better parsing in the matcher
                    if section != 'training_title':  # Don't add a header for the title
                        full_description += f"\n\n[SECTION:{section.upper()}]\n"
                    full_description += description_parts[section]
            
            # Add to the transformed trainings dictionary
            # If there are duplicate training titles, make them unique by appending creation timestamp
            unique_training_title = training_title
            if training_title in transformed_trainings:
                unique_id = training.get('created_at', '')[:10]  # Get date part of timestamp
                unique_training_title = f"{training_title} ({unique_id})"
            
            transformed_trainings[unique_training_title] = full_description.strip()
            
            # Store the mapping between the (possibly modified) training title and the training_id
            if training_id is not None:
                training_id_map[unique_training_title] = training_id
        
        if return_id_map:
            return transformed_trainings, training_id_map
        else:
            return transformed_trainings

    # Helper function to extract sections from transformed training descriptions
    def extract_training_sections(training_description):
        """Extract structured sections from a training description for section-based analysis"""
        sections = {}
        
        # Extract sections using regex pattern matching
        section_pattern = r'\[SECTION:([A-Z_]+)\](.*?)(?=\[SECTION:|$)'
        matches = re.findall(section_pattern, training_description, re.DOTALL)
        
        # Process each found section
        for section_name, content in matches:
            sections[section_name.lower()] = content.strip()
        
        # Extract the training title (which appears before any section markers)
        title_match = re.match(r'^(.*?)(?=\[SECTION:|$)', training_description, re.DOTALL)
        if title_match:
            sections['training_title'] = title_match.group(1).strip()
        
        return sections

    # run_training_matching.py - Script to run training recommendation process
    import json

    # Load the training postings
    def load_training_postings(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    # Load profile data
    def load_profile(filename):
        with open(filename, 'r') as f:
            return json.load(f)

    def format_recommendations_for_frontend(recommendations, original_training_postings_json):
        # Create a lookup dictionary for the original training postings using training_id
        training_lookup = {}
        for training in original_training_postings_json.get('training_postings', []):
            training_id = training.get('training_id')
            if training_id is not None:
                training_lookup[training_id] = training
        
        # Format the response
        formatted_response = {
            "success": True,
            "recommendations": []
        }
        
        for rec in recommendations:
            # Extract the training_id from the recommendation
            training_id = rec.get('training_id')
            match_score = rec['match_score']
            
            # Find the original training posting using training_id
            if training_id in training_lookup:
                # Create a recommendation object with the match score and original posting
                recommendation = {
                    "match_score": round(match_score, 2),
                    "training_posting": training_lookup[training_id],
                    "recommendation_factors": TrainingMatcher.generate_recommendation_explanation(rec)
                }
                formatted_response["recommendations"].append(recommendation)
        
        return formatted_response

    # Generate human-readable explanation of recommendation factors
    def generate_recommendation_explanation(recommendation):
        """Generate human-readable explanation for why this training was recommended"""
        match_score = recommendation['match_score']
        skill_gap = recommendation.get('skill_gap_opportunity', 0)
        new_skills = recommendation.get('new_skills', [])
        relevant_skills = recommendation.get('relevant_skills', [])
        
        # Generate different explanations based on the match score and skill gap
        if match_score > 85:
            primary_factors = [
                "Strong skills alignment with your profile",
                "Builds on your existing expertise",
                "Highly relevant to your career trajectory"
            ]
            skill_alignment = "Very High"
        elif match_score > 70:
            primary_factors = [
                "Good match with your current skillset",
                "Enhances your professional profile",
                "Relevant to your background"
            ]
            skill_alignment = "High"
        else:
            primary_factors = [
                "Provides complementary skills to your profile",
                "Moderate alignment with your experience",
                "Offers knowledge expansion opportunities"
            ]
            skill_alignment = "Moderate"
        
        # Add skill gap opportunities if they exist
        if skill_gap > 0.5 and new_skills:
            skill_development = "High"
            opportunity_factors = [
                f"Learn {', '.join(new_skills[:2])} and more" if len(new_skills) > 2 else f"Learn {', '.join(new_skills)}",
                "Addresses identified skill gaps in your profile",
                "High potential for career advancement"
            ]
        elif skill_gap > 0.2 and new_skills:
            skill_development = "Medium"
            opportunity_factors = [
                f"Develop skills in {', '.join(new_skills[:2])}" if len(new_skills) > 2 else f"Develop skills in {', '.join(new_skills)}",
                "Moderate skill development opportunity",
                "Useful addition to your qualification set"
            ]
        else:
            skill_development = "Low"
            opportunity_factors = [
                "Reinforces your existing skillset",
                "Certification opportunity for skills you already have",
                "Formal recognition of your capabilities"
            ]
        
        return {
            "primary_factors": primary_factors,
            "opportunity_factors": opportunity_factors,
            "skill_alignment": skill_alignment,
            "skill_development": skill_development,
            "key_skills": relevant_skills if relevant_skills else new_skills[:3]
        }

    # Main function to run the training matching process
    def run_training_matching(profile_json, training_postings_json, top_n=5, return_json=False):
        # # Load data
        # profile_data = load_profile(profile_file)
        # training_postings_json = load_training_postings(training_postings_file)
        
        # Transform training postings to the required format, passing training_id
        transformed_trainings, training_id_map = TrainingMatcher.transform_training_postings(training_postings_json, return_id_map=True)
        
        # Initialize the enhanced training matcher
        matcher = TrainingMatcher(debug=True)
        
        # Get recommendations
        recommendations = matcher.get_recommendations(profile_json, transformed_trainings, top_n)
        
        # Add training_id to each recommendation using the training_id_map
        for rec in recommendations:
            training_title = rec['training_title']
            rec['training_id'] = training_id_map.get(training_title)
        
        # Return the appropriate format
        if return_json:
            return TrainingMatcher.format_recommendations_for_frontend(recommendations, training_postings_json)
        else:
            return recommendations