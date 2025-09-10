"""
SQL Query Generation Module
Generates SQL queries from natural language using LLM or rule-based approaches.
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
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
        self.gemini_model = "gemini-2.0-flash"
        
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
                          context_results: Dict = None) -> Optional[str]:
        """Generate SQL query based on user input and classification"""
        
        if self.use_gemini and query_classification.get("is_complex", False):
            # Use LLM for complex queries
            return await self._generate_with_gemini(user_query, context_results)
        else:
            # Use rule-based approach for simple queries
            return self._generate_rule_based(user_query, query_classification)
    
    async def _generate_with_gemini(self, user_query: str, context_results: Dict = None) -> Optional[str]:
        """Generate SQL using Gemini LLM"""
        
        # Extract context information if available
        context_summary = ""
        if context_results and context_results.get('documents'):
            context_docs = context_results.get('documents', [[]])[0][:2]
            if context_docs:
                context_summary = f"Context from database: {'; '.join(context_docs)}"
        
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
            sql = response.text.strip()
            # Clean up any markdown formatting
            sql = sql.replace('```sql', '').replace('```', '').strip()
            return sql
        except Exception as e:
            print(f"Failed to generate SQL with Gemini: {e}")
            return None
    
    def _generate_rule_based(self, user_query: str, query_classification: Dict) -> Optional[str]:
        """Generate SQL using rule-based approach"""
        query_lower = user_query.lower()
        
        # Check for comparative queries first
        if self._is_comparative_query(query_lower):
            return self._generate_comparative_query(query_lower, query_classification)
        
        # Extract parameters
        params = self._extract_parameters(query_lower)
        
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
        
        # Add depth filter
        if params.get("depth_range"):
            depth_start, depth_end = params["depth_range"]
            where_conditions.append(f"depth BETWEEN {depth_start} AND {depth_end}")
        
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
        
        # Add LIMIT
        limit = 1000 if query_classification.get("is_complex") else 500
        sql += f" LIMIT {limit}"
        
        return sql
    
    def _extract_parameters(self, query_lower: str) -> Dict:
        """Extract parameters from query text"""
        params = {}
        
        # Extract location
        location_patterns = [
            r"near\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"in\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"around\s+([a-zA-Z\s]+?)(?:\s|$)"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                params["location"] = match.group(1).strip()
                break
        
        # Extract date information
        if "march" in query_lower and "2023" in query_lower:
            params["date_range"] = (datetime(2023, 3, 1), datetime(2023, 4, 1))
        elif "2023" in query_lower:
            params["date_range"] = (datetime(2023, 1, 1), datetime(2024, 1, 1))
        
        # Extract depth
        depth_match = re.search(r"depth\s*(\d+)", query_lower)
        if depth_match:
            depth = float(depth_match.group(1))
            params["depth_range"] = (depth - 25, depth + 25)
        
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
    
    def _generate_comparative_query(self, query_lower: str, query_classification: Dict) -> Optional[str]:
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
        
        # Allow sophisticated SQL patterns
        allowed_advanced = ["with", "cte", "case when", "percentile_cont", "corr", "stddev", "over()", "within group"]
        
        # Must have LIMIT (unless it's a CTE with aggregation only)
        if "limit" not in sql_clean:
            # Allow CTEs that only return aggregated results (no raw data)
            if not ("with" in sql_clean and any(agg in sql_clean for agg in ["avg(", "count(", "sum(", "max(", "min("])):
                return False
        
        # Check for reasonable LIMIT values when present
        limit_match = re.search(r'limit\s+(\d+)', sql_clean)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > 2000:  # Prevent excessive data retrieval
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