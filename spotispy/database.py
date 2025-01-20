from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from spotispy.config import DATABASE_URL

# Set up SQLAlchemy database connection
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define SQLAlchemy base class
Base = declarative_base()


# Define the User model
class User(Base):
    """
    SQLAlchemy model for storing user information and tokens.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    token_info = Column(JSON)
    user_info = Column(JSON)


# Create the database tables
Base.metadata.create_all(bind=engine)


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
