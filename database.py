# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Example: postgresql+psycopg2://user:password@localhost:5432/snalazljivko
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/snalazljivko"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True, echo=True)
print(">> USING DATABASE_URL =", DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
