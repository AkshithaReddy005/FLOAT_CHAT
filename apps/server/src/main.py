from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from pydantic import BaseModel
import os
import tempfile
import time
import hashlib
from typing import List, Optional
from dotenv import load_dotenv

from database.database import get_db, create_tables, ArgoMeasurement, UploadedFile
from rag_pipeline.vector_store import VectorStore
from utils.netcdf_processor import NetCDFProcessor
from chat_bot.chatbot_service import ChatbotService
from utils.example_query_generator import ExampleQueryGenerator

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
chatbot_service = ChatbotService(vector_store)
example_generator = ExampleQueryGenerator(vector_store)

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
        
        # Store in ChromaDB with duplicate detection (non-blocking)
        try:
            vector_results = vector_store.add_measurements(measurements, file_hash)
        except Exception as vector_e:
            print(f"Vector store operation failed: {vector_e}")
            # Continue processing even if vector store fails
            vector_results = {
                "new_measurements": 0,
                "duplicates_skipped": 0,
                "total_processed": len(measurements),
                "error": "Vector store operation failed but data was saved to database"
            }
        
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

@app.post("/admin/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Admin endpoint to upload multiple ARGO NetCDF files with batch processing"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    
    if len(files) > 20:  # Reasonable limit for batch processing
        raise HTTPException(status_code=400, detail="Too many files. Maximum 20 files allowed per batch.")
    
    results = []
    total_new_measurements = 0
    total_duplicates = 0
    total_errors = 0
    
    for i, file in enumerate(files):
        file_result = {
            "filename": file.filename,
            "index": i + 1,
            "status": "processing"
        }
        
        temp_file_path = None
        try:
            # Validate file type
            if not file.filename or not file.filename.endswith(('.nc', '.netcdf')):
                file_result.update({
                    "status": "error",
                    "error": "Invalid file format. Only NetCDF files are allowed.",
                    "measurements_count": 0
                })
                total_errors += 1
                results.append(file_result)
                continue
            
            # Read file content and calculate hash
            content = await file.read()
            file_hash = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            
            # Check if this exact file has been uploaded before
            existing_file = db.query(UploadedFile).filter(UploadedFile.file_hash == file_hash).first()
            if existing_file:
                file_result.update({
                    "status": "duplicate_file",
                    "message": f"File already uploaded on {existing_file.upload_date}",
                    "measurements_count": 0,
                    "existing_measurements": existing_file.measurements_count,
                    "original_upload_date": existing_file.upload_date.isoformat()
                })
                total_duplicates += 1
                results.append(file_result)
                continue
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
                temp_file.write(content)
                temp_file.flush()
                temp_file_path = temp_file.name
            
            # Validate NetCDF file
            if not NetCDFProcessor.validate_file(temp_file_path):
                file_result.update({
                    "status": "error",
                    "error": "Invalid NetCDF file format.",
                    "measurements_count": 0
                })
                total_errors += 1
                results.append(file_result)
                continue
            
            # Process the file
            measurements = NetCDFProcessor.process_argo_file(temp_file_path)
            
            if not measurements:
                file_result.update({
                    "status": "error", 
                    "error": "No valid measurements found in file.",
                    "measurements_count": 0
                })
                total_errors += 1
                results.append(file_result)
                continue
            
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
            
            # Update file result
            file_result.update({
                "status": "completed" if new_measurements_count > 0 else "all_duplicates",
                "measurements_count": new_measurements_count,
                "duplicate_measurements": duplicate_measurements_count,
                "total_in_file": len(measurements),
                "vector_stats": vector_results,
                "file_size": file_size
            })
            
            total_new_measurements += new_measurements_count
            if duplicate_measurements_count > 0:
                total_duplicates += 1
            
            results.append(file_result)
                
        except Exception as e:
            db.rollback()
            file_result.update({
                "status": "error",
                "error": f"Processing failed: {str(e)}",
                "measurements_count": 0
            })
            total_errors += 1
            results.append(file_result)
        
        finally:
            # Clean up temporary file
            if temp_file_path:
                _safe_delete_file(temp_file_path)
    
    # Prepare summary
    successful_files = len([r for r in results if r["status"] == "completed"])
    duplicate_files = len([r for r in results if r["status"] == "duplicate_file"])
    
    return {
        "message": f"Batch upload completed: {successful_files} files processed successfully, {duplicate_files} duplicates, {total_errors} errors",
        "summary": {
            "total_files": len(files),
            "successful_files": successful_files,
            "duplicate_files": duplicate_files,
            "error_files": total_errors,
            "total_new_measurements": total_new_measurements
        },
        "file_results": results,
        "status": "batch_completed"
    }

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

@app.post("/chat", response_model=ChatResponse)
async def chat_with_data(request: ChatRequest, db: Session = Depends(get_db)):
    """Chat endpoint for natural language queries about ARGO data"""
    
    try:
        # Process the chat query using the chatbot service with context
        result = await chatbot_service.process_chat_query(request.message, db, request.session_context)
        
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
            fallback_result = await chatbot_service.create_fallback_response(request.message, db)
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

@app.get("/examples")
def get_example_queries(db: Session = Depends(get_db)):
    """Get dynamic example queries based on available data"""
    try:
        examples = example_generator.generate_dynamic_examples(db, max_examples=6)
        return {
            "examples": examples,
            "generated_at": time.time(),
            "status": "success"
        }
    except Exception as e:
        # Return fallback examples on error
        fallback_examples = example_generator._get_fallback_examples()
        return {
            "examples": fallback_examples,
            "generated_at": time.time(),
            "status": "fallback",
            "error": str(e)
        }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check for all system components"""
    
    health_status = {
        "timestamp": time.time(),
        "overall_status": "healthy",
        "components": {}
    }
    
    try:
        # Check database connection
        db_count = db.query(ArgoMeasurement).count()
        health_status["components"]["database"] = {
            "status": "healthy",
            "measurements_count": db_count,
            "message": f"Database accessible with {db_count} measurements"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy", 
            "error": str(e),
            "message": "Database connection failed"
        }
        health_status["overall_status"] = "degraded"
    
    try:
        # Check vector store
        vector_stats = vector_store.get_collection_stats()
        health_status["components"]["vector_store"] = {
            "status": "healthy",
            "stats": vector_stats,
            "message": "Vector store accessible"
        }
    except Exception as e:
        health_status["components"]["vector_store"] = {
            "status": "unhealthy",
            "error": str(e), 
            "message": "Vector store connection failed"
        }
        health_status["overall_status"] = "degraded"
    
    try:
        # Check RAG components
        from rag_pipeline.rag_engine import RAGEngine
        rag_test = RAGEngine()
        health_status["components"]["rag_engine"] = {
            "status": "healthy",
            "gemini_available": rag_test.use_gemini,
            "message": f"RAG engine initialized ({'with Gemini' if rag_test.use_gemini else 'rule-based only'})"
        }
    except Exception as e:
        health_status["components"]["rag_engine"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "RAG engine initialization failed" 
        }
        health_status["overall_status"] = "degraded"
    
    return health_status

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

@app.get("/admin/knowledge-base")
def get_knowledge_base_details(db: Session = Depends(get_db)):
    """Get detailed knowledge base information including data distribution and RAG insights"""
    try:
        # Basic vector store statistics
        vector_stats = vector_store.get_collection_stats()
        
        # Database statistics
        total_measurements = db.query(ArgoMeasurement).count()
        unique_floats = db.query(ArgoMeasurement.float_id).distinct().count()
        
        # Depth distribution analysis
        depth_analysis = db.execute(text("""
            SELECT 
                CASE 
                    WHEN depth < 50 THEN 'surface'
                    WHEN depth < 200 THEN 'thermocline'
                    WHEN depth < 1000 THEN 'intermediate'
                    WHEN depth < 4000 THEN 'deep'
                    ELSE 'abyssal'
                END as depth_category,
                COUNT(*) as count,
                MIN(depth) as min_depth,
                MAX(depth) as max_depth,
                AVG(depth) as avg_depth
            FROM argo_measurements 
            WHERE depth IS NOT NULL
            GROUP BY depth_category
            ORDER BY min_depth
        """)).fetchall()
        
        # Geographic distribution
        geographic_analysis = db.execute(text("""
            SELECT 
                CASE
                    WHEN latitude BETWEEN 10 AND 30 AND longitude BETWEEN 60 AND 80 THEN 'Arabian Sea'
                    WHEN latitude BETWEEN -10 AND 10 AND longitude BETWEEN 60 AND 100 THEN 'Equatorial Indian Ocean'
                    WHEN latitude BETWEEN -30 AND -10 AND longitude BETWEEN 60 AND 120 THEN 'Southern Indian Ocean'
                    WHEN latitude BETWEEN -15 AND 15 AND longitude BETWEEN 40 AND 65 THEN 'Western Indian Ocean'
                    ELSE 'Other Indian Ocean'
                END as region,
                COUNT(*) as measurement_count,
                COUNT(DISTINCT float_id) as float_count,
                MIN(latitude) as min_lat, MAX(latitude) as max_lat,
                MIN(longitude) as min_lon, MAX(longitude) as max_lon
            FROM argo_measurements 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY region
            ORDER BY measurement_count DESC
        """)).fetchall()
        
        # Temperature and salinity ranges
        parameter_analysis = db.execute(text("""
            SELECT 
                COUNT(*) as total_measurements,
                COUNT(temperature) as temp_measurements,
                COUNT(salinity) as salinity_measurements,
                COUNT(pressure) as pressure_measurements,
                AVG(temperature) as avg_temp,
                MIN(temperature) as min_temp,
                MAX(temperature) as max_temp,
                AVG(salinity) as avg_salinity,
                MIN(salinity) as min_salinity,
                MAX(salinity) as max_salinity
            FROM argo_measurements
        """)).fetchone()
        
        # Temporal distribution
        temporal_analysis = db.execute(text("""
            SELECT 
                DATE_TRUNC('month', date) as month,
                COUNT(*) as measurement_count,
                COUNT(DISTINCT float_id) as active_floats
            FROM argo_measurements 
            WHERE date IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)).fetchall()
        
        # Sample vector store documents to understand content quality
        try:
            sample_vectors = vector_store.collection.get(limit=5)
            sample_documents = sample_vectors.get('documents', [])[:3] if sample_vectors else []
        except Exception as e:
            print(f"Failed to get sample vectors: {e}")
            sample_documents = []
        
        return {
            "knowledge_base_overview": {
                "vector_store": vector_stats,
                "database_measurements": total_measurements,
                "unique_instruments": unique_floats,
                "data_coverage_percentage": round((vector_stats.get('total_measurements', 0) / max(total_measurements, 1)) * 100, 2)
            },
            "depth_distribution": [
                {
                    "category": row[0],
                    "count": row[1],
                    "min_depth": float(row[2]) if row[2] is not None else None,
                    "max_depth": float(row[3]) if row[3] is not None else None,
                    "avg_depth": float(row[4]) if row[4] is not None else None
                }
                for row in depth_analysis
            ],
            "geographic_distribution": [
                {
                    "region": row[0],
                    "measurement_count": row[1],
                    "float_count": row[2],
                    "lat_range": [float(row[3]), float(row[4])] if row[3] and row[4] else None,
                    "lon_range": [float(row[5]), float(row[6])] if row[5] and row[6] else None
                }
                for row in geographic_analysis
            ],
            "parameter_coverage": {
                "total_measurements": parameter_analysis[0],
                "temperature_coverage": round((parameter_analysis[1] / max(parameter_analysis[0], 1)) * 100, 2),
                "salinity_coverage": round((parameter_analysis[2] / max(parameter_analysis[0], 1)) * 100, 2),
                "pressure_coverage": round((parameter_analysis[3] / max(parameter_analysis[0], 1)) * 100, 2),
                "ranges": {
                    "temperature": {
                        "avg": round(float(parameter_analysis[4]), 3) if parameter_analysis[4] else None,
                        "min": round(float(parameter_analysis[5]), 3) if parameter_analysis[5] else None,
                        "max": round(float(parameter_analysis[6]), 3) if parameter_analysis[6] else None
                    },
                    "salinity": {
                        "avg": round(float(parameter_analysis[7]), 3) if parameter_analysis[7] else None,
                        "min": round(float(parameter_analysis[8]), 3) if parameter_analysis[8] else None,
                        "max": round(float(parameter_analysis[9]), 3) if parameter_analysis[9] else None
                    }
                }
            },
            "temporal_distribution": [
                {
                    "month": row[0].isoformat() if row[0] else None,
                    "measurement_count": row[1],
                    "active_floats": row[2]
                }
                for row in temporal_analysis
            ],
            "rag_insights": {
                "vector_embeddings_quality": "Enhanced analytics-aware embeddings with oceanographic context",
                "search_capabilities": [
                    "Semantic search with oceanographic understanding",
                    "Depth-layer filtering (surface, thermocline, intermediate, deep, abyssal)",
                    "Regional filtering (Arabian Sea, Equatorial Indian Ocean, etc.)",
                    "Parameter-specific search (temperature, salinity, pressure)",
                    "Seasonal and temporal analysis",
                    "Water mass identification",
                    "Anomaly detection (temperature/salinity anomalies)"
                ],
                "sample_vector_content": sample_documents
            },
            "data_quality_indicators": {
                "completeness_score": round(((parameter_analysis[1] + parameter_analysis[2] + parameter_analysis[3]) / (parameter_analysis[0] * 3)) * 100, 2),
                "geographic_coverage": len([row for row in geographic_analysis if row[1] > 0]),
                "depth_coverage": len([row for row in depth_analysis if row[1] > 0]),
                "vector_db_sync": round((vector_stats.get('total_measurements', 0) / max(total_measurements, 1)) * 100, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze knowledge base: {str(e)}")

@app.get("/admin/rag-balance-test")
def test_rag_balance(db: Session = Depends(get_db)):
    """Test RAG pipeline balance with sample queries to identify potential data capture issues"""
    try:
        # Test queries to evaluate RAG balance
        test_queries = [
            "What is the temperature profile in the Arabian Sea?",
            "Show me salinity measurements from deep waters",  
            "Compare temperature between surface and deep waters",
            "What recent data do you have from Indian Ocean floats?",
            "Analyze temperature trends over depth"
        ]
        
        results = []
        
        for test_query in test_queries:
            try:
                # Quick context retrieval test
                context_results = vector_store.search(test_query, n_results=15)
                context_count = len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0
                
                # Quick data retrieval test
                sample_data = db.execute(text(
                    "SELECT COUNT(*) as count FROM argo_measurements WHERE temperature IS NOT NULL AND salinity IS NOT NULL"
                )).fetchone()
                
                results.append({
                    "query": test_query,
                    "vector_context_found": context_count,
                    "available_data_points": sample_data[0] if sample_data else 0,
                    "context_quality": "good" if context_count >= 8 else "limited" if context_count >= 3 else "poor"
                })
                
            except Exception as query_error:
                results.append({
                    "query": test_query,
                    "error": str(query_error),
                    "status": "failed"
                })
        
        # Overall assessment
        avg_context = sum(r.get('vector_context_found', 0) for r in results) / len(results)
        total_data = results[0].get('available_data_points', 0) if results else 0
        
        assessment = {
            "overall_status": "good" if avg_context >= 8 else "needs_improvement" if avg_context >= 5 else "poor",
            "average_context_retrieval": round(avg_context, 1),
            "total_available_data": total_data,
            "test_results": results,
            "recommendations": []
        }
        
        # Generate recommendations
        if avg_context < 8:
            assessment["recommendations"].append("Consider increasing vector search results limit")
        if avg_context < 5:
            assessment["recommendations"].append("Vector embeddings may need optimization")
        if total_data < 1000:
            assessment["recommendations"].append("More data may be needed for comprehensive analysis")
        
        return assessment
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test RAG balance: {str(e)}")

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

@app.delete("/admin/postgres/clear")
def clear_postgres_database(db: Session = Depends(get_db)):
    """Clear all data from PostgreSQL database (admin only)"""
    try:
        # Get stats before clearing
        measurements_before = db.query(ArgoMeasurement).count()
        files_before = db.query(UploadedFile).count()
        
        # Clear all data
        db.query(ArgoMeasurement).delete()
        db.query(UploadedFile).delete()
        db.commit()
        
        # Get stats after clearing
        measurements_after = db.query(ArgoMeasurement).count()
        files_after = db.query(UploadedFile).count()
        
        return {
            "message": f"PostgreSQL cleared successfully. Removed {measurements_before} measurements and {files_before} files.",
            "measurements_before": measurements_before,
            "measurements_after": measurements_after,
            "files_before": files_before,
            "files_after": files_after,
            "status": "cleared"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear PostgreSQL: {str(e)}")

@app.delete("/admin/databases/clear")
def clear_all_databases(db: Session = Depends(get_db)):
    """Clear all data from both PostgreSQL and ChromaDB (admin only)"""
    try:
        # Get stats before clearing
        measurements_before = db.query(ArgoMeasurement).count()
        files_before = db.query(UploadedFile).count()
        vector_stats_before = vector_store.get_collection_stats()
        vector_measurements_before = vector_stats_before.get('total_measurements', 0)
        
        # Clear PostgreSQL
        db.query(ArgoMeasurement).delete()
        db.query(UploadedFile).delete()
        db.commit()
        
        # Clear ChromaDB
        vector_store.clear_all()
        
        # Force reinitialize vector store to ensure clean state
        vector_store.reinitialize()
        
        # Get stats after clearing
        measurements_after = db.query(ArgoMeasurement).count()
        files_after = db.query(UploadedFile).count()
        vector_stats_after = vector_store.get_collection_stats()
        vector_measurements_after = vector_stats_after.get('total_measurements', 0)
        
        return {
            "message": f"All databases cleared successfully. Removed {measurements_before} PostgreSQL measurements, {files_before} files, and {vector_measurements_before} ChromaDB measurements.",
            "postgres": {
                "measurements_before": measurements_before,
                "measurements_after": measurements_after,
                "files_before": files_before,
                "files_after": files_after
            },
            "chromadb": {
                "measurements_before": vector_measurements_before,
                "measurements_after": vector_measurements_after
            },
            "status": "cleared"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear databases: {str(e)}")

@app.post("/admin/reinitialize")
def reinitialize_connections():
    """Reinitialize database connections and clear caches (admin only)"""
    global vector_store
    try:
        # Reinitialize vector store to pick up any external database changes
        vector_store.reinitialize()
        
        # Get fresh stats
        vector_stats = vector_store.get_collection_stats()
        
        return {
            "message": "Connections reinitialized successfully.",
            "vector_store": vector_stats,
            "status": "reinitialized"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)