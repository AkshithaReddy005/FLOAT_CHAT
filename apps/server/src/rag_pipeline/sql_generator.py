"""
SQL Query Generation Module
Generates SQL queries from natural language using LLM or rule-based approaches.
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

load_dotenv()


class SQLGenerator:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_SQL_MODEL", "gemini-2.0-flash")
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel(self.gemini_model)
                self.use_gemini = True
                print(f"SQL Generator: Gemini enabled with model {self.gemini_model}")
            except Exception as e:
                print(f"SQL Generator: Failed to initialize Gemini: {e}")
                self.use_gemini = False
        else:
            self.use_gemini = False
            print("SQL Generator: Using rule-based approach only")
    
    async def generate_sql(self, user_query: str, query_classification: Dict, 
                          context_results: Dict = None, session_context: dict = None) -> Optional[str]:
        """Generate SQL query based on user input and classification"""
        
        if self.use_gemini and query_classification.get("is_complex", False):
            # Use LLM for complex queries
            return await self._generate_with_gemini(user_query, context_results, session_context)
        else:
            # Use rule-based approach for simple queries
            return self._generate_rule_based(user_query, query_classification, session_context)
    
    async def generate_sql_from_context(self, parameter_context) -> Optional[str]:
        """Generate SQL query from unified parameter context (NEW UNIFIED METHOD)"""
        
        # Always use rule-based generation for comparative queries to ensure
        # deterministic region-wise aggregation SQL is produced.
        if getattr(parameter_context, "is_comparative", False):
            return self._generate_rule_based_from_context(parameter_context)
        
        if self.use_gemini and parameter_context.complexity_level == "complex":
            # Use LLM for complex queries (non-comparative)
            return await self._generate_with_gemini_from_context(parameter_context)
        else:
            # Use rule-based approach for simple queries
            return self._generate_rule_based_from_context(parameter_context)
    
    async def _generate_with_gemini_from_context(self, parameter_context) -> Optional[str]:
        """Generate SQL using Gemini LLM from parameter context"""
        
        # Build prompt from parameter context
        context_summary = f"Parameters: {parameter_context.get_summary()}"
        
        instruction = f"""Generate PostgreSQL query for ARGO oceanographic data.

Database: argo_measurements (float_id, latitude, longitude, date, depth, temperature, salinity, pressure)

Query: {parameter_context.original_query}
{context_summary}

Generate ONLY the SQL query:"""

        try:
            response = self.model.generate_content(
                instruction,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=300
                )
            )
            
            if response and hasattr(response, 'text') and response.text:
                sql = response.text.strip().replace('```sql', '').replace('```', '').strip()
                return sql
            return None
        except Exception as e:
            print(f"Gemini SQL generation failed: {e}")
            return None
    
    async def _generate_with_gemini(self, user_query: str, context_results: Dict = None, session_context: dict = None) -> Optional[str]:
        """Generate SQL using Gemini LLM"""
        
        # Extract context information if available
        context_summary = ""
        if context_results and context_results.get('documents'):
            context_docs = context_results.get('documents', [[]])[0][:2]
            if context_docs:
                context_summary = f"Context from database: {'; '.join(context_docs)}"
        
        # Add session context for better query continuity
        session_summary = ""
        if session_context:
            locations = session_context.get('key_context', {}).get('locations', [])
            data_types = session_context.get('key_context', {}).get('data_types', [])
            recent_focus = session_context.get('key_context', {}).get('recent_focus', [])
            
            if locations:
                session_summary += f"Previously discussed locations: {', '.join(locations[-3:])}\n"
            if data_types:
                session_summary += f"Data types of interest: {', '.join(data_types[-3:])}\n"
            if recent_focus:
                session_summary += f"Recent queries: {'; '.join(recent_focus[-2:])}\n"
        
        instruction = f"""You are an expert in ARGO oceanographic data analysis. Generate a PostgreSQL query for the user's question.

Database Schema:
Table: argo_measurements
Columns: id, float_id, latitude, longitude, date, depth, temperature, salinity, pressure

