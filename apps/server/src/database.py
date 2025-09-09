from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./floatchat.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ArgoMeasurement(Base):
    __tablename__ = "argo_measurements"
    
    id = Column(Integer, primary_key=True, index=True)
    float_id = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    date = Column(DateTime)
    depth = Column(Float)
    temperature = Column(Float)
    salinity = Column(Float)
    pressure = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)