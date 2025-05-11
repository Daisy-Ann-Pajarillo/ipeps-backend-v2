import cloudinary
import cloudinary.uploader

def upload_to_cloudinary(file):
    try:
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(file)
        return result['secure_url']
    except Exception as e:
        return None
