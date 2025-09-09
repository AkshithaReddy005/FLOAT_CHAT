from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv
from ...domain.entities.argo_measurement import ArgoMeasurement
from ...domain.repositories.measurement_repository import MeasurementRepository

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./floatchat.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ArgoMeasurementModel(Base):
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

def create_tables():
    Base.metadata.create_all(bind=engine)

class SQLiteMeasurementRepository(MeasurementRepository):
    def __init__(self):
        create_tables()
    
    def _get_db(self) -> Session:
        return SessionLocal()
    
    def save_batch(self, measurements: List[ArgoMeasurement]) -> None:
        db = self._get_db()
        try:
            db_measurements = []
            for measurement in measurements:
                db_measurement = ArgoMeasurementModel(**measurement.to_dict())
                db_measurements.append(db_measurement)
            
            db.add_all(db_measurements)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_count(self) -> int:
        db = self._get_db()
        try:
            return db.query(ArgoMeasurementModel).count()
        finally:
            db.close()
    
    def get_unique_float_count(self) -> int:
        db = self._get_db()
        try:
            return db.query(ArgoMeasurementModel.float_id).distinct().count()
        finally:
            db.close()
    
    def get_latest(self) -> Optional[ArgoMeasurement]:
        db = self._get_db()
        try:
            latest = db.query(ArgoMeasurementModel).order_by(ArgoMeasurementModel.created_at.desc()).first()
            if not latest:
                return None
            
            return ArgoMeasurement(
                id=latest.id,
                float_id=latest.float_id,
                latitude=latest.latitude,
                longitude=latest.longitude,
                date=latest.date,
                depth=latest.depth,
                temperature=latest.temperature,
                salinity=latest.salinity,
                pressure=latest.pressure,
                created_at=latest.created_at
            )
        finally:
            db.close()