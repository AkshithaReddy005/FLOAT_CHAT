from pydantic import BaseModel
from typing import List

class ArgoMeasurementDTO(BaseModel):
    float_id: str
    latitude: float
    longitude: float
    date: str
    depth: float
    temperature: float
    salinity: float
    pressure: float

class UploadResponse(BaseModel):
    message: str
    measurements_count: int
    status: str

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    results: List[ArgoMeasurementDTO]
    message: str

class StatsResponse(BaseModel):
    total_measurements: int
    unique_floats: int
    status: str