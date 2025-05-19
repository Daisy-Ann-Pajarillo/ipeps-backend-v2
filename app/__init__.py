from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.config import Config
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import logging

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
app = Flask(__name__)

def create_app():
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Enable CORS for your frontend domain with all headers and methods
    CORS(
        app,
        origins=[
            "https://ipeps-peso-v1.onrender.com",
            "http://localhost:3000"
        ],
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # from app.routes.recommendations.download_nltk_resources import download_nltk_resources
    # from app.routes.recommendations.download_punkt_tab import download_punkt_tab
    from app.routes import user_application_form, employer, student_jobseeker, main_bp, academe, recommendation, admin
    
    # download_punkt_tab()
    # download_nltk_resources()
    
    app.register_blueprint(main_bp, url_prefix='/api')
    app.register_blueprint(user_application_form, url_prefix='/api')
    app.register_blueprint(employer, url_prefix='/api')
    app.register_blueprint(student_jobseeker, url_prefix='/api')
    app.register_blueprint(academe, url_prefix='/api')
    app.register_blueprint(recommendation, url_prefix='/api')
    app.register_blueprint(admin, url_prefix='/api')

    # Logging configuration
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
        handler = logging.StreamHandler()
        file_handler = logging.FileHandler('app.log')
        
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        
        handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        app.logger.addHandler(handler)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('IPEPS Backend')
    
    return app
