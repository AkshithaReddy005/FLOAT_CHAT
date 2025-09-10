import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import requests

from database import ArgoMeasurement
from vector_store import VectorStore

# Try to import OpenAI, but make it optional
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not installed. Using rule-based responses only.")

load_dotenv()

class ChatbotService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize OpenAI client if API key is available and package is installed
        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                openai.api_key = self.openai_api_key
                self.use_openai = True
                print("OpenAI integration enabled")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI: {e}. Using rule-based responses.")
                self.use_openai = False
        else:
            self.use_openai = False
            if not OPENAI_AVAILABLE:
                print("Warning: OpenAI package not available. Using rule-based responses.")
            elif not self.openai_api_key:
                print("Warning: OPENAI_API_KEY not found. Using rule-based responses.")
    
    async def process_chat_query(self, user_query: str, db: Session) -> Dict:
        """Process a natural language query and return structured response"""
        
        # Step 1: Retrieve relevant context from ChromaDB
        context_results = self.vector_store.search(user_query, n_results=10)
        
        # Step 2: Extract query parameters using NLP or rule-based approach
        query_params = self._extract_query_parameters(user_query)
        
        # Step 3: Execute database query based on extracted parameters
        db_results = self._execute_database_query(db, query_params, context_results)
        
        # Step 4: Generate AI response using LLM (if available) or rule-based response
        if self.use_openai:
            ai_response = await self._generate_llm_response(user_query, context_results, db_results)
        else:
            ai_response = self._generate_rule_based_response(user_query, db_results)
        
        # Step 5: Prepare visualization data
        viz_data = self._prepare_visualization_data(db_results)
        
        return {
            "response": ai_response,
            "data": db_results,
            "visualization": viz_data,
            "query_params": query_params,
            "context_count": len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0
        }
    
    def _extract_query_parameters(self, query: str) -> Dict:
        """Extract query parameters from natural language using rule-based approach"""
        params = {
            "location": None,
            "date_range": None,
            "depth_range": None,
            "parameter": None,
            "float_id": None
        }
        
        query_lower = query.lower()
        
        # Extract location information with improved patterns
        location_patterns = [
            r"near\s+(?:the\s+)?([a-zA-Z\s]+?)(?:\s+in|\s+during|\s+for|$)",
            r"in\s+(?:the\s+)?([a-zA-Z\s]+?)(?:\s+during|\s+for|\s+in|\s+at|$)",
            r"around\s+([a-zA-Z\s]+?)(?:\s+in|\s+during|\s+for|$)",
            r"(?:at|in)\s+(?:the\s+)?([a-zA-Z\s]+ocean)(?:\s|$)",  # Better ocean detection
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location = match.group(1).strip()
                params["location"] = location
                break
        
        # Extract date information
        date_patterns = [
            r"before\s+(\d{4})",  # "before 2023"
            r"until\s+(\d{4})",  # "until 2023"
            r"after\s+(\d{4})",  # "after 2020"
            r"since\s+(\d{4})",  # "since 2020"
            r"in\s+(\w+)\s+(\d{4})",  # "in March 2023"
            r"during\s+(\w+)\s+(\d{4})",  # "during March 2023"
            r"from\s+(\w+)\s+(\d{4})",  # "from March 2023"
            r"in\s+(\d{4})",  # "in 2024"
            r"during\s+(\d{4})",  # "during 2024"
            r"from\s+(\d{4})",  # "from 2024"
            r"last\s+(\d+)\s+months?",  # "last 6 months"
            r"past\s+(\d+)\s+months?"   # "past 6 months"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if "before" in pattern or "until" in pattern:
                    # Handle "before 2023" - everything before that year
                    year = int(match.group(1))
                    start_date = datetime(1900, 1, 1)  # Very early date
                    end_date = datetime(year - 1, 12, 31, 23, 59, 59)  # End of previous year
                    params["date_range"] = (start_date, end_date)
                elif "after" in pattern or "since" in pattern:
                    # Handle "after 2020" - everything after that year
                    year = int(match.group(1))
                    start_date = datetime(year + 1, 1, 1)  # After the specified year
                    end_date = datetime.now()  # Until now
                    params["date_range"] = (start_date, end_date)
                elif "last" in pattern or "past" in pattern:
                    months_back = int(match.group(1))
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=months_back * 30)
                    params["date_range"] = (start_date, end_date)
                elif len(match.groups()) == 1 and match.group(1).isdigit():
                    # Handle standalone year patterns like "in 2024"
                    year = int(match.group(1))
                    start_date = datetime(year, 1, 1)
                    end_date = datetime(year + 1, 1, 1)
                    params["date_range"] = (start_date, end_date)
                else:
                    # Handle month + year patterns like "in March 2024"
                    month_name = match.group(1)
                    year = int(match.group(2))
                    month_map = {
                        "january": 1, "february": 2, "march": 3, "april": 4,
                        "may": 5, "june": 6, "july": 7, "august": 8,
                        "september": 9, "october": 10, "november": 11, "december": 12
                    }
                    if month_name in month_map:
                        start_date = datetime(year, month_map[month_name], 1)
                        if month_map[month_name] == 12:
                            end_date = datetime(year + 1, 1, 1)
                        else:
                            end_date = datetime(year, month_map[month_name] + 1, 1)
                        params["date_range"] = (start_date, end_date)
                break
        
        # Extract depth information
        depth_match = re.search(r"(?:depth|deep)\s*(?:of|at|between)?\s*(\d+)(?:\s*-\s*(\d+))?\s*m", query_lower)
        if depth_match:
            depth_start = float(depth_match.group(1))
            depth_end = float(depth_match.group(2)) if depth_match.group(2) else depth_start + 50
            params["depth_range"] = (depth_start, depth_end)
        
        # Extract parameter type
        parameter_keywords = {
            "temperature": ["temperature", "temp"],
            "salinity": ["salinity", "salt"],
            "pressure": ["pressure"],
            "bgc": ["bgc", "biochemical", "bio-geo-chemical"]
        }
        
        for param_type, keywords in parameter_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                params["parameter"] = param_type
                break
        
        # Extract float ID
        float_match = re.search(r"float\s+(\d+)", query_lower)
        if float_match:
            params["float_id"] = float_match.group(1)
        
        return params
    
    def _detect_location_bounds(self, location_name: str, db: Session) -> Optional[Dict]:
        """Detect location bounds using geocoding service and find ARGO data within those bounds"""
        if not db:
            return None
            
        # First, try to get actual coordinates for the location name using a geocoding service
        geocoded_bounds = self._geocode_location(location_name)
        
        if geocoded_bounds:
            # Check if we have ARGO data within these bounds
            argo_data_bounds = self._find_argo_data_in_bounds(db, geocoded_bounds)
            if argo_data_bounds:
                return argo_data_bounds
        
        # Fallback: if geocoding fails or no data in geocoded bounds, 
        # use the old clustering approach but with better logging
        logging.warning(f"Geocoding failed for '{location_name}', falling back to data clustering")
        return self._fallback_clustering_bounds(db)
    
    def _geocode_location(self, location_name: str) -> Optional[Dict]:
        """Get geographic bounds for a location name using Nominatim (OpenStreetMap) geocoding"""
        try:
            # Use Nominatim (free OpenStreetMap geocoding service)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location_name,
                'format': 'json',
                'limit': 1,
                'extratags': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'FloatChat-ARGO-System/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            if not results:
                return None
                
            result = results[0]
            
            # Extract bounding box if available
            if 'boundingbox' in result:
                bbox = result['boundingbox']
                # boundingbox format: [min_lat, max_lat, min_lon, max_lon]
                return {
                    "lat_range": (float(bbox[0]), float(bbox[1])),
                    "lon_range": (float(bbox[2]), float(bbox[3]))
                }
            else:
                # If no bounding box, create one around the point
                lat = float(result['lat'])
                lon = float(result['lon'])
                # Create a reasonable buffer (about 1 degree = ~111km)
                buffer = 1.0
                return {
                    "lat_range": (lat - buffer, lat + buffer),
                    "lon_range": (lon - buffer, lon + buffer)
                }
                
        except Exception as e:
            logging.error(f"Geocoding failed for '{location_name}': {e}")
            return None
    
    def _find_argo_data_in_bounds(self, db: Session, bounds: Dict) -> Optional[Dict]:
        """Find ARGO data within the specified geographic bounds"""
        try:
            lat_min, lat_max = bounds["lat_range"]
            lon_min, lon_max = bounds["lon_range"]
            
            # Query for measurements within these bounds
            measurements_in_bounds = db.query(ArgoMeasurement).filter(
                and_(
                    ArgoMeasurement.latitude >= lat_min,
                    ArgoMeasurement.latitude <= lat_max,
                    ArgoMeasurement.longitude >= lon_min,
                    ArgoMeasurement.longitude <= lon_max
                )
            ).all()
            
            if not measurements_in_bounds:
                return None
            
            # Calculate actual data bounds with some buffer
            actual_lats = [m.latitude for m in measurements_in_bounds if m.latitude is not None]
            actual_lons = [m.longitude for m in measurements_in_bounds if m.longitude is not None]
            
            if not actual_lats or not actual_lons:
                return None
            
            # Add 5% buffer around actual data
            lat_range = max(actual_lats) - min(actual_lats)
            lon_range = max(actual_lons) - min(actual_lons)
            lat_buffer = max(lat_range * 0.05, 0.1)  # At least 0.1 degree buffer
            lon_buffer = max(lon_range * 0.05, 0.1)
            
            return {
                "lat_range": (min(actual_lats) - lat_buffer, max(actual_lats) + lat_buffer),
                "lon_range": (min(actual_lons) - lon_buffer, max(actual_lons) + lon_buffer)
            }
            
        except Exception as e:
            logging.error(f"Error finding ARGO data in bounds: {e}")
            return None
    
    def _fallback_clustering_bounds(self, db: Session) -> Optional[Dict]:
        """Fallback method using data clustering when geocoding fails"""
        # Get all measurements
        all_measurements = db.query(ArgoMeasurement).all()
        
        if not all_measurements:
            return None
        
        # Extract coordinates
        coordinates = [(m.latitude, m.longitude) for m in all_measurements 
                      if m.latitude is not None and m.longitude is not None]
        
        if not coordinates:
            return None
        
        # Simple approach: find the region with highest data density
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]
        
        # Calculate center of mass of all data
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Find measurements within different radius sizes and pick the best concentration
        best_bounds = None
        best_density = 0
        
        # Try different radius sizes to find optimal data cluster
        for radius_factor in [0.1, 0.2, 0.3, 0.5, 0.8]:
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            
            radius_lat = lat_range * radius_factor
            radius_lon = lon_range * radius_factor
            
            # Count measurements within this radius from center
            cluster_measurements = [
                m for m in all_measurements
                if m.latitude and m.longitude and
                abs(m.latitude - center_lat) <= radius_lat and
                abs(m.longitude - center_lon) <= radius_lon
            ]
            
            if cluster_measurements:
                density = len(cluster_measurements) / (radius_lat * radius_lon)
                
                if density > best_density:
                    best_density = density
                    cluster_lats = [m.latitude for m in cluster_measurements]
                    cluster_lons = [m.longitude for m in cluster_measurements]
                    
                    # Add 10% buffer around the cluster
                    lat_buffer = (max(cluster_lats) - min(cluster_lats)) * 0.1
                    lon_buffer = (max(cluster_lons) - min(cluster_lons)) * 0.1
                    
                    best_bounds = {
                        "lat_range": (min(cluster_lats) - lat_buffer, max(cluster_lats) + lat_buffer),
                        "lon_range": (min(cluster_lons) - lon_buffer, max(cluster_lons) + lon_buffer)
                    }
        
        return best_bounds
    
    def _execute_database_query(self, db: Session, params: Dict, context_results: Dict) -> List[Dict]:
        """Execute database query based on extracted parameters"""
        query = db.query(ArgoMeasurement)
        
        # Apply location filter
        if params.get("location"):
            location_bounds = self._detect_location_bounds(params["location"], db)
            if location_bounds:
                query = query.filter(
                    and_(
                        ArgoMeasurement.latitude >= location_bounds["lat_range"][0],
                        ArgoMeasurement.latitude <= location_bounds["lat_range"][1],
                        ArgoMeasurement.longitude >= location_bounds["lon_range"][0],
                        ArgoMeasurement.longitude <= location_bounds["lon_range"][1]
                    )
                )
        
        # Apply date filter
        if params.get("date_range"):
            start_date, end_date = params["date_range"]
            query = query.filter(
                and_(
                    ArgoMeasurement.date >= start_date,
                    ArgoMeasurement.date <= end_date
                )
            )
        
        # Apply depth filter
        if params.get("depth_range"):
            depth_start, depth_end = params["depth_range"]
            query = query.filter(
                and_(
                    ArgoMeasurement.depth >= depth_start,
                    ArgoMeasurement.depth <= depth_end
                )
            )
        
        # Apply float ID filter
        if params.get("float_id"):
            query = query.filter(ArgoMeasurement.float_id == params["float_id"])
        
        # Execute query and convert to dict
        results = query.all()
        return [
            {
                "float_id": r.float_id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "date": r.date.isoformat() if r.date else None,
                "depth": r.depth,
                "temperature": r.temperature,
                "salinity": r.salinity,
                "pressure": r.pressure
            }
            for r in results
        ]
    
    async def _generate_llm_response(self, user_query: str, context_results: Dict, db_results: List[Dict]) -> str:
        """Generate response using OpenAI LLM with RAG"""
        
        # Prepare context from ChromaDB results
        context_docs = context_results.get('documents', [[]])[0][:5]  # Top 5 most relevant
        context_text = "\n".join(context_docs) if context_docs else "No relevant context found."
        
        # Prepare data summary
        data_summary = f"Found {len(db_results)} measurements"
        if db_results:
            temps_with_values = [r['temperature'] for r in db_results if r['temperature'] is not None]
            salinities_with_values = [r['salinity'] for r in db_results if r['salinity'] is not None]
            
            if temps_with_values:
                avg_temp = sum(temps_with_values) / len(temps_with_values)
                data_summary += f", average temperature {avg_temp:.2f}°C"
            
            if salinities_with_values:
                avg_sal = sum(salinities_with_values) / len(salinities_with_values)
                data_summary += f", average salinity {avg_sal:.2f}"
            
            if db_results:
                depth_range = (min(r['depth'] for r in db_results), max(r['depth'] for r in db_results))
                data_summary += f", depth range {depth_range[0]:.1f}-{depth_range[1]:.1f}m"
        
        # Create prompt for LLM
        prompt = f"""You are FloatChat, an AI assistant specialized in ARGO oceanographic data analysis. 
        
User Query: {user_query}

Relevant Context from Database:
{context_text}

Query Results Summary:
{data_summary}

Please provide a helpful, informative response about the oceanographic data. Include:
1. A direct answer to the user's question
2. Key insights from the data
3. Any notable patterns or observations
4. Suggestions for further exploration if relevant

Keep the response conversational but scientifically accurate."""

        try:
            # Try new OpenAI API format first
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are FloatChat, an expert oceanographic data analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except:
                # Fallback to old OpenAI API format
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are FloatChat, an expert oceanographic data analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_rule_based_response(user_query, db_results)
    
    def _generate_rule_based_response(self, user_query: str, db_results: List[Dict]) -> str:
        """Generate response using rule-based approach when LLM is not available"""
        
        if not db_results:
            return "I couldn't find any ARGO measurements matching your query. Try adjusting your search criteria or check if data is available for that location and time period."
        
        count = len(db_results)
        
        # Calculate basic statistics
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        
        response_parts = [f"I found {count} ARGO measurements matching your query."]
        
        if temps:
            avg_temp = sum(temps) / len(temps)
            min_temp, max_temp = min(temps), max(temps)
            response_parts.append(f"Temperature ranges from {min_temp:.2f}°C to {max_temp:.2f}°C (average: {avg_temp:.2f}°C).")
        
        if salinities:
            avg_sal = sum(salinities) / len(salinities)
            min_sal, max_sal = min(salinities), max(salinities)
            response_parts.append(f"Salinity ranges from {min_sal:.2f} to {max_sal:.2f} (average: {avg_sal:.2f}).")
        
        if depths:
            min_depth, max_depth = min(depths), max(depths)
            response_parts.append(f"Depth range: {min_depth:.1f}m to {max_depth:.1f}m.")
        
        # Add unique float count
        unique_floats = len(set(r['float_id'] for r in db_results))
        response_parts.append(f"Data comes from {unique_floats} different ARGO floats.")
        
        return " ".join(response_parts)
    
    def _prepare_visualization_data(self, db_results: List[Dict]) -> Dict:
        """Prepare data for frontend visualization"""
        if not db_results:
            return {"type": "empty"}
        
        # Prepare map data (locations of measurements)
        map_data = {
            "type": "map",
            "points": [
                {
                    "lat": r["latitude"],
                    "lon": r["longitude"],
                    "float_id": r["float_id"],
                    "temperature": r["temperature"],
                    "salinity": r["salinity"],
                    "depth": r["depth"],
                    "date": r["date"]
                }
                for r in db_results
            ]
        }
        
        # Prepare depth profile data
        depth_profile = {
            "type": "depth_profile",
            "data": [
                {
                    "depth": r["depth"],
                    "temperature": r["temperature"],
                    "salinity": r["salinity"],
                    "float_id": r["float_id"]
                }
                for r in db_results
            ]
        }
        
        # Prepare time series data
        time_series = {
            "type": "time_series",
            "data": [
                {
                    "date": r["date"],
                    "temperature": r["temperature"],
                    "salinity": r["salinity"],
                    "float_id": r["float_id"]
                }
                for r in db_results
                if r["date"]
            ]
        }
        
        return {
            "map": map_data,
            "depth_profile": depth_profile,
            "time_series": time_series,
            "summary": {
                "total_measurements": len(db_results),
                "unique_floats": len(set(r['float_id'] for r in db_results)),
                "date_range": {
                    "start": min(r["date"] for r in db_results if r["date"]),
                    "end": max(r["date"] for r in db_results if r["date"])
                } if any(r["date"] for r in db_results) else None
            }
        }
