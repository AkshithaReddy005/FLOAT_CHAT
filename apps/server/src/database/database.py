from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://username:pass@localhost:5432/db_name")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, unique=True, nullable=False, index=True)
    file_size = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    measurements_count = Column(Integer, default=0)

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
    file_hash = Column(String, index=True)  # Link to source file
    measurement_hash = Column(String, unique=True, index=True)  # Unique identifier for this measurement
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Create a unique constraint on the combination of key fields to prevent exact duplicates
    __table_args__ = (
        UniqueConstraint('float_id', 'latitude', 'longitude', 'date', 'depth', name='unique_measurement'),
        Index('idx_location_date', 'latitude', 'longitude', 'date'),
        Index('idx_float_date', 'float_id', 'date'),
    )
    
    @staticmethod
    def generate_measurement_hash(float_id: str, latitude: float, longitude: float, 
                                 date: datetime, depth: float) -> str:
        """Generate a unique hash for a measurement based on key identifying fields"""
        key_string = f"{float_id}_{latitude:.6f}_{longitude:.6f}_{date.isoformat()}_{depth:.2f}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)