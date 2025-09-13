"""
LLM-based parameter extraction using structured prompting
"""

import json
import logging
from typing import Dict, Optional, Any
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMParameterExtractor:
    """Extract parameters using LLM with structured JSON schema"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def extract(self, user_query: str, session_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract parameters using LLM with strict JSON schema"""
        
        schema_prompt = self._build_schema_prompt(user_query, session_context)
        
        try:
            response = self.model.generate_content(
                schema_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=800
                )
            )
            
            if response and hasattr(response, 'text') and response.text:
                # Extract JSON from response
                json_text = self._extract_json(response.text)
                if json_text:
                    extracted = json.loads(json_text)
                    return self._validate_and_normalize(extracted, user_query)
            
            logger.warning(f"LLM extraction failed for query: {user_query}")
            return {"extraction_method": "llm_failed"}
            
        except Exception as e:
            logger.error(f"LLM parameter extraction error: {e}")
            return {"extraction_method": "llm_error", "error": str(e)}
    
    def _build_schema_prompt(self, user_query: str, session_context: Optional[Dict]) -> str:
        """Build structured prompt with JSON schema"""
        
        session_info = ""
        if session_context:
            recent_locations = session_context.get('key_context', {}).get('locations', [])
            if recent_locations:
                session_info = f"Recent locations discussed: {', '.join(recent_locations[-3:])}"
        
        return f"""Extract oceanographic query parameters as JSON ONLY. No explanations.

Query: "{user_query}"
{session_info}

Return JSON with this exact structure:
{{
    "location_name": null,
    "location_bounds": null,
    "date_range": null,
    "date_years": null,
    "depth_range": null,
    "depth_type": null,
    "parameters": [],
    "float_ids": null,
    "is_analytical": false,
    "is_comparative": false,
    "is_chart_request": false,
    "complexity_level": "simple"
}}

Rules:
- location_name: string like "arabian sea", "indian ocean", "mumbai" or null
- location_bounds: {{"lat_min": num, "lat_max": num, "lon_min": num, "lon_max": num}} or null
- date_range: ["YYYY-MM-DD", "YYYY-MM-DD"] or null
- date_years: [2022, 2023] or null
- depth_range: [">=", 200] for "greater than 200m", ["<=", 100] for "less than 100m", [100, 500] for ranges, or null
- depth_type: "operator" or "range" or null
- parameters: ["temperature"] or ["salinity"] or ["temperature", "salinity"] or []
- float_ids: ["FLOAT_000123"] or null
- is_analytical: true for average/mean/std/correlation/min/max queries
- is_comparative: true for "compare X and Y" or "X vs Y"
- is_chart_request: true for "plot", "chart", "graph", "visualize"
- complexity_level: "simple", "moderate", or "complex"

Depth extraction examples:
- "greater than 200m" → [">=", 200]
- "depth greater than 200m" → [">=", 200] 
- "deeper than 500m" → [">=", 500]
- "below 100m" → ["<=", 100]
- "shallower than 50m" → ["<=", 50]
- "between 100m and 500m" → [100, 500]
- "at 1000m depth" → [950, 1050]

Known regions with bounds:
- arabian sea: 10-25°N, 65-75°E
- indian ocean: -40-30°N, 20-120°E
- mumbai: 18-20°N, 72-74°E

JSON only:"""
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from LLM response"""
        text = text.strip()
        
        # Find JSON block
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx + 1]
        
        return None
    
    def _validate_and_normalize(self, extracted: Dict, user_query: str) -> Dict[str, Any]:
        """Validate and normalize extracted parameters"""
        
        # Ensure required fields exist
        normalized = {
            "location_name": extracted.get("location_name"),
            "location_bounds": extracted.get("location_bounds"),
            "date_range": extracted.get("date_range"),
            "date_years": extracted.get("date_years"),
            "depth_range": extracted.get("depth_range"),
            "depth_type": extracted.get("depth_type"),
            "parameters": extracted.get("parameters", []),
            "float_ids": extracted.get("float_ids"),
            "is_analytical": bool(extracted.get("is_analytical", False)),
            "is_comparative": bool(extracted.get("is_comparative", False)),
            "is_chart_request": bool(extracted.get("is_chart_request", False)),
            "complexity_level": extracted.get("complexity_level", "simple"),
            "extraction_method": "llm_structured",
            "confidence_score": 0.9,  # High confidence for structured extraction
            "original_query": user_query
        }
        
        # Validate depth_range format
        if normalized["depth_range"]:
            if isinstance(normalized["depth_range"], list) and len(normalized["depth_range"]) == 2:
                if isinstance(normalized["depth_range"][0], str):  # Operator format
                    normalized["depth_type"] = "operator"
                else:  # Range format
                    normalized["depth_type"] = "range"
        
        # Validate parameters
        valid_params = ["temperature", "salinity", "pressure"]
        if normalized["parameters"]:
            normalized["parameters"] = [p for p in normalized["parameters"] if p in valid_params]
        
        return normalized
