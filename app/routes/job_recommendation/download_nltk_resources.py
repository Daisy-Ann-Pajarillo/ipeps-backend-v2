# download_nltk_resources.py
# Run this script once to download all required NLTK resources
import nltk
import os
import sys

def download_nltk_resources():
    """Download all NLTK resources needed for the job matching system"""
    print("Downloading NLTK resources...")
    
    # Create nltk_data directories if they don't exist
    data_dirs = [
        os.path.join(os.path.expanduser('~'), 'nltk_data'),
        os.path.join(os.getcwd(), 'venv', 'nltk_data')
    ]
    
    for directory in data_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created NLTK data directory: {directory}")
    
    # Download required resources
    resources = [
        'punkt',       # For tokenization
        'stopwords',   # For stopword removal
        'wordnet',     # For lemmatization
        'averaged_perceptron_tagger'  # Often needed for POS tagging
    ]
    
    for resource in resources:
        try:
            nltk.download(resource, quiet=False)
            print(f"Successfully downloaded {resource}")
        except Exception as e:
            print(f"Error downloading {resource}: {str(e)}")
    
    # Verify downloads
    print("\nVerifying NLTK resources...")
    
    # Test each resource
    try:
        from nltk.tokenize import word_tokenize
        print(f"Tokenization test: {word_tokenize('This is a test.')}")
        
        from nltk.corpus import stopwords
        stops = stopwords.words('english')
        print(f"Stopwords test: First 5 stopwords: {stops[:5]}")
        
        from nltk.corpus import wordnet
        print(f"Wordnet test: {wordnet.synsets('test')[:1]}")
        
        print("\nAll NLTK resources verified successfully!")
    except Exception as e:
        print(f"Verification failed: {str(e)}")
        print("Please check your NLTK installation and try again.")