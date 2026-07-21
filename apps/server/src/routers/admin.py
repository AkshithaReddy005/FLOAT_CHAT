from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import tempfile
import time
import hashlib

from database.database import get_db, ArgoMeasurement, UploadedFile
from utils.netcdf_processor import NetCDFProcessor
from routers import deps

router = APIRouter()

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

def _get_enhanced_region_info(row, location_intel):
    """Get enhanced location information for a geographic region"""
    if not location_intel:
        return None

    try:
        # Handle both old format and new enhanced format
        if len(row) >= 8 and hasattr(row[7], 'get'):
            # New format with location context included
            return {
                "ocean_basin": row[7].get("ocean_basin"),
                "marine_region": row[7].get("marine_region"),
                "oceanographic_region": row[7].get("oceanographic_region"),
                "circulation_feature": row[7].get("circulation_feature"),
                "oceanographic_features": row[7].get("oceanographic_features", []),
                "seasonal_notes": row[7].get("seasonal_notes", []),
                "coordinates_center": row[7].get("coordinates"),
                "data_density": round(row[1] / ((row[4] - row[3]) * (row[6] - row[5])), 2) if (row[4] - row[3]) * (row[6] - row[5]) > 0 else 0
            }
        elif len(row) >= 7:
            # Old format, calculate location context
            region_name = row[0]
            measurement_count = row[1]
            float_count = row[2]
            lat_min, lat_max = row[3], row[4]
            lon_min, lon_max = row[5], row[6]

            if not all([lat_min, lat_max, lon_min, lon_max]):
                return None

            # Get center coordinates
            center_lat = (lat_min + lat_max) / 2
            center_lon = (lon_min + lon_max) / 2

            # Get enhanced location context
            location_context = location_intel.get_location_based_context(center_lat, center_lon)

            return {
                "ocean_basin": location_context.get("ocean_basin"),
                "marine_region": location_context.get("marine_region"),
                "oceanographic_region": location_context.get("oceanographic_region"),
                "circulation_feature": location_context.get("circulation_feature"),
                "oceanographic_features": location_context.get("oceanographic_features", []),
                "seasonal_notes": location_context.get("seasonal_notes", []),
                "coordinates_center": location_context.get("coordinates"),
                "data_density": round(measurement_count / ((lat_max - lat_min) * (lon_max - lon_min)), 2) if (lat_max - lat_min) * (lon_max - lon_min) > 0 else 0
            }
        else:
            return None

    except Exception as e:
        print(f"Error getting enhanced region info: {e}")
        return None

