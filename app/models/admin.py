from datetime import datetime
from app import db
from sqlalchemy.orm import relationship
from app.models import BaseModel

class Announcement(BaseModel):
    __tablename__ = 'admin_announcement'

    announcement_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('active', 'expired','inactive', name='status_enum_announcement'), nullable=False, default='active')
    expiration_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', back_populates='admin_announcement')