Advanced Query Patterns:
1. COMPARATIVE ANALYSIS: Use subqueries or CTEs for area comparisons
2. STATISTICAL OPERATIONS: AVG, MIN, MAX, COUNT, STDDEV, PERCENTILE_CONT
3. GEOSPATIAL FILTERING: Use BETWEEN for lat/lon ranges
4. TEMPORAL ANALYSIS: GROUP BY date components, date ranges
5. DEPTH STRATIFICATION: GROUP BY depth ranges or specific depths
6. CORRELATION ANALYSIS: Multiple parameters with statistical functions

Rules:
- ONLY SELECT from argo_measurements table
- Use explicit column names: float_id, latitude, longitude, date, depth, temperature, salinity, pressure
- For area comparisons, use subqueries or CASE statements
- Support advanced aggregations: PERCENTILE_CONT(0.5) for median, STDDEV for std deviation
- Use CTEs (WITH clause) for complex multi-step queries
- Always include ORDER BY for meaningful sorting
- Always include LIMIT (max 1500 for complex comparative queries, 500 for simple)
- For location queries: Mumbai ≈ 19°N, 73°E, Arabian Sea ≈ 15-25°N, 65-75°E
- Handle NULL values explicitly in aggregations

{context_summary}

{session_summary}

IMPORTANT for Session Context:
- If user asks "what about below 1000m" or similar relative queries, consider previous location context
- Use session context to infer missing parameters (location, depth ranges, data types)
- For queries like "below X meters", combine with previous location context

Advanced Examples:
- "Average temperature difference between areas": 
  WITH area1 AS (SELECT AVG(temperature) as avg_temp FROM argo_measurements WHERE latitude BETWEEN 18 AND 20 AND longitude BETWEEN 72 AND 74),
  area2 AS (SELECT AVG(temperature) as avg_temp FROM argo_measurements WHERE latitude BETWEEN 15 AND 17 AND longitude BETWEEN 70 AND 72)
  SELECT area1.avg_temp - area2.avg_temp as temp_difference FROM area1, area2

- "Temperature by depth ranges": 
  SELECT 
    CASE WHEN depth < 50 THEN 'Surface' WHEN depth < 200 THEN 'Thermocline' ELSE 'Deep' END as depth_category,
    AVG(temperature) as avg_temp, COUNT(*) as measurements
  FROM argo_measurements WHERE temperature IS NOT NULL
  GROUP BY CASE WHEN depth < 50 THEN 'Surface' WHEN depth < 200 THEN 'Thermocline' ELSE 'Deep' END
  ORDER BY avg_temp DESC

- "Correlation between temperature and depth":
  SELECT depth, temperature, CORR(temperature, depth) OVER() as correlation
  FROM argo_measurements WHERE temperature IS NOT NULL AND depth IS NOT NULL LIMIT 1000

User Query: {user_query}

