from app import db
# Base class with a generic `to_dict` method
class BaseModel(db.Model):
    __abstract__ = True  # Makes this class abstract so SQLAlchemy doesn't create a table for it

    def to_dict(self):
        """Convert the model instance into a dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
