import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database

# PostgreSQL Database URL - can be set via environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/mydatabase")

# SQLAlchemy specific settings
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Use this for synchronous operations (optional if using async)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the base class for SQLAlchemy models
Base = declarative_base()

# Async database connection
db = Database(DATABASE_URL)

# Dependency for getting the database session (sync mode)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for async database connection
async def get_async_db():
    try:
        await db.connect()
        yield db
    finally:
        await db.disconnect()
