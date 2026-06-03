import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typing import Generator

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/regradar'
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check if connections are alive
    pool_size = 10,  # Adjust pool size as needed
    max_overflow = 20,  # Allow temporary connections beyond pool size
    echo = False,  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()