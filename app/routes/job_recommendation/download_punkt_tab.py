# download_punkt_tab.py
import nltk
import os
import sys

def download_punkt_tab():
    """Download the specific punkt_tab resource needed by the application"""
    print("Downloading punkt_tab resource...")
    
    # Try to download punkt_tab specifically
    try:
        nltk.download('punkt_tab')
        print("Successfully downloaded punkt_tab")
    except Exception as e:
        print(f"Error downloading punkt_tab: {str(e)}")
        
        # Fallback: try to create the directory structure and punkt_tab manually
        try:
            # Get NLTK data path
            nltk_data = nltk.data.path[0]
            print(f"NLTK data path: {nltk_data}")
            
            # Create directory structure
            punkt_tab_dir = os.path.join(nltk_data, 'tokenizers', 'punkt_tab', 'english')
            os.makedirs(punkt_tab_dir, exist_ok=True)
            print(f"Created directory: {punkt_tab_dir}")
            
            # Copy from punkt if available
            punkt_dir = os.path.join(nltk_data, 'tokenizers', 'punkt', 'english')
            if os.path.exists(punkt_dir):
                import shutil
                for file in os.listdir(punkt_dir):
                    if file.endswith('.pickle'):
                        src = os.path.join(punkt_dir, file)
                        dst = os.path.join(punkt_tab_dir, file.replace('punkt', 'punkt_tab'))
                        shutil.copy2(src, dst)
                        print(f"Copied {src} to {dst}")
            
            print("Manual creation of punkt_tab completed")
        except Exception as ex:
            print(f"Manual creation failed: {str(ex)}")
