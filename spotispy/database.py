from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from spotispy.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    token_info = Column(JSON)
    user_info = Column(JSON)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
