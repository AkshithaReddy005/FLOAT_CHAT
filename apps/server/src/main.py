from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import tempfile
import time
from typing import List
from dotenv import load_dotenv

from database import get_db, create_tables, ArgoMeasurement
from vector_store import VectorStore
from netcdf_processor import NetCDFProcessor

# Load environment variables
load_dotenv()

app = FastAPI(title="FloatChat ARGO Data System")

# Get environment variables
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5432")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Frontend servers
        f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",
        f"http://127.0.0.1:{FRONTEND_PORT}",
        # Keep for backward compatibility during development
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://localhost:3000",
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174", 
        "http://127.0.0.1:3000",
        # API server itself for any internal calls
        f"http://{BACKEND_HOST}:{BACKEND_PORT}",
        f"http://127.0.0.1:{BACKEND_PORT}"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# Initialize components
vector_store = VectorStore()

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

@app.on_event("startup")
def startup_event():
    create_tables()

@app.get("/")
def read_root():
    return {"message": "FloatChat ARGO Data System API"}

@app.post("/admin/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Admin endpoint to upload ARGO NetCDF files"""
    
    temp_file_path = None
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(('.nc', '.netcdf')):
            raise HTTPException(status_code=400, detail="Invalid file format. Only NetCDF files are allowed.")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()  # Ensure data is written to disk
            temp_file_path = temp_file.name
        
        # Validate NetCDF file
        if not NetCDFProcessor.validate_file(temp_file_path):
            raise HTTPException(status_code=400, detail="Invalid NetCDF file format.")
        
        # Process the file
        measurements = NetCDFProcessor.process_argo_file(temp_file_path)
        
        if not measurements:
            raise HTTPException(status_code=400, detail="No valid measurements found in file.")
        
        # Store in PostgreSQL
        db_measurements = []
        for measurement in measurements:
            db_measurement = ArgoMeasurement(**measurement)
            db_measurements.append(db_measurement)
        
        db.add_all(db_measurements)
        db.commit()
        
        # Store in ChromaDB
        vector_store.add_measurements(measurements)
        
        return {
            "message": f"Successfully processed {len(measurements)} measurements",
            "measurements_count": len(measurements),
            "status": "completed"
        }
            
    except HTTPException:
        # Re-raise HTTP exceptions
        if temp_file_path:
            _safe_delete_file(temp_file_path)
        raise
    except Exception as e:
        # Rollback database changes on error
        db.rollback()
        if temp_file_path:
            _safe_delete_file(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path:
            _safe_delete_file(temp_file_path)

def _safe_delete_file(file_path: str, max_attempts: int = 5, delay: float = 0.1):
    """Safely delete a file with retry logic for Windows file locking issues"""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
            return
        except PermissionError:
            if attempt < max_attempts - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                # Log the error but don't fail the entire operation
                print(f"Warning: Could not delete temporary file {file_path} after {max_attempts} attempts")
        except Exception as e:
            print(f"Warning: Error deleting temporary file {file_path}: {e}")
            return

@app.post("/researcher/query", response_model=QueryResponse)
async def query_data(request: QueryRequest, db: Session = Depends(get_db)):
    """Researcher endpoint to query ARGO data"""
    
    try:
        # Search in vector store for relevant measurements
        search_results = vector_store.search(request.query, n_results=20)
        
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
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/admin/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics for admin"""
    total_measurements = db.query(ArgoMeasurement).count()
    unique_floats = db.query(ArgoMeasurement.float_id).distinct().count()
    
    return {
        "total_measurements": total_measurements,
        "unique_floats": unique_floats,
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)