def _get_enhanced_geographic_distribution(db, location_intel):
    """Get enhanced geographic distribution using location intelligence"""
    if location_intel:
        # Get all data points with coordinates
        raw_data = db.execute(text("""
            SELECT latitude, longitude, float_id
            FROM argo_measurements
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """)).fetchall()

        # Use location intelligence to classify regions
        region_data = {}

        for lat, lon, float_id in raw_data:
            try:
                # Get location context for this point
                location_context = location_intel.get_location_based_context(lat, lon)

                # Use ocean basin as primary classification
                ocean_basin = location_context.get("ocean_basin", "Unknown Ocean")
                marine_region = location_context.get("marine_region", "Unknown Region")

                # Create hierarchical region name
                if marine_region and marine_region != "Unknown Region" and marine_region != ocean_basin:
                    region_name = f"{ocean_basin} - {marine_region}"
                else:
                    region_name = ocean_basin

                if region_name not in region_data:
                    region_data[region_name] = {
                        'measurements': [],
                        'floats': set(),
                        'lats': [],
                        'lons': [],
                        'context': location_context
                    }

                region_data[region_name]['measurements'].append((lat, lon))
                region_data[region_name]['floats'].add(float_id)
                region_data[region_name]['lats'].append(lat)
                region_data[region_name]['lons'].append(lon)

            except Exception as e:
                print(f"Error processing location {lat}, {lon}: {e}")
                continue

        # Convert to format expected by analytics
        result = []
        for region_name, data in region_data.items():
            if len(data['measurements']) > 0:  # Only include regions with data
                result.append((
                    region_name,
                    len(data['measurements']),  # measurement_count
                    len(data['floats']),         # float_count
                    min(data['lats']),           # min_lat
                    max(data['lats']),           # max_lat
                    min(data['lons']),           # min_lon
                    max(data['lons']),           # max_lon
                    data['context']              # Enhanced context
                ))

        # Sort by measurement count descending
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    else:
        # Fallback to enhanced static classification
        return db.execute(text("""
            SELECT
                CASE
                    WHEN latitude BETWEEN 15 AND 25 AND longitude BETWEEN 65 AND 75 THEN 'Arabian Sea - Central'
                    WHEN latitude BETWEEN 10 AND 15 AND longitude BETWEEN 65 AND 75 THEN 'Arabian Sea - Southern'
                    WHEN latitude BETWEEN 20 AND 30 AND longitude BETWEEN 60 AND 70 THEN 'Arabian Sea - Northern'
                    WHEN latitude BETWEEN 8 AND 20 AND longitude BETWEEN 80 AND 95 THEN 'Bay of Bengal - Western'
                    WHEN latitude BETWEEN 8 AND 20 AND longitude BETWEEN 90 AND 100 THEN 'Bay of Bengal - Eastern'
                    WHEN latitude BETWEEN -5 AND 5 AND longitude BETWEEN 50 AND 100 THEN 'Equatorial Indian Ocean'
                    WHEN latitude BETWEEN -20 AND -5 AND longitude BETWEEN 60 AND 100 THEN 'Southern Indian Ocean - Tropical'
                    WHEN latitude BETWEEN -40 AND -20 AND longitude BETWEEN 60 AND 120 THEN 'Southern Indian Ocean - Subtropical'
                    WHEN latitude < -40 AND longitude BETWEEN 60 AND 140 THEN 'Southern Ocean - Indian Sector'
                    WHEN latitude BETWEEN 0 AND 30 AND longitude BETWEEN 40 AND 65 THEN 'Western Indian Ocean'
                    WHEN latitude BETWEEN -30 AND 0 AND longitude BETWEEN 40 AND 65 THEN 'Southwest Indian Ocean'
                    WHEN latitude BETWEEN -15 AND 15 AND longitude BETWEEN 100 AND 120 THEN 'Eastern Indian Ocean'
                    ELSE 'Other Indian Ocean Regions'
                END as region,
                COUNT(*) as measurement_count,
                COUNT(DISTINCT float_id) as float_count,
                MIN(latitude) as min_lat, MAX(latitude) as max_lat,
                MIN(longitude) as min_lon, MAX(longitude) as max_lon
            FROM argo_measurements
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY region
            HAVING COUNT(*) > 0
            ORDER BY measurement_count DESC
        """)).fetchall()

