from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.database import get_db, ArgoMeasurement
from routers import deps

router = APIRouter()

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

@router.post("/query", response_model=QueryResponse)
async def query_data(request: QueryRequest, db: Session = Depends(get_db)):
    """Researcher endpoint to query ARGO data"""
    
    try:
        # Search in vector store for relevant measurements
        search_results = deps.vector_store.search(request.query, n_results=20)
        
        if not search_results['documents']:
            return QueryResponse(
                results=[],
                message="No relevant data found for your query."
            )
        
        # Extract metadata from search results
        results = []
        for metadata in search_results['metadatas'][0]:
            results.append(ArgoMeasurementDict(
                float_id=str(metadata['float_id']),
                latitude=float(metadata['latitude']),
                longitude=float(metadata['longitude']),
                date=str(metadata['date']),
                depth=float(metadata['depth']),
                temperature=float(metadata['temperature']),
                salinity=float(metadata['salinity']),
                pressure=float(metadata['pressure'])
            ))
        
        # Get the most recent data timestamp
        latest_measurement = db.query(ArgoMeasurement).order_by(ArgoMeasurement.created_at.desc()).first()
        last_update = latest_measurement.created_at if latest_measurement else "No data available"
        
        return QueryResponse(
            results=results,
            message=f"Found {len(results)} relevant measurements. Data current as of {last_update}"
        )
        
    except Exception as e:
        print(f"Query processing error: {e}")
        # Try to provide some recent data as fallback
        try:
            recent_data = db.query(ArgoMeasurement).order_by(ArgoMeasurement.date.desc()).limit(50).all()
            results = []
            for r in recent_data:
                try:
                    results.append(ArgoMeasurementDict(
                        float_id=str(r.float_id),
                        latitude=float(r.latitude) if r.latitude is not None else 0.0,
                        longitude=float(r.longitude) if r.longitude is not None else 0.0,
                        date=str(r.date) if r.date else "",
                        depth=float(r.depth) if r.depth is not None else 0.0,
                        temperature=float(r.temperature) if r.temperature is not None else 0.0,
                        salinity=float(r.salinity) if r.salinity is not None else 0.0,
                        pressure=float(r.pressure) if r.pressure is not None else 0.0
                    ))
                except (ValueError, TypeError):
                    continue
            
            fallback_message = (
                f"I encountered a technical issue while processing your specific query, but I can show you "
                f"some recent ARGO data from our system. Found {len(results)} recent measurements. "
                f"Please try rephrasing your question or asking about specific ocean regions or parameters."
            )
            
            return QueryResponse(
                results=results,
                message=fallback_message
            )
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")
            # Final fallback
            return QueryResponse(
                results=[],
                message=(
                    "I'm experiencing technical difficulties. Our system contains ARGO oceanographic "
                    "measurements including temperature, salinity, depth, and pressure data. "
                    "Please try asking about recent data, specific ocean regions, or what data is available."
                )
            )

@router.post("/download-data")
def download_query_data(request: QueryRequest, db: Session = Depends(get_db)):
    """Download query results as CSV file"""
    try:
        from io import StringIO
        import csv
        from fastapi.responses import StreamingResponse
        
        # Execute the same query logic as the main query endpoint
        from rag_pipeline.unified_query_parser import UnifiedQueryParser
        from rag_pipeline.sql_generator import SQLGenerator
        
        # Parse query parameters
        parser = UnifiedQueryParser()
        parameter_context = parser.parse_query(request.query)
        
        # Generate and execute SQL
        sql_generator = SQLGenerator()
        sql_query = sql_generator.generate_sql_from_context(parameter_context)
        
        # Execute query
        results = db.execute(text(sql_query)).fetchall()
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = ['float_id', 'latitude', 'longitude', 'date', 'depth', 'temperature', 'salinity', 'pressure']
        writer.writerow(headers)
        
        # Write data rows
        for row in results:
            writer.writerow([
                row.float_id,
                row.latitude,
                row.longitude,
                row.date.isoformat() if row.date else '',
                row.depth,
                row.temperature,
                row.salinity,
                row.pressure
            ])
        
        # Prepare response
        output.seek(0)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"argo_data_{timestamp}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download data: {str(e)}")

@router.post("/export/query-csv")
def export_query_csv(request: QueryRequest, db: Session = Depends(get_db)):
    """Export query results as CSV (alternative endpoint)"""
    try:
        from io import StringIO
        import csv
        from fastapi.responses import StreamingResponse
        
        # Execute the same query logic as the main query endpoint
        from rag_pipeline.unified_query_parser import UnifiedQueryParser
        from rag_pipeline.sql_generator import SQLGenerator
        
        # Parse query parameters
        parser = UnifiedQueryParser()
        parameter_context = parser.parse_query(request.query)
        
        # Generate and execute SQL
        sql_generator = SQLGenerator()
        sql_query = sql_generator.generate_sql_from_context(parameter_context)
        
        # Execute query
        results = db.execute(text(sql_query)).fetchall()
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = ['float_id', 'latitude', 'longitude', 'date', 'depth', 'temperature', 'salinity', 'pressure']
        writer.writerow(headers)
        
        # Write data rows
        for row in results:
            writer.writerow([
                row.float_id,
                row.latitude,
                row.longitude,
                row.date.isoformat() if row.date else '',
                row.depth,
                row.temperature,
                row.salinity,
                row.pressure
            ])
        
        # Prepare response
        output.seek(0)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"argo_data_{timestamp}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")

@router.get("/export-chat/{session_id}")
def export_chat_session(session_id: str):
    """Export chat session as JSON file"""
    try:
        from fastapi.responses import StreamingResponse
        import json
        from datetime import datetime
        
        # For now, we'll create a basic export structure
        # In a full implementation, you'd retrieve actual session data from storage
        chat_export = {
            "session_id": session_id,
            "export_timestamp": datetime.now().isoformat(),
            "queries": [
                # This would be populated from actual session storage
                {
                    "timestamp": datetime.now().isoformat(),
                    "query": "Sample query for export",
                    "results_count": 0,
                    "parameters_extracted": {},
                    "visualization_type": "table"
                }
            ],
            "metadata": {
                "total_queries": 0,
                "session_duration": "0 minutes",
                "data_sources": ["PostgreSQL", "ChromaDB"]
            }
        }
        
        # Convert to JSON string
        json_content = json.dumps(chat_export, indent=2)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"floatchat_session_{session_id}_{timestamp}.json"
        
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export chat: {str(e)}")