Generate ONLY the SQL query (no explanation or markdown):"""

        try:
            response = self.model.generate_content(
                instruction,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=300
                )
            )
            
            # Enhanced response validation and safety handling
            if response:
                # Check if response was blocked or filtered
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        if finish_reason in [2, 3, 4]:  # SAFETY, RECITATION, OTHER
                            print(f"SQL Generator: Response blocked (reason: {finish_reason}), using rule-based approach")
                            return None
                
                # Try to get text, handle various response structures
                response_text = None
                try:
                    if hasattr(response, 'text') and response.text:
                        response_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        # Try to get text from first candidate
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_text = part.text
                                        break
                except Exception as text_extract_error:
                    print(f"SQL Generator: Error extracting text from response: {text_extract_error}")
                
                # Validate and clean extracted text
                if response_text and len(response_text.strip()) > 5:
                    sql = response_text.strip()
                    # Clean up any markdown formatting
                    sql = sql.replace('```sql', '').replace('```', '').strip()
                    return sql
                else:
                    print("SQL Generator: Gemini returned empty or very short response")
                    return None
            else:
                print("SQL Generator: No response from Gemini")
                return None
                
        except Exception as e:
            print(f"Failed to generate SQL with Gemini: {e}")
            return None
    
    def _generate_rule_based_from_context(self, parameter_context) -> Optional[str]:
        """Generate SQL using rule-based approach from parameter context"""
        
        # Build SQL components from parameter context
        select_clause = "SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure"
        where_conditions = []
        
        # Location filter
        if parameter_context.location_bounds:
            bounds = parameter_context.location_bounds
            where_conditions.append(f"latitude BETWEEN {bounds['lat_min']} AND {bounds['lat_max']}")
            where_conditions.append(f"longitude BETWEEN {bounds['lon_min']} AND {bounds['lon_max']}")
        
        # Temporal filter
        if parameter_context.date_years:
            # Year comparison logic using half-open intervals [start, end)
            year_conditions = [
                f"(date >= '{year}-01-01' AND date < '{year + 1}-01-01')" for year in parameter_context.date_years
            ]
            where_conditions.append(f"({' OR '.join(year_conditions)})")
        elif parameter_context.date_range:
            start_date, end_date = parameter_context.date_range
            # Use half-open interval [start, end_next) to include the full end day
            try:
                end_exclusive = (end_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            except Exception:
                end_exclusive = end_date
            where_conditions.append(f"date >= '{start_date.isoformat()}'")
            where_conditions.append(f"date < '{end_exclusive.isoformat()}'")
        
        # Depth filter
        if parameter_context.depth_range:
            if parameter_context.depth_type == 'operator':
                operator, value = parameter_context.depth_range
                where_conditions.append(f"depth {operator} {value}")
            else:
                min_depth, max_depth = parameter_context.depth_range
                where_conditions.append(f"depth BETWEEN {min_depth} AND {max_depth}")
        
        # Parameter filter
        if parameter_context.parameters:
            for param in parameter_context.parameters:
                where_conditions.append(f"{param} IS NOT NULL")

        # Temperature threshold filter - FIXED
        if parameter_context.temperature_range:
            operator, temp_value = parameter_context.temperature_range
            where_conditions.append(f"temperature {operator} {temp_value}")
            where_conditions.append(f"temperature IS NOT NULL")

        # Salinity threshold filter - FIXED
        if parameter_context.salinity_range:
            operator, sal_value = parameter_context.salinity_range
            where_conditions.append(f"salinity {operator} {sal_value}")
            where_conditions.append(f"salinity IS NOT NULL")

        # Float ID filter
        if parameter_context.float_ids:
            float_list = "', '".join(parameter_context.float_ids)
            where_conditions.append(f"float_id IN ('{float_list}')")
        
        # Build final query
        sql = select_clause + " FROM argo_measurements"
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
        
        # Handle analytical queries
        if parameter_context.is_analytical:
            if parameter_context.parameters:
                # Special case: correlation between temperature and salinity
                oq = (parameter_context.original_query or "").lower()
                has_temp = 'temperature' in parameter_context.parameters
                has_sal = 'salinity' in parameter_context.parameters
                if 'correlation' in oq and has_temp and has_sal:
                    # Build WHERE with existing conditions plus non-null checks
                    where_clauses = list(where_conditions) if where_conditions else []
                    where_clauses.append("temperature IS NOT NULL")
                    where_clauses.append("salinity IS NOT NULL")
                    sql = "SELECT corr(temperature, salinity) AS corr_temp_sal, COUNT(*) AS count FROM argo_measurements"
                    if where_clauses:
                        sql += " WHERE " + " AND ".join(where_clauses)
                    return sql
                
                param = parameter_context.parameters[0]
                
                # Handle comparative queries with regional breakdown
                if parameter_context.is_comparative and parameter_context.coordinate_precision == "comparative":
                    # Extract the two locations from location_name
                    locations = parameter_context.location_name.split("_vs_")
                    if len(locations) == 2:
                        loc1_bounds = self._get_location_bounds_from_name(locations[0])
                        loc2_bounds = self._get_location_bounds_from_name(locations[1])
                        
                        if loc1_bounds and loc2_bounds:
                            sql = f"""
                            SELECT 
                                CASE 
                                    WHEN latitude BETWEEN {loc1_bounds['lat_min']} AND {loc1_bounds['lat_max']} 
                                         AND longitude BETWEEN {loc1_bounds['lon_min']} AND {loc1_bounds['lon_max']} 
                                    THEN '{locations[0].replace('_', ' ').title()}'
                                    WHEN latitude BETWEEN {loc2_bounds['lat_min']} AND {loc2_bounds['lat_max']} 
                                         AND longitude BETWEEN {loc2_bounds['lon_min']} AND {loc2_bounds['lon_max']} 
                                    THEN '{locations[1].replace('_', ' ').title()}'
                                    ELSE 'Other'
                                END as region,
                                AVG({param}) as avg_{param}, 
                                MIN({param}) as min_{param}, 
                                MAX({param}) as max_{param}, 
                                STDDEV({param}) as stddev_{param}, 
                                COUNT(*) as count 
                            FROM argo_measurements 
                            WHERE {param} IS NOT NULL
                            GROUP BY region
                            HAVING region != 'Other'
                            ORDER BY region
                            """
                            return sql.strip()
                
                # Regular analytical query
                sql = f"SELECT AVG({param}) as avg_{param}, MIN({param}) as min_{param}, MAX({param}) as max_{param}, STDDEV({param}) as stddev_{param}, COUNT(*) as count FROM argo_measurements"
                if where_conditions:
                    sql += " WHERE " + " AND ".join(where_conditions)
                # No ORDER BY or LIMIT for aggregation queries
                return sql
        
        # Add ORDER BY and LIMIT for non-analytical queries
        sql += " ORDER BY date DESC"

        # Determine appropriate limit based on query type and data availability
        if parameter_context.is_full_data_request:
            # For full knowledge base requests, allow comprehensive data access
            limit = 8000  # Allow full dataset exploration
        elif parameter_context.complexity_level == "complex":
            limit = 3000  # More data for complex analysis
        else:
            limit = 1500  # Reasonable default for standard queries

        sql += f" LIMIT {limit}"

        return sql
    
    def _get_location_bounds_from_name(self, location_name: str) -> Optional[Dict]:
        """Get location bounds from location name"""
        location_bounds = {
            "mumbai": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "bombay": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "arabian sea": {"lat_min": 10, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "indian ocean": {"lat_min": -40, "lat_max": 30, "lon_min": 20, "lon_max": 120},
            "northern arabian sea": {"lat_min": 20, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "southern arabian sea": {"lat_min": 10, "lat_max": 20, "lon_min": 65, "lon_max": 75},
            "coastal": {"lat_min": 18, "lat_max": 22, "lon_min": 70, "lon_max": 74},
            "offshore": {"lat_min": 15, "lat_max": 25, "lon_min": 65, "lon_max": 72}
        }
        return location_bounds.get(location_name.lower().strip())
    
    def _generate_rule_based(self, user_query: str, query_classification: Dict, session_context: dict = None) -> Optional[str]:
        """Generate SQL using rule-based approach"""
        query_lower = user_query.lower()
        
        # Check for comparative queries first
        if self._is_comparative_query(query_lower):
            return self._generate_comparative_query(query_lower, query_classification, session_context)
        
        # Extract parameters with session context support
        params = self._extract_parameters(query_lower, session_context)
        
        # Build SQL components
        select_clause = "SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure"
        where_conditions = []
        
        # Add location filter
        if params.get("location"):
            location_bounds = self._get_location_bounds(params["location"])
            if location_bounds:
                where_conditions.append(
                    f"latitude BETWEEN {location_bounds['lat_min']} AND {location_bounds['lat_max']}"
                )
                where_conditions.append(
                    f"longitude BETWEEN {location_bounds['lon_min']} AND {location_bounds['lon_max']}"
                )
        
        # Add date filter
        if params.get("date_range"):
            start_date, end_date = params["date_range"]
            where_conditions.append(f"date >= '{start_date.isoformat()}'")
            where_conditions.append(f"date <= '{end_date.isoformat()}'")
        
        # Add depth filter with enhanced operators
        if params.get("depth_range"):
            depth_range = params["depth_range"]
            if isinstance(depth_range[0], str):  # Operator-based depth filtering
                operator, depth_value = depth_range
                where_conditions.append(f"depth {operator} {depth_value}")
            else:  # Range-based depth filtering
                depth_start, depth_end = depth_range
                where_conditions.append(f"depth BETWEEN {depth_start} AND {depth_end}")

        # Add temperature threshold filter - FIXED
        if params.get("temperature_range"):
            operator, temp_value = params["temperature_range"]
            where_conditions.append(f"temperature {operator} {temp_value}")
            where_conditions.append(f"temperature IS NOT NULL")

        # Add salinity threshold filter - FIXED
        if params.get("salinity_range"):
            operator, sal_value = params["salinity_range"]
            where_conditions.append(f"salinity {operator} {sal_value}")
            where_conditions.append(f"salinity IS NOT NULL")

        # Add parameter filter (temperature, salinity, etc.)
        if params.get("parameter"):
            param_name = params["parameter"]
            where_conditions.append(f"{param_name} IS NOT NULL")
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Handle sophisticated analytical queries
        if query_classification.get("is_analytical"):
            select_clause = self._build_analytical_select(query_lower, params)
        
        # Handle depth stratification queries
        if "depth" in query_lower and any(word in query_lower for word in ["profile", "layer", "stratif"]):
            select_clause = self._build_depth_profile_select(params)
            where_conditions = [f"{params.get('parameter', 'temperature')} IS NOT NULL"]
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Build final query
        sql = f"{select_clause} FROM argo_measurements"
        if where_clause:
            sql += f" {where_clause}"
        
        # Add GROUP BY if needed
        if "CASE WHEN" in select_clause or "GROUP BY" in query_lower:
            if "depth" in select_clause and "depth_category" in select_clause:
                sql += " GROUP BY CASE WHEN depth < 50 THEN 'Surface' WHEN depth < 200 THEN 'Thermocline' ELSE 'Deep' END"
        
        # Add ORDER BY
        if not query_classification.get("is_analytical") or "ORDER BY" not in sql:
            if "avg_" in select_clause or "COUNT" in select_clause:
                sql += " ORDER BY COUNT(*) DESC"
            else:
                sql += " ORDER BY date DESC"
        
        # Add LIMIT - increased for better data coverage
        limit = 1500 if query_classification.get("is_complex") else 800
        sql += f" LIMIT {limit}"
        
        return sql
    
    def _extract_parameters(self, query_lower: str, session_context: dict = None) -> Dict:
        """Extract parameters from query text with session context support"""
        params = {}

        # Extract location
        location_patterns = [
            r"mumbai",
            r"bombay",
            r"near\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"in\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"around\s+([a-zA-Z\s]+?)(?:\s|$)"
        ]

        location_found = False
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if pattern in ["mumbai", "bombay"]:
                    params["location"] = "mumbai"
                else:
                    params["location"] = match.group(1).strip()
                location_found = True
                break

        # If no explicit location found, use session context for relative queries
        if not location_found and session_context:
            relative_indicators = ["below", "above", "deeper", "shallower", "there", "that area", "same area"]
            if any(indicator in query_lower for indicator in relative_indicators):
                recent_locations = session_context.get('key_context', {}).get('locations', [])
                if recent_locations:
                    # Use the most recent location from session
                    for location in reversed(recent_locations):
                        if location.lower() in ["mumbai", "bombay", "arabian sea", "indian ocean"]:
                            params["location"] = location.lower()
                            print(f"Using session context location: {params['location']} for query: {query_lower}")
                            break

        # Extract date information
        if "march" in query_lower and "2023" in query_lower:
            params["date_range"] = (datetime(2023, 3, 1), datetime(2023, 4, 1))
        elif "2023" in query_lower:
            params["date_range"] = (datetime(2023, 1, 1), datetime(2024, 1, 1))

        # Extract depth with better pattern matching
        depth_patterns = [
            r"below\s*(\d+)\s*m",      # "below 1000m"
            r"above\s*(\d+)\s*m",      # "above 500m"
            r"deeper\s*than\s*(\d+)",  # "deeper than 1000"
            r"shallower\s*than\s*(\d+)", # "shallower than 500"
            r"greater\s*than\s*(\d+)\s*m", # "greater than 200m"
            r"depth.*greater.*than.*(\d+)", # "depth greater than 200m"
            r"depth\s*(\d+)",          # "depth 1000"
            r"(\d+)\s*m.*deep",        # "1000m deep"
            r"at\s*(\d+)\s*m"          # "at 1000m"
        ]

        for i, pattern in enumerate(depth_patterns):
            match = re.search(pattern, query_lower)
            if match:
                depth = float(match.group(1))
                if i == 0:  # below X meters (shallower)
                    params["depth_range"] = ("<=", depth)
                elif i == 1:  # above X meters (deeper)
                    params["depth_range"] = (">=", depth)
                elif i == 2:  # deeper than X
                    params["depth_range"] = (">=", depth)
                elif i == 3:  # shallower than X
                    params["depth_range"] = ("<=", depth)
                elif i == 4:  # greater than X meters
                    params["depth_range"] = (">=", depth)
                elif i == 5:  # depth greater than X
                    params["depth_range"] = (">=", depth)
                else:  # specific depth or range
                    params["depth_range"] = (depth - 50, depth + 50)
                break

        # Extract temperature thresholds - FIXED: Add temperature value filters
        temp_patterns = [
            r"temperature\s*(?:is\s*)?(?:less\s+than|below|under)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?",  # "temperature less than 20°C"
            r"temperature\s*(?:is\s*)?(?:greater\s+than|above|over)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?", # "temperature greater than 25°C"
            r"temps?\s*(?:less\s+than|below|under)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?",  # "temp below 20°C"
            r"temps?\s*(?:greater\s+than|above|over)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?", # "temp above 25°C"
            r"(?:where|with|having)\s+temperature\s*[<]\s*(\d+(?:\.\d+)?)", # "where temperature < 20"
            r"(?:where|with|having)\s+temperature\s*[>]\s*(\d+(?:\.\d+)?)", # "where temperature > 20"
        ]

        for i, pattern in enumerate(temp_patterns):
            match = re.search(pattern, query_lower)
            if match:
                temp_value = float(match.group(1))
                if i in [0, 2, 4]:  # less than/below patterns
                    params["temperature_range"] = ("<", temp_value)
                else:  # greater than/above patterns
                    params["temperature_range"] = (">", temp_value)
                break

        # Extract salinity thresholds
        sal_patterns = [
            r"salinity\s*(?:is\s*)?(?:less\s+than|below|under)\s*(\d+(?:\.\d+)?)",  # "salinity less than 35"
            r"salinity\s*(?:is\s*)?(?:greater\s+than|above|over)\s*(\d+(?:\.\d+)?)", # "salinity greater than 35"
            r"(?:where|with|having)\s+salinity\s*[<]\s*(\d+(?:\.\d+)?)", # "where salinity < 35"
            r"(?:where|with|having)\s+salinity\s*[>]\s*(\d+(?:\.\d+)?)", # "where salinity > 35"
        ]

        for i, pattern in enumerate(sal_patterns):
            match = re.search(pattern, query_lower)
            if match:
                sal_value = float(match.group(1))
                if i in [0, 2]:  # less than/below patterns
                    params["salinity_range"] = ("<", sal_value)
                else:  # greater than/above patterns
                    params["salinity_range"] = (">", sal_value)
                break

        # Extract parameter type
        if "temperature" in query_lower:
            params["parameter"] = "temperature"
        elif "salinity" in query_lower:
            params["parameter"] = "salinity"
        elif "pressure" in query_lower:
            params["parameter"] = "pressure"

        return params
    
    def _get_location_bounds(self, location: str) -> Optional[Dict]:
        """Get geographic bounds for known locations"""
        location_lower = location.lower().strip()
        
        # Known locations
        locations = {
            "mumbai": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "arabian sea": {"lat_min": 10, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "indian ocean": {"lat_min": -40, "lat_max": 30, "lon_min": 20, "lon_max": 120}
        }
        
        for loc_name, bounds in locations.items():
            if loc_name in location_lower:
                return bounds
        
        return None
    
    def _is_comparative_query(self, query_lower: str) -> bool:
        """Check if query involves area/location comparison"""
        comparison_patterns = [
            "vs", "versus", "compared to", "compare", "difference between",
            "warmer than", "cooler than", "saltier than", "difference in",
            "area vs area", "region vs region", "this area vs that area"
        ]
        return any(pattern in query_lower for pattern in comparison_patterns)
    
    def _generate_comparative_query(self, query_lower: str, query_classification: Dict = None, session_context: dict = None) -> Optional[str]:
        """Generate SQL for comparative analysis between areas/conditions"""
        
        # Extract comparison type
        if "temperature" in query_lower:
            param = "temperature"
        elif "salinity" in query_lower:
            param = "salinity"
        else:
            param = "temperature"  # default
        
        # Try to identify two areas for comparison
        areas = self._extract_comparison_areas(query_lower)
        
        if len(areas) >= 2:
            area1, area2 = areas[0], areas[1]
            
            # Build CTE-based comparative query
            sql = f"""
            WITH area1 AS (
                SELECT AVG({param}) as avg_value, COUNT(*) as count
                FROM argo_measurements 
                WHERE {param} IS NOT NULL 
                AND latitude BETWEEN {area1['lat_min']} AND {area1['lat_max']}
                AND longitude BETWEEN {area1['lon_min']} AND {area1['lon_max']}
            ),
            area2 AS (
                SELECT AVG({param}) as avg_value, COUNT(*) as count
                FROM argo_measurements 
                WHERE {param} IS NOT NULL
                AND latitude BETWEEN {area2['lat_min']} AND {area2['lat_max']}
                AND longitude BETWEEN {area2['lon_min']} AND {area2['lon_max']}
            )
            SELECT 
                area1.avg_value as area1_avg_{param},
                area2.avg_value as area2_avg_{param},
                (area1.avg_value - area2.avg_value) as {param}_difference,
                area1.count as area1_measurements,
                area2.count as area2_measurements
            FROM area1, area2
            """.strip()
            
            return sql
        
        return None
    
    def _extract_comparison_areas(self, query_lower: str) -> List[Dict]:
        """Extract areas for comparison from query"""
        areas = []
        
        # Default area definitions for common comparisons
        known_areas = {
            "mumbai": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "arabian sea": {"lat_min": 15, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "northern arabian sea": {"lat_min": 20, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "southern arabian sea": {"lat_min": 10, "lat_max": 20, "lon_min": 65, "lon_max": 75},
            "coastal": {"lat_min": 18, "lat_max": 22, "lon_min": 70, "lon_max": 74},
            "offshore": {"lat_min": 15, "lat_max": 25, "lon_min": 65, "lon_max": 72}
        }
        
        for area_name, bounds in known_areas.items():
            if area_name in query_lower:
                areas.append(bounds)
        
        # If we don't have 2 areas, create default comparison
        if len(areas) < 2:
            areas = [
                {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},  # Mumbai area
                {"lat_min": 15, "lat_max": 17, "lon_min": 68, "lon_max": 70}   # Southern area
            ]
        
        return areas[:2]  # Return only first 2 areas
    
    def _build_analytical_select(self, query_lower: str, params: Dict) -> str:
        """Build sophisticated analytical SELECT clause"""
        
        if "difference" in query_lower and "average" in query_lower:
            param = params.get("parameter", "temperature")
            return f"SELECT AVG({param}) as avg_{param}, STDDEV({param}) as std_{param}, COUNT(*) as count"
        elif "correlation" in query_lower:
            return "SELECT CORR(temperature, depth) as temp_depth_corr, CORR(salinity, depth) as sal_depth_corr, COUNT(*) as measurements"
        elif "percentile" in query_lower or "median" in query_lower:
            param = params.get("parameter", "temperature")
            return f"SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {param}) as q25, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {param}) as median, PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {param}) as q75"
        elif "average" in query_lower or "mean" in query_lower:
            if params.get("parameter"):
                param = params["parameter"]
                return f"SELECT AVG({param}) as avg_{param}, MIN({param}) as min_{param}, MAX({param}) as max_{param}, COUNT(*) as count"
            else:
                return "SELECT AVG(temperature) as avg_temp, AVG(salinity) as avg_sal, COUNT(*) as count"
        elif "maximum" in query_lower or "max" in query_lower:
            return "SELECT MAX(temperature) as max_temp, MAX(salinity) as max_sal, MAX(depth) as max_depth, float_id, latitude, longitude"
        elif "minimum" in query_lower or "min" in query_lower:
            return "SELECT MIN(temperature) as min_temp, MIN(salinity) as min_sal, MIN(depth) as min_depth, float_id, latitude, longitude"
        else:
            param = params.get("parameter", "temperature")
            return f"SELECT AVG({param}) as avg_{param}, COUNT(*) as count"
    
    def _build_depth_profile_select(self, params: Dict) -> str:
        """Build depth profile SELECT clause"""
        param = params.get("parameter", "temperature")
        return f"""SELECT 
            CASE 
                WHEN depth < 50 THEN 'Surface (0-50m)'
                WHEN depth < 200 THEN 'Thermocline (50-200m)' 
                WHEN depth < 1000 THEN 'Intermediate (200-1000m)'
                ELSE 'Deep (>1000m)'
            END as depth_category,
            AVG({param}) as avg_{param},
            MIN({param}) as min_{param},
            MAX({param}) as max_{param},
            COUNT(*) as measurements"""
    
    def validate_sql(self, sql: str) -> bool:
        """Validate that the SQL is safe to execute"""
        if not sql:
            return False
        
        # Clean and normalize SQL
        sql_clean = sql.strip().strip(';').lower()
        # Remove comments and normalize whitespace
        sql_clean = re.sub(r'--[^\n]*', '', sql_clean)  # Remove -- comments
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # Remove /* */ comments
        sql_clean = re.sub(r'\s+', ' ', sql_clean)  # Normalize whitespace
        
        # Must start with SELECT or WITH (for CTEs)
        if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
            return False
        
        # Must reference only argo_measurements table
        if "from argo_measurements" not in sql_clean:
            return False
        
        # Disallow dangerous keywords (excluding -- since we removed comments)
        forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", ";", "create", "grant", "revoke"]
        if any(keyword in sql_clean for keyword in forbidden):
            return False
        
        
        # Must have LIMIT (unless it's a CTE with aggregation only)
        if "limit" not in sql_clean:
            # Allow CTEs that only return aggregated results (no raw data)
            if not ("with" in sql_clean and any(agg in sql_clean for agg in ["avg(", "count(", "sum(", "max(", "min("])):
                return False
        
        # Check for reasonable LIMIT values when present
        limit_match = re.search(r'limit\s+(\d+)', sql_clean)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > 10000:  # Allow much higher limits for comprehensive data requests
                return False
        
        # Validate CTE structure if present
        if "with" in sql_clean:
            if not self._validate_cte_structure(sql_clean):
                return False
        
        return True
    
    def _validate_cte_structure(self, sql_clean: str) -> bool:
        """Validate CTE (Common Table Expression) structure"""
        # Basic CTE validation
        with_count = sql_clean.count("with")
        
        # Check for CTE pattern: WITH name AS (...)
        if with_count > 0:
            # Look for proper CTE syntax
            if " as (" not in sql_clean and " as(" not in sql_clean:
                return False
        
        # Check for properly closed parentheses in CTE
        paren_count = sql_clean.count("(") - sql_clean.count(")")
        if paren_count != 0:
            return False
        
        # Ensure final SELECT statement exists
        if with_count > 0:
            # Should have a final SELECT after the CTEs
            parts = sql_clean.split("select")
            if len(parts) < 2:  # WITH clause + final SELECT
                return False
        
        return True