@router.post("/upload")
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
        
        # Use new chunked transaction system for reliable data consistency
        print(f"Processing {len(measurements)} measurements using chunked transaction system")
        start_transaction_time = time.time()

        # Prepare file record for insertion
        file_record = {
            'filename': file.filename,
            'file_hash': file_hash,
            'file_size': file_size
        }

        # Execute coordinated transaction
        coord_result = deps.transaction_coordinator.execute_coordinated_transaction(
            db=db,
            vector_store=deps.vector_store,
            measurements=measurements,
            file_hash=file_hash,
            file_record=file_record
        )

        transaction_time = time.time() - start_transaction_time
        print(f"Coordinated transaction completed in {transaction_time:.2f}s")

        # Extract results for response
        new_measurements_count = coord_result.measurements_processed
        duplicate_measurements_count = 0
        vector_results = coord_result.chromadb_details or {}

        if coord_result.postgresql_details:
            duplicate_measurements_count = coord_result.postgresql_details.duplicate_skips
            print(f"Transaction summary: {new_measurements_count} inserted, "
                  f"{duplicate_measurements_count} duplicates, "
                  f"{coord_result.postgresql_details.failed_inserts} failed")

        if not coord_result.consistency_maintained:
            print(f"WARNING: Data consistency issue: {coord_result.error_details}")
        elif not coord_result.chromadb_success:
            print(f"INFO: ChromaDB processing failed but PostgreSQL succeeded: {coord_result.error_details}")

        # Update vector_results for backward compatibility
        if 'new_measurements' not in vector_results:
            vector_results = {
                "new_measurements": vector_results.get('new_measurements', 0),
                "duplicates_skipped": vector_results.get('duplicates_skipped', 0),
                "total_processed": len(measurements),
                "coordinator_status": "success" if coord_result.consistency_maintained else "partial_failure"
            }
        
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

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get system statistics for admin"""
    total_measurements = db.query(ArgoMeasurement).count()
    unique_floats = db.query(ArgoMeasurement.float_id).distinct().count()
    total_files = db.query(UploadedFile).count()
    
    # Get latest upload
    latest_upload = db.query(UploadedFile).order_by(UploadedFile.upload_date.desc()).first()
    
    # Get vector store stats
    vector_stats = deps.vector_store.get_collection_stats()
    
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

@router.get("/knowledge-base")
def get_knowledge_base_details(db: Session = Depends(get_db)):
    """Get detailed knowledge base information including data distribution and RAG insights"""
    try:
        # Initialize location intelligence
        try:
            from analysis.location_intelligence import LocationIntelligence
            location_intel = LocationIntelligence()
            location_available = True
        except ImportError:
            location_intel = None
            location_available = False
        # Basic vector store statistics
        vector_stats = deps.vector_store.get_collection_stats()
        
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
        
        # Enhanced Geographic distribution using location intelligence
        geographic_analysis = _get_enhanced_geographic_distribution(db, location_intel if location_available else None)
        
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
            sample_vectors = deps.vector_store.collection.get(limit=5)
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
                    "lon_range": [float(row[5]), float(row[6])] if row[5] and row[6] else None,
                    # Enhanced location intelligence
                    "enhanced_location_info": _get_enhanced_region_info(row, location_intel) if location_available else None
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

@router.get("/rag-balance-test")
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
                context_results = deps.vector_store.search(test_query, n_results=15)
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

@router.get("/files")
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

@router.delete("/chroma/clear")
def clear_chroma_database():
    """Clear all data from ChromaDB vector store (admin only)"""
    try:
        # Get stats before clearing
        stats_before = deps.vector_store.get_collection_stats()
        measurements_before = stats_before.get('total_measurements', 0)
        
        # Clear the vector store
        deps.vector_store.clear_all()
        
        # Get stats after clearing
        stats_after = deps.vector_store.get_collection_stats()
        measurements_after = stats_after.get('total_measurements', 0)
        
        return {
            "message": f"ChromaDB cleared successfully. Removed {measurements_before} measurements.",
            "measurements_before": measurements_before,
            "measurements_after": measurements_after,
            "status": "cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear ChromaDB: {str(e)}")

@router.delete("/postgres/clear")
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

@router.delete("/databases/clear")
def clear_all_databases(db: Session = Depends(get_db)):
    """Clear all data from both PostgreSQL and ChromaDB (admin only)"""
    try:
        # Get stats before clearing
        measurements_before = db.query(ArgoMeasurement).count()
        files_before = db.query(UploadedFile).count()
        vector_stats_before = deps.vector_store.get_collection_stats()
        vector_measurements_before = vector_stats_before.get('total_measurements', 0)
        
        # Clear PostgreSQL
        db.query(ArgoMeasurement).delete()
        db.query(UploadedFile).delete()
        db.commit()
        
        # Clear ChromaDB
        deps.vector_store.clear_all()
        
        # Force reinitialize vector store to ensure clean state
        deps.vector_store.reinitialize()
        
        # Get stats after clearing
        measurements_after = db.query(ArgoMeasurement).count()
        files_after = db.query(UploadedFile).count()
        vector_stats_after = deps.vector_store.get_collection_stats()
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

@router.get("/data-consistency-check")
def check_data_consistency(db: Session = Depends(get_db)):
    """Comprehensive data consistency check between PostgreSQL and ChromaDB with enhanced edge case handling"""
    try:
        # Get PostgreSQL statistics
        postgres_measurements = db.query(ArgoMeasurement).count()
        postgres_unique_floats = db.query(ArgoMeasurement.float_id).distinct().count()
        postgres_files = db.query(UploadedFile).count()

        # Enhanced sample data collection - use dynamic sample size based on data volume
        sample_size = min(max(10, postgres_measurements // 1000), 50)  # Scale sample size with data volume
        postgres_sample = db.execute(text("""
            SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure, measurement_hash
            FROM argo_measurements
            WHERE temperature IS NOT NULL AND salinity IS NOT NULL AND depth IS NOT NULL
            ORDER BY created_at DESC
            LIMIT :sample_size
        """), {"sample_size": sample_size}).fetchall()

        # Get ChromaDB statistics
        vector_stats = deps.vector_store.get_collection_stats()
        chroma_measurements = vector_stats.get('total_measurements', 0)

        # Enhanced vector store connectivity test
        vector_error = None
        chroma_searchable = 0
        try:
            # Test multiple search patterns to ensure robustness
            test_searches = [
                "temperature salinity depth",
                "oceanographic measurement",
                "argo float data"
            ]
            
            for search_query in test_searches:
                # Test with a reasonable sample size to verify searchability
                test_n_results = min(50, max(10, chroma_measurements // 100))  # Test with up to 50 results
                sample_search = deps.vector_store.search(search_query, n_results=test_n_results)
                if sample_search and sample_search.get('documents'):
                    search_results = sample_search.get('documents', [[]])[0]
                    chroma_searchable = max(chroma_searchable, len(search_results))
                    # If we got meaningful results, break early
                    if len(search_results) >= test_n_results * 0.8:  # Got at least 80% of requested results
                        break
            
        except Exception as e:
            vector_error = str(e)

        # Initialize consistency tracking
        consistency_issues = []
        consistency_score = 100
        detailed_checks = {
            "count_consistency": {"passed": True, "details": ""},
            "vector_searchability": {"passed": True, "details": ""},
            "sample_verification": {"passed": True, "details": ""},
            "hash_consistency": {"passed": True, "details": ""},
            "file_consistency": {"passed": True, "details": ""},
            "data_completeness": {"passed": True, "details": ""}
        }

        # 1. Enhanced count consistency check with better edge case handling
        if postgres_measurements == 0 and chroma_measurements == 0:
            detailed_checks["count_consistency"]["details"] = "Both databases are empty - consistent but no data"
        elif postgres_measurements == 0:
            consistency_issues.append(f"PostgreSQL is empty but ChromaDB has {chroma_measurements} measurements")
            consistency_score -= 50
            detailed_checks["count_consistency"]["passed"] = False
        else:
            count_diff = abs(postgres_measurements - chroma_measurements)
            count_diff_percentage = (count_diff / postgres_measurements) * 100

            if count_diff_percentage > 10:  # More than 10% difference is critical
                consistency_issues.append(f"Critical count difference: PostgreSQL has {postgres_measurements}, ChromaDB has {chroma_measurements} ({count_diff_percentage:.1f}% difference)")
                consistency_score -= 40
                detailed_checks["count_consistency"]["passed"] = False
            elif count_diff_percentage > 5:  # More than 5% difference is significant
                consistency_issues.append(f"Significant count difference: PostgreSQL has {postgres_measurements}, ChromaDB has {chroma_measurements} ({count_diff_percentage:.1f}% difference)")
                consistency_score -= 25
                detailed_checks["count_consistency"]["passed"] = False
            elif count_diff_percentage > 1:  # More than 1% difference is minor
                consistency_issues.append(f"Minor count difference: PostgreSQL has {postgres_measurements}, ChromaDB has {chroma_measurements} ({count_diff_percentage:.1f}% difference)")
                consistency_score -= 10

            detailed_checks["count_consistency"]["details"] = f"PostgreSQL: {postgres_measurements}, ChromaDB: {chroma_measurements}, Difference: {count_diff_percentage:.1f}%"

        # 2. Enhanced vector store searchability check
        if vector_error:
            consistency_issues.append(f"Vector store connectivity error: {vector_error}")
            consistency_score -= 30
            detailed_checks["vector_searchability"]["passed"] = False
            detailed_checks["vector_searchability"]["details"] = f"Error: {vector_error}"
        elif chroma_measurements > 0 and chroma_searchable == 0:
            consistency_issues.append("ChromaDB has data but appears to have no searchable documents")
            consistency_score -= 35
            detailed_checks["vector_searchability"]["passed"] = False
        elif chroma_measurements > 0:
            # Calculate expected results based on what we requested
            expected_min_results = min(50, max(10, chroma_measurements // 100))
            if chroma_searchable < expected_min_results * 0.5:  # Got less than 50% of reasonable expected results
                consistency_issues.append(f"ChromaDB search returns fewer results than expected: {chroma_searchable} found when requesting {expected_min_results}")
                consistency_score -= 20
                detailed_checks["vector_searchability"]["passed"] = False

        detailed_checks["vector_searchability"]["details"] = f"Searchable: {chroma_searchable}, Total: {chroma_measurements}"

        # 3. Enhanced sample data verification with comprehensive field matching
        missing_in_vector = 0
        hash_mismatches = 0
        field_validation_issues = 0
        
        if postgres_sample:
            check_sample_size = min(len(postgres_sample), max(5, len(postgres_sample) // 2))
            
            for i, row in enumerate(postgres_sample[:check_sample_size]):
                try:
                    # Safely construct search query with null checks
                    float_id = str(row[0]) if row[0] is not None else "unknown"
                    temperature = f"{float(row[5]):.2f}" if row[5] is not None else "null"
                    salinity = f"{float(row[6]):.2f}" if row[6] is not None else "null"
                    depth = f"{float(row[4]):.2f}" if row[4] is not None else "null"
                    
                    # First try direct hash-based lookup
                    measurement_hash = row[8] if len(row) > 8 and row[8] else None
                    found_by_hash = False
                    
                    if measurement_hash:
                        try:
                            hash_search = deps.vector_store.collection.get(ids=[measurement_hash])
                            if hash_search and hash_search.get('ids'):
                                found_by_hash = True
                        except Exception:
                            pass
                    
                    # If hash lookup fails, try content-based search
                    found_by_content = False
                    if not found_by_hash:
                        search_query = f"float {float_id} temperature {temperature} salinity {salinity} depth {depth}"
                        search_result = deps.vector_store.search(search_query, n_results=5)

                        if search_result.get('metadatas'):
                            for metadata in search_result['metadatas'][0]:
                                if not metadata:
                                    continue
                                
                                # Enhanced matching with multiple field validation
                                matches = 0
                                total_checks = 0
                                
                                # Float ID match
                                if metadata.get('float_id') == row[0]:
                                    matches += 1
                                
                                total_checks += 1
                                
                                # Temperature match (with tolerance)
                                if row[5] is not None and metadata.get('temperature') is not None:
                                    try:
                                        temp_diff = abs(float(metadata.get('temperature')) - float(row[5]))
                                        if temp_diff < 0.01:  # Tighter tolerance
                                            matches += 1
                                    except (ValueError, TypeError):
                                        pass
                                    total_checks += 1
                                
                                # Salinity match (with tolerance)
                                if row[6] is not None and metadata.get('salinity') is not None:
                                    try:
                                        sal_diff = abs(float(metadata.get('salinity')) - float(row[6]))
                                        if sal_diff < 0.01:  # Tighter tolerance
                                            matches += 1
                                    except (ValueError, TypeError):
                                        pass
                                    total_checks += 1
                                
                                # Depth match (with tolerance)
                                if row[4] is not None and metadata.get('depth') is not None:
                                    try:
                                        depth_diff = abs(float(metadata.get('depth')) - float(row[4]))
                                        if depth_diff < 0.1:
                                            matches += 1
                                    except (ValueError, TypeError):
                                        pass
                                    total_checks += 1
                                
                                # Consider it a match if at least 75% of fields match
                                if total_checks > 0 and (matches / total_checks) >= 0.75:
                                    found_by_content = True
                                    break

                    if not found_by_hash and not found_by_content:
                        missing_in_vector += 1
                    elif not found_by_hash and measurement_hash:
                        hash_mismatches += 1
                        
                except Exception as e:
                    missing_in_vector += 1
                    field_validation_issues += 1

            # Calculate consistency based on sample results
            sample_loss_percentage = (missing_in_vector / check_sample_size) * 100 if check_sample_size > 0 else 0
            
            if sample_loss_percentage > 50:  # More than 50% missing is critical
                consistency_issues.append(f"Critical data loss: {missing_in_vector}/{check_sample_size} recent measurements not found in vector store ({sample_loss_percentage:.1f}%)")
                consistency_score -= 35
                detailed_checks["sample_verification"]["passed"] = False
            elif sample_loss_percentage > 20:  # More than 20% missing is significant
                consistency_issues.append(f"Significant data loss: {missing_in_vector}/{check_sample_size} recent measurements not found in vector store ({sample_loss_percentage:.1f}%)")
                consistency_score -= 25
                detailed_checks["sample_verification"]["passed"] = False
            elif missing_in_vector > 0:
                consistency_issues.append(f"Minor data inconsistency: {missing_in_vector}/{check_sample_size} recent measurements not found in vector store ({sample_loss_percentage:.1f}%)")
                consistency_score -= 10

            # Hash consistency issues
            if hash_mismatches > 0:
                consistency_issues.append(f"Hash consistency issues: {hash_mismatches}/{check_sample_size} measurements found by content but not by hash")
                consistency_score -= 15
                detailed_checks["hash_consistency"]["passed"] = False

            # Field validation issues
            if field_validation_issues > 0:
                consistency_issues.append(f"Data validation issues: {field_validation_issues}/{check_sample_size} measurements had field validation errors")
                consistency_score -= 10

            detailed_checks["sample_verification"]["details"] = f"Checked: {check_sample_size}, Missing: {missing_in_vector}, Hash mismatches: {hash_mismatches}, Field issues: {field_validation_issues}"

        # 4. Enhanced file upload consistency with data completeness check
        try:
            total_measurements_from_files = db.execute(text(
                "SELECT COALESCE(SUM(measurements_count), 0) FROM uploaded_files"
            )).fetchone()[0]

            # Check for data completeness
            null_data_count = db.execute(text("""
                SELECT COUNT(*) FROM argo_measurements 
                WHERE temperature IS NULL OR salinity IS NULL OR depth IS NULL
            """)).fetchone()[0]

            file_consistency_diff = abs(total_measurements_from_files - postgres_measurements)
            file_consistency_percentage = (file_consistency_diff / max(postgres_measurements, 1)) * 100

            if file_consistency_percentage > 5:
                consistency_issues.append(f"File upload records inconsistent: Files report {total_measurements_from_files} measurements, but database has {postgres_measurements} ({file_consistency_percentage:.1f}% difference)")
                consistency_score -= 20
                detailed_checks["file_consistency"]["passed"] = False

            # Data completeness check
            if postgres_measurements > 0:
                null_percentage = (null_data_count / postgres_measurements) * 100
                if null_percentage > 10:
                    consistency_issues.append(f"High null data rate: {null_data_count}/{postgres_measurements} measurements ({null_percentage:.1f}%) have missing critical data")
                    consistency_score -= 15
                    detailed_checks["data_completeness"]["passed"] = False
                elif null_percentage > 5:
                    consistency_issues.append(f"Moderate null data rate: {null_data_count}/{postgres_measurements} measurements ({null_percentage:.1f}%) have missing critical data")
                    consistency_score -= 8

            detailed_checks["file_consistency"]["details"] = f"Files report: {total_measurements_from_files}, DB has: {postgres_measurements}, Null data: {null_data_count}"

        except Exception as e:
            consistency_issues.append(f"File consistency check failed: {str(e)}")
            consistency_score -= 15
            detailed_checks["file_consistency"]["passed"] = False

        # Determine overall status with enhanced thresholds
        if consistency_score >= 95:
            overall_status = "excellent"
        elif consistency_score >= 85:
            overall_status = "good"
        elif consistency_score >= 70:
            overall_status = "acceptable"
        elif consistency_score >= 50:
            overall_status = "concerning"
        else:
            overall_status = "critical"

        # Enhanced recommendations based on specific issues
        recommendations = []
        if any(not check["passed"] for check in detailed_checks.values()):
            if not detailed_checks["count_consistency"]["passed"]:
                recommendations.append("Re-sync data between PostgreSQL and ChromaDB to resolve count differences")
            if not detailed_checks["vector_searchability"]["passed"]:
                recommendations.append("Rebuild vector store indexes to restore search functionality")
            if not detailed_checks["sample_verification"]["passed"]:
                recommendations.append("Investigate recent data ingestion process for consistency issues")
            if not detailed_checks["hash_consistency"]["passed"]:
                recommendations.append("Validate hash generation consistency between database and vector store")
            if not detailed_checks["file_consistency"]["passed"]:
                recommendations.append("Audit file upload tracking and measurement counting processes")
            if not detailed_checks["data_completeness"]["passed"]:
                recommendations.append("Review data validation rules and improve null data handling")
        
        if consistency_score < 80:
            recommendations.append("Run full database reinitialization to fix multiple consistency issues")
        if not detailed_checks["vector_searchability"]["passed"]:
            recommendations.append("Check vector store search functionality and embedding quality")
        if postgres_measurements > 10000 and len(postgres_sample) < 20:
            recommendations.append("Increase sample size for large datasets to improve validation accuracy")

        return {
            "overall_status": overall_status,
            "consistency_score": consistency_score,
            "consistency_issues": consistency_issues,
            "recommendations": recommendations,
            "detailed_analysis": {
                "postgresql": {
                    "total_measurements": postgres_measurements,
                    "unique_floats": postgres_unique_floats,
                    "uploaded_files": postgres_files,
                    "sample_data_count": len(postgres_sample),
                    "sample_size_used": sample_size
                },
                "chromadb": {
                    "total_measurements": chroma_measurements,
                    "searchable_results": chroma_searchable,
                    "vector_store_error": vector_error,
                    "collection_stats": vector_stats
                },
                "consistency_checks": detailed_checks,
                "validation_metrics": {
                    "sample_size_used": len(postgres_sample) if postgres_sample else 0,
                    "missing_in_vector_store": missing_in_vector,
                    "hash_mismatches": hash_mismatches,
                    "field_validation_issues": field_validation_issues,
                    "count_difference": abs(postgres_measurements - chroma_measurements),
                    "count_difference_percentage": round((abs(postgres_measurements - chroma_measurements) / max(postgres_measurements, 1)) * 100, 2),
                    "file_upload_consistency": total_measurements_from_files == postgres_measurements
                }
            },
            "test_timestamp": time.time(),
            "enhanced_validation": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check data consistency: {str(e)}")

@router.post("/reinitialize")
def reinitialize_connections():
    """Reinitialize database connections and clear caches (admin only)"""
    try:
        # Reinitialize vector store to pick up any external database changes
        deps.vector_store.reinitialize()

        # Get fresh stats
        vector_stats = deps.vector_store.get_collection_stats()

        return {
            "message": "Connections reinitialized successfully.",
            "vector_store": vector_stats,
            "status": "reinitialized"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize: {str(e)}")
