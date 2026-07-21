"""
Shared Pydantic models used across all routers.
"""
from pydantic import BaseModel
from typing import List, Optional


class QueryRequest(BaseModel):
    query: str


class ArgoMeasurementDict(BaseModel):
    float_id: str
    latitude: float
    longitude: float
    date: str
    depth: float
    temperature: float
    salinity: float
    pressure: float


class QueryResponse(BaseModel):
    results: List[ArgoMeasurementDict]
    message: str


class ChatRequest(BaseModel):
    message: str
    session_context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    data: List[ArgoMeasurementDict]
    visualization: dict
    pipeline_flow: Optional[dict] = None
    query_params: dict
    context_count: int


class SessionResetRequest(BaseModel):
    session_id: Optional[str] = None


class SessionResetResponse(BaseModel):
    success: bool
    message: str
