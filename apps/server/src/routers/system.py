from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

from database.database import get_db, ArgoMeasurement, UploadedFile
from routers import deps

router = APIRouter()

@router.get("/api/location/reverse-geocode")
def reverse_geocode_location(lat: float, lon: float):
    """Convert latitude/longitude coordinates to location name using LocationIntelligence"""
    try:
        # Initialize location intelligence
        from analysis.location_intelligence import LocationIntelligence
        location_intel = LocationIntelligence()

        # Get location context
        location_context = location_intel.get_location_based_context(lat, lon)

        # Build simple location name from context
        location_name = []

        # Add marine region if available
        if location_context.get("marine_region") and location_context["marine_region"] != "Unknown":
            location_name.append(location_context["marine_region"])

        # Add ocean basin if available
        if location_context.get("ocean_basin") and location_context["ocean_basin"] != "Unknown":
            location_name.append(location_context["ocean_basin"])

        # Fallback to oceanographic region
        if not location_name and location_context.get("oceanographic_region"):
            location_name.append(location_context["oceanographic_region"])

        # Create final location string
        final_location = ", ".join(location_name) if location_name else f"Ocean ({lat:.1f}°, {lon:.1f}°)"

        return {
            "location": final_location,
            "details": {
                "ocean_basin": location_context.get("ocean_basin"),
                "marine_region": location_context.get("marine_region"),
                "oceanographic_region": location_context.get("oceanographic_region"),
                "coordinates": f"{lat:.4f}°, {lon:.4f}°"
            },
            "success": True
        }

    except Exception as e:
        print(f"Error in reverse geocoding: {e}")
        return {
            "location": f"Ocean ({lat:.1f}°, {lon:.1f}°)",
            "details": {
                "coordinates": f"{lat:.4f}°, {lon:.4f}°"
            },
            "success": False,
            "error": str(e)
        }

@router.get("/health")
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
        vector_stats = deps.vector_store.get_collection_stats()
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


@router.get("/user/analytics")
def get_user_analytics(db: Session = Depends(get_db)):
    """Get analytics data for regular users with enhanced location intelligence"""
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
            "data_quality_indicators": {
                "completeness_score": round(((parameter_analysis[1] + parameter_analysis[2] + parameter_analysis[3]) / (parameter_analysis[0] * 3)) * 100, 2),
                "geographic_coverage": len([row for row in geographic_analysis if row[1] > 0]),
                "depth_coverage": len([row for row in depth_analysis if row[1] > 0]),
                "vector_db_sync": round((vector_stats.get('total_measurements', 0) / max(total_measurements, 1)) * 100, 2)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load user analytics: {str(e)}")
