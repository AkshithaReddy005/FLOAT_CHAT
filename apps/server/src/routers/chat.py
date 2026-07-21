from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time

from database.database import get_db, ArgoMeasurement
from routers import deps

router = APIRouter()

class ArgoMeasurementDict(BaseModel):
    float_id: str
    latitude: float
    longitude: float
    date: str
    depth: float
    temperature: float
    salinity: float
    pressure: float

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

@router.post("/chat", response_model=ChatResponse)
async def chat_with_data(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat endpoint for natural language queries about ARGO data"""
    
    try:
        # Process the chat query using the chatbot service with context
        result = await deps.chatbot_service.process_chat_query(request.message, db, request.session_context)
        
        # Convert data to ArgoMeasurementDict format for consistency
        data_dicts = []
        for item in result["data"]:
            try:
                data_dicts.append(ArgoMeasurementDict(
                    float_id=str(item["float_id"]),
                    latitude=float(item["latitude"]) if item["latitude"] is not None else 0.0,
                    longitude=float(item["longitude"]) if item["longitude"] is not None else 0.0,
                    date=str(item["date"]) if item["date"] else "",
                    depth=float(item["depth"]) if item["depth"] is not None else 0.0,
                    temperature=float(item["temperature"]) if item["temperature"] is not None else 0.0,
                    salinity=float(item["salinity"]) if item["salinity"] is not None else 0.0,
                    pressure=float(item["pressure"]) if item["pressure"] is not None else 0.0
                ))
            except (ValueError, TypeError) as e:
                # Skip invalid data points but continue processing
                print(f"Skipping invalid data point: {e}")
                continue
        
        return ChatResponse(
            response=result["response"],
            data=data_dicts,
            visualization=result["visualization"],
            pipeline_flow=result.get("pipeline_flow"),
            query_params=result["query_params"],
            context_count=result["context_count"]
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        # Instead of raising an exception, provide a fallback response
        try:
            # Try to get some basic data as fallback
            fallback_result = await deps.chatbot_service.create_fallback_response(request.message, db)
            return ChatResponse(
                response=fallback_result["response"],
                data=fallback_result["data"],
                visualization=fallback_result["visualization"],
                query_params=fallback_result["query_params"],
                context_count=fallback_result["context_count"]
            )
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            # Final safety net - always return something useful
            return ChatResponse(
                response=("I'm having some technical difficulties, but I can still help you explore ARGO data! "
                         "The system contains oceanographic measurements including temperature, salinity, and depth data "
                         "from ARGO floats across various ocean regions. You can try asking about specific locations, "
                         "recent measurements, or data comparisons. I'm working to resolve the technical issue."),
                data=[],
                visualization={"map": {"points": []}, "depth_profile": {"data": []}},
                query_params={"classification": {"needs_data": False}, "sql_used": None, 
                            "context_retrieved": 0, "data_points": 0},
                context_count=0
            )

@router.post("/session/reset", response_model=SessionResetResponse)
async def reset_session(request: SessionResetRequest):
    """Reset session context to prevent AI hallucination"""
    try:
        # Clear any server-side cached session context if it exists
        # For now, since session context is client-managed, we just confirm reset

        # Reset the chatbot service's internal state if needed
        await deps.chatbot_service.reset_session_context(request.session_id)

        return SessionResetResponse(
            success=True,
            message="Session context successfully reset. All previous conversation context has been cleared."
        )
    except Exception as e:
        print(f"Error resetting session: {e}")
        return SessionResetResponse(
            success=False,
            message=f"Failed to reset session: {str(e)}"
        )

@router.get("/examples")
def get_example_queries(db: Session = Depends(get_db)):
    """Get dynamic example queries based on available data"""
    try:
        examples = deps.example_generator.generate_dynamic_examples(db, max_examples=6)
        return {
            "examples": examples,
            "generated_at": time.time(),
            "status": "success"
        }
    except Exception as e:
        # Return fallback examples on error
        fallback_examples = deps.example_generator._get_fallback_examples()
        return {
            "examples": fallback_examples,
            "generated_at": time.time(),
            "status": "fallback",
            "error": str(e)
        }
