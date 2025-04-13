# job_matcher.py - Enhanced with Novelty Features
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

class NoveltyEnhancedJobMatcher:
    def __init__(self, debug=True):
        """Initialize the enhanced job matcher with advanced text processing tools"""
        # Download all required resources explicitly
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        
        # Make sure nltk has the tokenize package
        try:
            from nltk.tokenize import word_tokenize
            word_tokenize("Test tokenization")
        except LookupError:
            # If word_tokenize still fails, download punkt again
            nltk.download('punkt', quiet=False)
            
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
                          'critical thinking', 'time management', 'organization']
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