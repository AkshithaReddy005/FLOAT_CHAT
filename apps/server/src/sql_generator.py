"""
SQL Query Generation Module
Generates SQL queries from natural language using LLM or rule-based approaches.
"""

import os
import re
from typing import Dict, Optional
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

Rules:
- ONLY SELECT from argo_measurements table
- Use explicit column names: float_id, latitude, longitude, date, depth, temperature, salinity, pressure
- For statistical queries, use aggregation functions (AVG, MIN, MAX, COUNT, STDDEV, etc.)
- Support GROUP BY for grouping, HAVING for filtering groups
- Use appropriate WHERE clauses for filtering
- Always include ORDER BY for meaningful sorting
- Always include LIMIT (max 1000 for complex queries, 500 for simple)
- For location queries near cities: Mumbai ≈ 19°N, 73°E (use BETWEEN for ranges)
- For depth analysis: surface (0-10m), thermocline (50-200m), deep (>500m)
- Handle date ranges properly with DATE casting if needed

{context_summary}

Examples:
- "Average temperature": SELECT AVG(temperature) as avg_temp, COUNT(*) as measurements FROM argo_measurements WHERE temperature IS NOT NULL
- "Temperature by depth": SELECT depth, AVG(temperature) as avg_temp FROM argo_measurements GROUP BY depth ORDER BY depth LIMIT 500
- "Floats near Mumbai": SELECT DISTINCT float_id, latitude, longitude FROM argo_measurements WHERE latitude BETWEEN 18 AND 20 AND longitude BETWEEN 72 AND 74

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
        
        # Handle analytical queries
        if query_classification.get("is_analytical"):
            if "average" in query_lower or "mean" in query_lower:
                if params.get("parameter"):
                    param = params["parameter"]
                    select_clause = f"SELECT AVG({param}) as avg_{param}, COUNT(*) as count"
                else:
                    select_clause = "SELECT AVG(temperature) as avg_temp, AVG(salinity) as avg_sal, COUNT(*) as count"
            elif "maximum" in query_lower or "max" in query_lower:
                select_clause = "SELECT MAX(temperature) as max_temp, MAX(salinity) as max_sal, MAX(depth) as max_depth"
            elif "minimum" in query_lower or "min" in query_lower:
                select_clause = "SELECT MIN(temperature) as min_temp, MIN(salinity) as min_sal, MIN(depth) as min_depth"
        
        # Build final query
        sql = f"{select_clause} FROM argo_measurements"
        if where_clause:
            sql += f" {where_clause}"
        
        # Add ORDER BY
        if not query_classification.get("is_analytical"):
            sql += " ORDER BY date DESC"
        
        # Add LIMIT
        sql += " LIMIT 500"
        
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
        
        # Must start with SELECT
        if not sql_clean.startswith("select"):
            return False
        
        # Must reference only argo_measurements table
        if "from argo_measurements" not in sql_clean:
            return False
        
        # Disallow dangerous keywords (excluding -- since we removed comments)
        forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", ";"]
        if any(keyword in sql_clean for keyword in forbidden):
            return False
        
        # Must have LIMIT
        if "limit" not in sql_clean:
            return False
        
        # Check for reasonable LIMIT values
        limit_match = re.search(r'limit\s+(\d+)', sql_clean)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > 2000:  # Prevent excessive data retrieval
                return False
        
        return True