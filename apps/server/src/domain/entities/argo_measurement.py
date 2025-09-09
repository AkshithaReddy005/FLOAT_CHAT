from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ArgoMeasurement:
    float_id: str
    latitude: float
    longitude: float
    date: datetime
    depth: float
    temperature: float
    salinity: float
    pressure: float
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'float_id': self.float_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            'depth': self.depth,
            'temperature': self.temperature,
            'salinity': self.salinity,
            'pressure': self.pressure
        }
    
    def to_dto_dict(self) -> dict:
        return {
            'float_id': self.float_id,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'date': self.date.isoformat() if isinstance(self.date, datetime) else str(self.date),
            'depth': float(self.depth),
            'temperature': float(self.temperature),
            'salinity': float(self.salinity),
            'pressure': float(self.pressure)
        }