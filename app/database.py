# app/database.py
# This module sets up the SQLAlchemy database connection and session management.
# It defines the Base class for models and a dependency function to get DB sessions.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Synchronous engine for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,      
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
