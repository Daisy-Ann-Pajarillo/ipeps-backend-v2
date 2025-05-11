import os
import cloudinary
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # cloudinary.config( 
    #     cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    #     api_key = os.getenv("CLOUDINARY_API_KEY"), 
    #     api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    #     secure=True
    # )