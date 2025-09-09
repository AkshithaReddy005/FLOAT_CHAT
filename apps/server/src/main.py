from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
import os
import tempfile
import time
import hashlib
from typing import List
from dotenv import load_dotenv

from database import get_db, create_tables, ArgoMeasurement, UploadedFile
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
    """Admin endpoint to upload ARGO NetCDF files with duplicate detection"""
    
    temp_file_path = None
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(('.nc', '.netcdf')):
            raise HTTPException(status_code=400, detail="Invalid file format. Only NetCDF files are allowed.")
        
        # Read file content and calculate hash
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        
        # Check if this exact file has been uploaded before
        existing_file = db.query(UploadedFile).filter(UploadedFile.file_hash == file_hash).first()
        if existing_file:
            return {
                "message": f"File '{file.filename}' has already been uploaded on {existing_file.upload_date}. No new data added.",
                "measurements_count": 0,
                "existing_measurements": existing_file.measurements_count,
                "status": "duplicate_file",
                "original_upload_date": existing_file.upload_date.isoformat()
            }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
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
        
        # Add file hash and measurement hash to each measurement
        for measurement in measurements:
            measurement['file_hash'] = file_hash
            measurement['measurement_hash'] = ArgoMeasurement.generate_measurement_hash(
                measurement['float_id'],
                measurement['latitude'],
                measurement['longitude'],
                measurement['date'],
                measurement['depth']
            )
        
        # Store in PostgreSQL with duplicate detection
        db_measurements = []
        new_measurements_count = 0
        duplicate_measurements_count = 0
        
        for measurement in measurements:
            try:
                # Check if this exact measurement already exists
                existing_measurement = db.query(ArgoMeasurement).filter(
                    ArgoMeasurement.measurement_hash == measurement['measurement_hash']
                ).first()
                
                if existing_measurement:
                    duplicate_measurements_count += 1
                    continue
                
                db_measurement = ArgoMeasurement(**measurement)
                db_measurements.append(db_measurement)
                new_measurements_count += 1
                
            except Exception as e:
                print(f"Error processing measurement: {e}")
                continue
        
        # Add new measurements to database
        if db_measurements:
            try:
                db.add_all(db_measurements)
                db.commit()
            except IntegrityError as e:
                db.rollback()
                # Handle potential race conditions with unique constraints
                print(f"Integrity error (likely duplicate): {e}")
                # Re-count actual new measurements
                new_measurements_count = len([m for m in measurements 
                                            if not db.query(ArgoMeasurement).filter(
                                                ArgoMeasurement.measurement_hash == m['measurement_hash']
                                            ).first()])
        
        # Store in ChromaDB with duplicate detection
        vector_results = vector_store.add_measurements(measurements, file_hash)
        
        # Record the uploaded file
        uploaded_file = UploadedFile(
            filename=file.filename,
            file_hash=file_hash,
            file_size=file_size,
            measurements_count=new_measurements_count
        )
        db.add(uploaded_file)
        db.commit()
        
        # Prepare response message
        total_processed = len(measurements)
        message_parts = [f"Successfully processed {total_processed} measurements from file"]
        
        if new_measurements_count > 0:
            message_parts.append(f"{new_measurements_count} new measurements added")
        
        if duplicate_measurements_count > 0:
            message_parts.append(f"{duplicate_measurements_count} duplicate measurements skipped")
        
        if vector_results.get('duplicates_skipped', 0) > 0:
            message_parts.append(f"{vector_results['duplicates_skipped']} vector duplicates skipped")
        
        return {
            "message": ". ".join(message_parts) + ".",
            "measurements_count": new_measurements_count,
            "duplicate_measurements": duplicate_measurements_count,
            "total_in_file": total_processed,
            "vector_stats": vector_results,
            "status": "completed" if new_measurements_count > 0 else "all_duplicates"
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
    total_files = db.query(UploadedFile).count()
    
    # Get latest upload
    latest_upload = db.query(UploadedFile).order_by(UploadedFile.upload_date.desc()).first()
    
    # Get vector store stats
    vector_stats = vector_store.get_collection_stats()
    
    return {
        "total_measurements": total_measurements,
        "unique_floats": unique_floats,
        "total_files_uploaded": total_files,
        "latest_upload": {
            "filename": latest_upload.filename if latest_upload else None,
            "upload_date": latest_upload.upload_date.isoformat() if latest_upload else None,
            "measurements_count": latest_upload.measurements_count if latest_upload else 0
        } if latest_upload else None,
        "vector_store": vector_stats,
        "status": "active"
    }

@app.get("/admin/files")
def get_uploaded_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of uploaded files for admin monitoring"""
    files = db.query(UploadedFile).order_by(UploadedFile.upload_date.desc()).offset(skip).limit(limit).all()
    
    return {
        "files": [
            {
                "id": file.id,
                "filename": file.filename,
                "file_hash": file.file_hash[:16] + "...",  # Show partial hash for identification
                "file_size": file.file_size,
                "upload_date": file.upload_date.isoformat(),
                "measurements_count": file.measurements_count
            }
            for file in files
        ],
        "total_files": db.query(UploadedFile).count()
    }

@app.delete("/admin/chroma/clear")
def clear_chroma_database():
    """Clear all data from ChromaDB vector store (admin only)"""
    try:
        # Get stats before clearing
        stats_before = vector_store.get_collection_stats()
        measurements_before = stats_before.get('total_measurements', 0)
        
        # Clear the vector store
        vector_store.clear_all()
        
        # Get stats after clearing
        stats_after = vector_store.get_collection_stats()
        measurements_after = stats_after.get('total_measurements', 0)
        
        return {
            "message": f"ChromaDB cleared successfully. Removed {measurements_before} measurements.",
            "measurements_before": measurements_before,
            "measurements_after": measurements_after,
            "status": "cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear ChromaDB: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)