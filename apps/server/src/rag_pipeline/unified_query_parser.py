"""
Unified Query Parser Module
Centralized parameter extraction that serves as single source of truth for all query parameters.
"""

import re
import uuid
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from .parameter_context import ParameterContext
from .param_extractors.llm_extractor import LLMParameterExtractor
from .param_extractors.region_resolver import RegionResolver


class UnifiedQueryParser:
    """
    Centralized query parser that extracts all parameters from user queries.
    This is the ONLY place where parameter extraction should happen.
    """
    
    def __init__(self, gemini_api_key: str = None, extraction_strategy: str = "llm_first"):
        """
        Initialize parser with configurable extraction strategy
        
        Args:
            gemini_api_key: API key for LLM extraction
            extraction_strategy: "llm_first", "heuristic_only", or "llm_only"
        """
        self.extraction_strategy = extraction_strategy
        self.region_resolver = RegionResolver()
        
        # Initialize LLM extractor if API key provided
        self.llm_extractor = None
        if gemini_api_key and extraction_strategy in ["llm_first", "llm_only"]:
            try:
                self.llm_extractor = LLMParameterExtractor(gemini_api_key)
            except Exception as e:
                print(f"Warning: Could not initialize LLM extractor: {e}")
                self.extraction_strategy = "heuristic_only"
        
        # Fallback location definitions (kept for heuristic mode)
        self.location_bounds = {
            "mumbai": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "bombay": {"lat_min": 18, "lat_max": 20, "lon_min": 72, "lon_max": 74},
            "arabian sea": {"lat_min": 10, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "indian ocean": {"lat_min": -40, "lat_max": 30, "lon_min": 20, "lon_max": 120},
            "northern arabian sea": {"lat_min": 20, "lat_max": 25, "lon_min": 65, "lon_max": 75},
            "southern arabian sea": {"lat_min": 10, "lat_max": 20, "lon_min": 65, "lon_max": 75},
            "coastal": {"lat_min": 18, "lat_max": 22, "lon_min": 70, "lon_max": 74},
            "offshore": {"lat_min": 15, "lat_max": 25, "lon_min": 65, "lon_max": 72}
        }
    
    def parse_query(self, user_query: str, session_context: Optional[Dict] = None, 
                   query_classification: Optional[Dict] = None) -> ParameterContext:
        """
        Parse user query and extract all parameters into a unified context.
        This is the ONLY method that should extract parameters from queries.
        """
        
        query_id = str(uuid.uuid4())[:8]
        session_id = session_context.get('session_id') if session_context else None
        
        # Strategy-based extraction
        if self.extraction_strategy == "llm_first" and self.llm_extractor:
            extracted = self._extract_with_llm_first(user_query, session_context)
        elif self.extraction_strategy == "llm_only" and self.llm_extractor:
            extracted = self._extract_with_llm_only(user_query, session_context)
        else:
            extracted = self._extract_with_heuristics(user_query, session_context)
        
        # Create ParameterContext from extracted data
        return ParameterContext(
            original_query=user_query,
            query_id=query_id,
            session_id=session_id,
            location_name=extracted.get("location_name"),
            location_bounds=extracted.get("location_bounds"),
            coordinate_precision=extracted.get("coordinate_precision", "approximate"),
            date_range=extracted.get("date_range"),
            date_years=extracted.get("date_years"),
            temporal_type=extracted.get("temporal_type"),
            depth_range=extracted.get("depth_range"),
            depth_type=extracted.get("depth_type"),
            float_ids=extracted.get("float_ids"),
            parameters=extracted.get("parameters"),
            is_analytical=extracted.get("is_analytical", False),
            is_comparative=extracted.get("is_comparative", False),
            is_chart_request=extracted.get("is_chart_request", False),
            complexity_level=extracted.get("complexity_level", "simple"),
            session_context=session_context,
            extraction_method=extracted.get("extraction_method", "unknown"),
            confidence_score=extracted.get("confidence_score", 0.5)
        )
    
    def _extract_with_llm_first(self, user_query: str, session_context: Optional[Dict]) -> Dict:
        """Extract using LLM first, fallback to heuristics"""
        llm_result = self.llm_extractor.extract(user_query, session_context)
        
        if llm_result.get("extraction_method") in ["llm_structured"]:
            # LLM succeeded, enhance with fuzzy region resolution
            return self._enhance_with_region_resolver(llm_result, user_query)
        else:
            # LLM failed, use heuristics
            print(f"LLM extraction failed, falling back to heuristics for: {user_query}")
            return self._extract_with_heuristics(user_query, session_context)
    
    def _extract_with_llm_only(self, user_query: str, session_context: Optional[Dict]) -> Dict:
        """Extract using LLM only"""
        llm_result = self.llm_extractor.extract(user_query, session_context)
        return self._enhance_with_region_resolver(llm_result, user_query)
    
    def _extract_with_heuristics(self, user_query: str, session_context: Optional[Dict]) -> Dict:
        """Extract using original heuristic methods"""
        query_lower = user_query.lower()
        
        # Extract location parameters
        location_name, location_bounds, coordinate_precision = self._extract_location(query_lower, session_context)
        
        # Extract temporal parameters
        date_range, date_years, temporal_type = self._extract_temporal(query_lower)
        
        # Extract depth parameters
        depth_range, depth_type = self._extract_depth(query_lower, session_context)
        
        # Extract data parameters
        float_ids = self._extract_float_ids(query_lower)
        parameters = self._extract_parameters(query_lower)
        
        # Extract query characteristics
        is_analytical = self._is_analytical_query(query_lower)
        is_comparative = self._is_comparative_query(query_lower)
        is_chart_request = False  # Simple heuristic detection
        complexity_level = self._determine_complexity(query_lower, is_analytical, is_comparative)
        
        return {
            "location_name": location_name,
            "location_bounds": location_bounds,
            "coordinate_precision": coordinate_precision,
            "date_range": date_range,
            "date_years": date_years,
            "temporal_type": temporal_type,
            "depth_range": depth_range,
            "depth_type": depth_type,
            "float_ids": float_ids,
            "parameters": parameters,
            "is_analytical": is_analytical,
            "is_comparative": is_comparative,
            "is_chart_request": is_chart_request,
            "complexity_level": complexity_level,
            "extraction_method": "heuristic",
            "confidence_score": self._calculate_confidence_score(query_lower, location_name, date_range, depth_range)
        }
    
    def _enhance_with_region_resolver(self, extracted: Dict, user_query: str) -> Dict:
        """Enhance extracted data with fuzzy region resolution"""
        if extracted.get("location_name") and not extracted.get("location_bounds"):
            # Try to resolve region using fuzzy matching
            result = self.region_resolver.resolve_region(extracted["location_name"])
            if result:
                canonical_name, bounds, confidence = result
                extracted["location_name"] = canonical_name
                extracted["location_bounds"] = bounds
                extracted["coordinate_precision"] = "fuzzy_resolved"
                # Adjust confidence based on region resolution
                extracted["confidence_score"] = min(extracted.get("confidence_score", 0.5) * confidence, 1.0)
        
        return extracted
    
    def _extract_location(self, query_lower: str, session_context: Optional[Dict] = None) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """Extract location parameters with session context support"""
        
        # Check for comparative location queries first
        comparative_locations = self._extract_comparative_locations(query_lower)
        if comparative_locations:
            return comparative_locations
        
        # Direct coordinate patterns (highest precision)
        coordinate_patterns = [
            r"between\s+(\d+)-(\d+)°?n\s+and\s+(\d+)-(\d+)°?e",  # "between 15-25°N and 65-75°E"
            r"(\d+)-(\d+)°?n.*?(\d+)-(\d+)°?e",  # "15-25°N and 65-75°E"
            r"(\d+\.?\d*)°?n[,\s]+(\d+\.?\d*)°?e",  # "19.5°N, 73.2°E"
        ]
        
        for i, pattern in enumerate(coordinate_patterns):
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) == 4:  # Range coordinates
                    lat_min, lat_max, lon_min, lon_max = map(float, match.groups())
                    bounds = {
                        "lat_min": lat_min, "lat_max": lat_max,
                        "lon_min": lon_min, "lon_max": lon_max
                    }
                    location_name = f"coordinates_{lat_min}-{lat_max}N_{lon_min}-{lon_max}E"
                    return location_name, bounds, "exact"
                elif len(match.groups()) == 2:  # Point coordinates
                    lat, lon = map(float, match.groups())
                    bounds = {
                        "lat_min": lat - 0.5, "lat_max": lat + 0.5,
                        "lon_min": lon - 0.5, "lon_max": lon + 0.5
                    }
                    location_name = f"point_{lat}N_{lon}E"
                    return location_name, bounds, "exact"
        
        # Named location patterns
        location_patterns = [
            r"mumbai", r"bombay",
            r"arabian\s+sea", r"indian\s+ocean",
            r"northern\s+arabian\s+sea", r"southern\s+arabian\s+sea",
            r"coastal", r"offshore",
            r"near\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"in\s+([a-zA-Z\s]+?)(?:\s|$)",
            r"around\s+([a-zA-Z\s]+?)(?:\s|$)"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if pattern in [r"mumbai", r"bombay"]:
                    location_name = "mumbai"
                elif pattern == r"arabian\s+sea":
                    location_name = "arabian sea"
                elif pattern == r"indian\s+ocean":
                    location_name = "indian ocean"
                elif pattern == r"northern\s+arabian\s+sea":
                    location_name = "northern arabian sea"
                elif pattern == r"southern\s+arabian\s+sea":
                    location_name = "southern arabian sea"
                elif pattern in [r"coastal", r"offshore"]:
                    location_name = match.group(0)
                else:
                    location_name = match.group(1).strip()
                
                bounds = self.location_bounds.get(location_name)
                precision = "approximate" if bounds else None
                return location_name, bounds, precision
        
        # Session context fallback for relative queries
        if session_context:
            relative_indicators = ["below", "above", "deeper", "shallower", "there", "that area", "same area"]
            if any(indicator in query_lower for indicator in relative_indicators):
                recent_locations = session_context.get('key_context', {}).get('locations', [])
                if recent_locations:
                    # Use the most recent location from session
                    for location in reversed(recent_locations):
                        if location.lower() in self.location_bounds:
                            bounds = self.location_bounds[location.lower()]
                            return location.lower(), bounds, "session_context"
        
        return None, None, None
    
    def _extract_temporal(self, query_lower: str) -> Tuple[Optional[Tuple[datetime, datetime]], Optional[List[int]], Optional[str]]:
        """Extract temporal parameters with comprehensive pattern matching"""
        
        # Year comparison patterns (highest priority)
        comparison_patterns = [
            r"(?:comparison|compare|comparing)?\s*([12][09][0-9]{2})\s*(?:and|vs|versus)\s*([12][09][0-9]{2})",
            r"between\s+([12][09][0-9]{2})\s+and\s+([12][09][0-9]{2})",
            r"compare.*?([12][09][0-9]{2}).*?([12][09][0-9]{2})",
        ]
        
        for pattern in comparison_patterns:
            match = re.search(pattern, query_lower)
            if match:
                year1, year2 = map(int, match.groups())
                return None, [year1, year2], "comparison"
        
        # Date range patterns
        range_patterns = [
            r"from\s+([12][09][0-9]{2})\s+to\s+([12][09][0-9]{2})",
            r"([12][09][0-9]{2})\s*-\s*([12][09][0-9]{2})",
        ]
        
        for pattern in range_patterns:
            match = re.search(pattern, query_lower)
            if match:
                year1, year2 = map(int, match.groups())
                start_year = min(year1, year2)
                end_year = max(year1, year2)
                date_range = (datetime(start_year, 1, 1), datetime(end_year, 12, 31))
                return date_range, None, "range"
        
        # Single year patterns
        single_year_patterns = [
            r"(?:in|for|during)\s+([12][09][0-9]{2})",
            r"year\s+([12][09][0-9]{2})",
        ]
        
        for pattern in single_year_patterns:
            match = re.search(pattern, query_lower)
            if match:
                year = int(match.group(1))
                date_range = (datetime(year, 1, 1), datetime(year, 12, 31))
                return date_range, None, "single_year"
        
        # Specific month patterns
        if "march" in query_lower and "2023" in query_lower:
            date_range = (datetime(2023, 3, 1), datetime(2023, 4, 1))
            return date_range, None, "specific_month"
        
        return None, None, None
    
    def _extract_depth(self, query_lower: str, session_context: Optional[Dict] = None) -> Tuple[Optional[Tuple[Any, Any]], Optional[str]]:
        """Extract depth parameters with operator and range support"""
        
        depth_patterns = [
            (r"below\s*(\d+)\s*m", ">=", "operator"),
            (r"above\s*(\d+)\s*m", "<=", "operator"),
            (r"deeper\s*than\s*(\d+)", ">=", "operator"),
            (r"shallower\s*than\s*(\d+)", "<=", "operator"),
            (r"greater\s*than\s*(\d+)\s*m", ">=", "operator"),
            (r"less\s*than\s*(\d+)\s*m", "<=", "operator"),
            (r"depths?\s+greater\s+than\s*(\d+)\s*m", ">=", "operator"),
            (r"depths?\s+less\s+than\s*(\d+)\s*m", "<=", "operator"),
            (r"at\s*(\d+)\s*m", None, "exact"),
            (r"depth\s*(\d+)", None, "range"),
            (r"(\d+)\s*m.*deep", None, "range"),
        ]
        
        for pattern, operator, depth_type in depth_patterns:
            match = re.search(pattern, query_lower)
            if match:
                depth = float(match.group(1))
                
                if depth_type == "operator":
                    return (operator, depth), "operator"
                elif depth_type == "exact":
                    return (depth - 1, depth + 1), "range"  # ±1m for exact depth
                else:  # range
                    return (depth - 50, depth + 50), "range"  # ±50m for general depth mentions
        
        return None, None
    
    def _extract_float_ids(self, query_lower: str) -> Optional[List[str]]:
        """Extract float IDs from query"""
        float_patterns = [
            r"float[_\s]*([a-zA-Z0-9_]+)",
            r"argo[_\s]*([a-zA-Z0-9_]+)",
        ]
        
        float_ids = []
        for pattern in float_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                float_id = match.upper()
                if not float_id.startswith('FLOAT_'):
                    float_id = f'FLOAT_{float_id}'
                float_ids.append(float_id)
        
        return float_ids if float_ids else None
    
    def _extract_parameters(self, query_lower: str) -> Optional[List[str]]:
        """Extract measurement parameters from query"""
        # Detect analytical queries (average, mean, etc.)
        is_analytical = any(word in query_lower for word in ['average', 'mean', 'avg', 'median', 'max', 'min', 'total', 'sum', 'count'])
        
        # Detect comparative queries
        is_comparative = any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference', 'between', 'higher', 'lower', 'warmer', 'colder'])
        
        parameters = []
        
        if any(word in query_lower for word in ['temperature', 'temp', 'thermal']):
            parameters.append('temperature')
        if any(word in query_lower for word in ['salinity', 'salt', 'saline']):
            parameters.append('salinity')
        if any(word in query_lower for word in ['pressure']):
            parameters.append('pressure')
        
        return parameters if parameters else None
    
    def _extract_comparative_locations(self, query_lower: str) -> Optional[Tuple[str, Dict, str]]:
        """Extract multiple locations for comparative queries"""
        # Check for comparative patterns
        comparative_patterns = [
            r"compare\s+(.+?)\s+and\s+(.+?)(?:\s+temperatures?)",
            r"compare\s+(.+?)\s+and\s+(.+?)$",
            r"(.+?)\s+vs\s+(.+?)(?:\s+temperatures?)",
            r"(.+?)\s+vs\s+(.+?)$",
            r"(.+?)\s+versus\s+(.+?)(?:\s+temperatures?)",
            r"(.+?)\s+versus\s+(.+?)$",
            r"difference\s+between\s+(.+?)\s+and\s+(.+?)(?:\s+temperatures?)",
            r"difference\s+between\s+(.+?)\s+and\s+(.+?)$"
        ]
        
        print(f"DEBUG: Checking comparative patterns for: {query_lower}")
        
        for pattern in comparative_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location1 = match.group(1).strip()
                location2 = match.group(2).strip()
                print(f"DEBUG: Found comparative match - Location1: '{location1}', Location2: '{location2}'")
                
                # Map to known locations
                loc1_bounds = self._get_location_bounds(location1)
                loc2_bounds = self._get_location_bounds(location2)
                print(f"DEBUG: Location bounds - Loc1: {loc1_bounds}, Loc2: {loc2_bounds}")
                
                if loc1_bounds and loc2_bounds:
                    # Create combined bounds for both locations
                    combined_bounds = {
                        "lat_min": min(loc1_bounds["lat_min"], loc2_bounds["lat_min"]),
                        "lat_max": max(loc1_bounds["lat_max"], loc2_bounds["lat_max"]),
                        "lon_min": min(loc1_bounds["lon_min"], loc2_bounds["lon_min"]),
                        "lon_max": max(loc1_bounds["lon_max"], loc2_bounds["lon_max"])
                    }
                    location_name = f"{location1}_vs_{location2}"
                    print(f"DEBUG: Returning comparative location: {location_name}")
                    return location_name, combined_bounds, "comparative"
        
        return None
    
    def _get_location_bounds(self, location_name: str) -> Optional[Dict]:
        """Get bounds for a specific location name"""
        location_clean = location_name.lower().strip()
        return self.location_bounds.get(location_clean)
    
    def _is_analytical_query(self, query_lower: str) -> bool:
        """Determine if query requires analytical processing"""
        analytical_indicators = [
            'average', 'mean', 'median', 'std', 'deviation', 'correlation',
            'trend', 'pattern', 'analysis', 'compare', 'difference',
            'maximum', 'minimum', 'percentile', 'distribution', 'standard'
        ]
        return any(indicator in query_lower for indicator in analytical_indicators)
    
    def _is_comparative_query(self, query_lower: str) -> bool:
        """Determine if query involves comparison between areas/conditions"""
        comparison_indicators = [
            'vs', 'versus', 'compared to', 'compare', 'difference between',
            'warmer than', 'cooler than', 'saltier than', 'difference in'
        ]
        return any(indicator in query_lower for indicator in comparison_indicators)
    
    def _determine_complexity(self, query_lower: str, is_analytical: bool, is_comparative: bool) -> str:
        """Determine query complexity level"""
        if is_comparative or 'correlation' in query_lower or 'percentile' in query_lower:
            return "complex"
        elif is_analytical or len(query_lower.split()) > 10:
            return "moderate"
        else:
            return "simple"
    
    def _calculate_confidence_score(self, query_lower: str, location_name: Optional[str], 
                                  date_range: Optional[Tuple], depth_range: Optional[Tuple]) -> float:
        """Calculate confidence score for parameter extraction"""
        score = 1.0
        
        # Reduce confidence for ambiguous queries
        if len(query_lower.split()) < 3:
            score -= 0.2
        
        # Increase confidence for specific parameters
        if location_name:
            score += 0.1
        if date_range:
            score += 0.1
        if depth_range:
            score += 0.1
        
        # Reduce confidence for very long queries (might be ambiguous)
        if len(query_lower.split()) > 15:
            score -= 0.1
        
        return max(0.1, min(1.0, score))
    
    def create_fallback_context(self, original_context: ParameterContext, 
                               fallback_reason: str) -> ParameterContext:
        """Create a fallback parameter context with relaxed constraints"""
        
        # Create new context with some parameters relaxed
        fallback_params = {
            'original_query': original_context.original_query,
            'query_id': original_context.query_id,
            'session_id': original_context.session_id,
            'fallback_applied': True,
            'fallback_reason': fallback_reason,
            'confidence_score': original_context.confidence_score * 0.7,  # Reduce confidence
        }
        
        # Keep most restrictive filters, relax others
        if original_context.location_bounds:
            fallback_params['location_name'] = original_context.location_name
            fallback_params['location_bounds'] = original_context.location_bounds
            fallback_params['coordinate_precision'] = "approximate"
        
        # For temporal: keep year comparisons, relax ranges
        if original_context.date_years:
            fallback_params['date_years'] = original_context.date_years
            fallback_params['temporal_type'] = original_context.temporal_type
        elif original_context.date_range and fallback_reason != "no_temporal_data":
            fallback_params['date_range'] = original_context.date_range
            fallback_params['temporal_type'] = original_context.temporal_type
        
        # For depth: relax ranges, keep operators
        if original_context.depth_range and original_context.depth_type == "operator":
            fallback_params['depth_range'] = original_context.depth_range
            fallback_params['depth_type'] = original_context.depth_type
        
        # Keep data parameters
        if original_context.parameters:
            fallback_params['parameters'] = original_context.parameters
        
        # Keep query characteristics
        fallback_params['is_analytical'] = original_context.is_analytical
        fallback_params['is_comparative'] = original_context.is_comparative
        fallback_params['is_chart_request'] = original_context.is_chart_request
        fallback_params['complexity_level'] = original_context.complexity_level
        
        return ParameterContext(**fallback_params)
