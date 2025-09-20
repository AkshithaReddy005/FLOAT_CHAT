"""
Unified Query Parser Module
Centralized parameter extraction that serves as single source of truth for all query parameters.
"""

import re
import uuid
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import calendar
import difflib
from .parameter_context import ParameterContext
from .param_extractors.llm_extractor import LLMParameterExtractor
from .param_extractors.region_resolver import RegionResolver

# Location intelligence integration
try:
    from ..analysis.location_intelligence import LocationIntelligence
    LOCATION_INTELLIGENCE_AVAILABLE = True
except ImportError:
    LOCATION_INTELLIGENCE_AVAILABLE = False


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

        # Initialize location intelligence
        self.location_intel = LocationIntelligence() if LOCATION_INTELLIGENCE_AVAILABLE else None

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
            "western indian ocean": {"lat_min": -30, "lat_max": 30, "lon_min": 20, "lon_max": 70},  # Added western Indian Ocean
            "eastern indian ocean": {"lat_min": -30, "lat_max": 30, "lon_min": 70, "lon_max": 120},  # Added eastern Indian Ocean
            "northern indian ocean": {"lat_min": 0, "lat_max": 30, "lon_min": 40, "lon_max": 100},   # Added northern Indian Ocean
            "southern indian ocean": {"lat_min": -40, "lat_max": 0, "lon_min": 20, "lon_max": 120},  # Added southern Indian Ocean
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

        # Force heuristic extraction for queries with clear threshold keywords
        # to bypass potential LLM failures on these specific patterns.
        query_lower = user_query.lower()
        threshold_keywords = ["above", "below", "greater", "less", ">", "<", ">=", "<=", "under", "over"]
        strategy = self.extraction_strategy

        # Use typo-tolerant detection for threshold keywords
        if strategy == "llm_first" and self._contains_threshold_keyword(query_lower, threshold_keywords):
            print(f"DEBUG: Threshold keyword (typo-tolerant) detected. Forcing heuristic extraction for query: '{user_query}'")
            strategy = "heuristic_only"
        
        # Strategy-based extraction
        if strategy == "llm_first" and self.llm_extractor:
            extracted = self._extract_with_llm_first(user_query, session_context)
        elif strategy == "llm_only" and self.llm_extractor:
            extracted = self._extract_with_llm_only(user_query, session_context)
        else:
            extracted = self._extract_with_heuristics(user_query, session_context)
        
        # Normalize date_range to datetime objects if LLM returned strings
        def _to_datetime(val):
            from datetime import datetime
            if isinstance(val, datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace('Z', '+00:00'))
                except Exception:
                    # Try plain date without timezone
                    try:
                        return datetime.fromisoformat(val)
                    except Exception:
                        return None
            return None
        dr = extracted.get("date_range")
        if dr and isinstance(dr, (list, tuple)):
            d0 = _to_datetime(dr[0])
            d1 = _to_datetime(dr[1])
            if d0 and d1:
                extracted["date_range"] = (d0, d1)
                # If we have a concrete range (e.g., a month), drop date_years to avoid conflicts
                if extracted.get("date_years"):
                    try:
                        if (d1 - d0).days < 370:  # treat as specific period, not whole year(s)
                            extracted["date_years"] = None
                    except Exception:
                        extracted["date_years"] = None
        
        # Create ParameterContext from extracted data
        # Create temporary context for location enhancement
        temp_context = ParameterContext(
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
            temperature_range=extracted.get("temperature_range"),  # FIXED: Add temperature threshold
            salinity_range=extracted.get("salinity_range"),        # FIXED: Add salinity threshold
            is_analytical=extracted.get("is_analytical", False),
            is_comparative=extracted.get("is_comparative", False),
            is_chart_request=extracted.get("is_chart_request", False),
            complexity_level=extracted.get("complexity_level", "simple"),
            session_context=session_context,
            extraction_method=extracted.get("extraction_method", "unknown"),
            confidence_score=extracted.get("confidence_score", 0.5)
        )

        # Get enhanced location context before final creation
        enhanced_location_context = self._get_enhanced_location_context(temp_context)

        # Create final ParameterContext with enhanced location intelligence
        param_context = ParameterContext(
            original_query=user_query,
            query_id=query_id,
            session_id=session_id,
            location_name=extracted.get("location_name"),
            location_bounds=extracted.get("location_bounds"),
            coordinate_precision=extracted.get("coordinate_precision", "approximate"),
            location_context=enhanced_location_context,
            date_range=extracted.get("date_range"),
            date_years=extracted.get("date_years"),
            temporal_type=extracted.get("temporal_type"),
            depth_range=extracted.get("depth_range"),
            depth_type=extracted.get("depth_type"),
            float_ids=extracted.get("float_ids"),
            parameters=extracted.get("parameters"),
            temperature_range=extracted.get("temperature_range"),  # FIXED: Add temperature threshold
            salinity_range=extracted.get("salinity_range"),        # FIXED: Add salinity threshold
            is_analytical=extracted.get("is_analytical", False),
            is_comparative=extracted.get("is_comparative", False),
            is_chart_request=extracted.get("is_chart_request", False),
            complexity_level=extracted.get("complexity_level", "simple"),
            session_context=session_context,
            extraction_method=extracted.get("extraction_method", "unknown"),
            confidence_score=extracted.get("confidence_score", 0.5)
        )

        return param_context

    def _contains_threshold_keyword(self, query_lower: str, keywords: List[str]) -> bool:
        """Detect threshold keywords with tolerance to common typos.
        - Directly checks for symbol operators like >, <, >=, <=
        - For word keywords, uses difflib to allow minor misspellings
        """
        # Direct symbol check first
        if any(sym in query_lower for sym in [">=", "<=", ">", "<"]):
            return True

        # Tokenize on non-letters to compare words
        tokens = re.split(r"[^a-zA-Z]+", query_lower)
        word_keywords = [k for k in keywords if k.isalpha()]

        # Quick exact match
        if any(tok in word_keywords for tok in tokens if tok):
            return True

        # Fuzzy match: allow close matches (similarity >= 0.8)
        for tok in tokens:
            if not tok:
                continue
            matches = difflib.get_close_matches(tok, word_keywords, n=1, cutoff=0.8)
            if matches:
                return True
        return False
    
    def _extract_with_llm_first(self, user_query: str, session_context: Optional[Dict]) -> Dict:
        """Extract using LLM first, fallback to heuristics"""
        llm_result = self.llm_extractor.extract(user_query, session_context)
        
        if llm_result.get("extraction_method") in ["llm_structured"]:
            # LLM succeeded — but ensure month specificity isn't lost
            query_lower = user_query.lower()
            # If query has a Month Year but llm_result lacks a date_range, supplement heuristically
            if (re.search(r"\b([a-zA-Z]{3,9})\s+([12][09][0-9]{2})\b", query_lower)
                and not llm_result.get("date_range")):
                try:
                    date_range, date_years, temporal_type = self._extract_temporal(query_lower)
                    if date_range:
                        llm_result["date_range"] = date_range
                        llm_result["temporal_type"] = temporal_type or llm_result.get("temporal_type")
                except Exception as e:
                    print(f"LLM-first month supplement failed, proceeding without: {e}")
            # Enhance with region resolver as usual
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

        # Extract parameter thresholds - FIXED: Add temperature/salinity threshold extraction
        temperature_range, salinity_range = self._extract_parameter_thresholds(query_lower)

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
            "temperature_range": temperature_range,  
            "salinity_range": salinity_range,        
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

        # CRITICAL FIX: Only check for comparative queries if there are actual comparison keywords
        # Don't treat "locations with temperatures higher than X" as comparative
        has_comparison_keywords = any(word in query_lower for word in ['vs', 'versus', 'compare', 'comparison', 'difference between'])

        if has_comparison_keywords:
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
        
        # Named location patterns - ordered from most specific to least specific
        location_patterns = [
            r"mumbai", r"bombay",
            r"western\s+indian\s+ocean", r"eastern\s+indian\s+ocean",
            r"northern\s+indian\s+ocean", r"southern\s+indian\s+ocean",
            r"northern\s+arabian\s+sea", r"southern\s+arabian\s+sea",
            r"arabian\s+sea", r"indian\s+ocean",
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
                elif pattern == r"western\s+indian\s+ocean":
                    location_name = "western indian ocean"
                elif pattern == r"eastern\s+indian\s+ocean":
                    location_name = "eastern indian ocean"
                elif pattern == r"northern\s+indian\s+ocean":
                    location_name = "northern indian ocean"
                elif pattern == r"southern\s+indian\s+ocean":
                    location_name = "southern indian ocean"
                elif pattern == r"northern\s+arabian\s+sea":
                    location_name = "northern arabian sea"
                elif pattern == r"southern\s+arabian\s+sea":
                    location_name = "southern arabian sea"
                elif pattern == r"arabian\s+sea":
                    location_name = "arabian sea"
                elif pattern == r"indian\s+ocean":
                    location_name = "indian ocean"
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
        now = datetime.now()

        # Helper: month name mapping
        month_map = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
        month_map.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})

        def month_num(s: str) -> Optional[int]:
            return month_map.get(s[:3].lower()) if s else None

        def start_of_month(year: int, month: int) -> datetime:
            return datetime(year, month, 1)

        def end_of_month_exclusive(year: int, month: int) -> datetime:
            # Return first day of next month (exclusive bound)
            if month == 12:
                return datetime(year + 1, 1, 1)
            return datetime(year, month + 1, 1)

        def add_months(dt: datetime, months: int) -> datetime:
            y = dt.year + (dt.month - 1 + months) // 12
            m = (dt.month - 1 + months) % 12 + 1
            d = min(dt.day, calendar.monthrange(y, m)[1])
            return datetime(y, m, d)

        # 1) Year comparisons (highest priority)
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

        # 2) Absolute year ranges
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
                return (datetime(start_year, 1, 1), datetime(end_year, 12, 31)), None, "range"

        # 3) Month with year: "March 2023", "Mar 2023" (must come BEFORE single year)
        m = re.search(r"\b([a-zA-Z]{3,9})\s+([12][09][0-9]{2})\b", query_lower)
        if m:
            mon, yr = m.group(1), int(m.group(2))
            mn = month_num(mon)
            if mn:
                # Use inclusive end-of-month for consistency with SQL generator (which adds +1 day)
                end_inclusive = end_of_month_exclusive(yr, mn) - timedelta(days=1)
                return (start_of_month(yr, mn), end_inclusive), None, "month"

        # 4) Month range possibly across years: "Jan 2022 to Mar 2023"
        m2 = re.search(r"\b([a-zA-Z]{3,9})\s+([12][09][0-9]{2})\s*(?:to|-)\s*([a-zA-Z]{3,9})\s+([12][09][0-9]{2})\b", query_lower)
        if m2:
            m1s, y1s, m2s, y2s = m2.groups()
            y1, y2 = int(y1s), int(y2s)
            mn1, mn2 = month_num(m1s), month_num(m2s)
            if mn1 and mn2:
                start = start_of_month(y1, mn1)
                end_inclusive = end_of_month_exclusive(y2, mn2) - timedelta(days=1)
                return (start, end_inclusive), None, "month_range"

        # 5) Single year (after month patterns to avoid swallowing month-specific queries)
        single_year_patterns = [
            r"(?:in|for|during)\s+([12][09][0-9]{2})",
            r"year\s+([12][09][0-9]{2})",
            r"\b([12][09][0-9]{2})\b",
        ]
        for pattern in single_year_patterns:
            match = re.search(pattern, query_lower)
            if match:
                year = int(match.group(1))
                return (datetime(year, 1, 1), datetime(year, 12, 31)), None, "single_year"

        # 6) Quarter handling: Q1 2023, first quarter 2023
        q = re.search(r"\bq([1-4])\s+([12][09][0-9]{2})\b", query_lower)
        if q:
            qn, yr = int(q.group(1)), int(q.group(2))
            start_month = (qn - 1) * 3 + 1
            start = start_of_month(yr, start_month)
            end_excl = end_of_month_exclusive(yr, start_month + 2)
            return (start, end_excl - timedelta(days=1)), None, "quarter"
        q2 = re.search(r"\b(first|second|third|fourth)\s+quarter\s+([12][09][0-9]{2})\b", query_lower)
        if q2:
            qname, yr = q2.group(1), int(q2.group(2))
            qmap = {"first": 1, "second": 2, "third": 3, "fourth": 4}
            qn = qmap.get(qname)
            if qn:
                start_month = (qn - 1) * 3 + 1
                start = start_of_month(yr, start_month)
                end_excl = end_of_month_exclusive(yr, start_month + 2)
                return (start, end_excl - timedelta(days=1)), None, "quarter"

        # 7) Relative ranges
        # this year / last year
        if re.search(r"\bthis\s+year\b", query_lower):
            start = datetime(now.year, 1, 1)
            end = datetime(now.year, 12, 31)
            return (start, end), None, "relative"
        if re.search(r"\blast\s+year\b", query_lower):
            start = datetime(now.year - 1, 1, 1)
            end = datetime(now.year - 1, 12, 31)
            return (start, end), None, "relative"

        # this month / last month
        if re.search(r"\bthis\s+month\b", query_lower):
            start = start_of_month(now.year, now.month)
            end_excl = end_of_month_exclusive(now.year, now.month)
            return (start, end_excl - timedelta(days=1)), None, "relative"
        if re.search(r"\blast\s+month\b", query_lower):
            last_m = add_months(now, -1)
            start = start_of_month(last_m.year, last_m.month)
            end_excl = end_of_month_exclusive(last_m.year, last_m.month)
            return (start, end_excl - timedelta(days=1)), None, "relative"

        # last N months / past N months
        m_rel = re.search(r"\b(last|past)\s+(\d+)\s+months?\b", query_lower)
        if m_rel:
            n = int(m_rel.group(2))
            start = add_months(now.replace(day=1), -n)
            end = now
            return (start, end), None, "relative"

        # last N days
        d_rel = re.search(r"\b(last|past)\s+(\d+)\s+days?\b", query_lower)
        if d_rel:
            n = int(d_rel.group(2))
            start = now - timedelta(days=n)
            end = now
            return (start, end), None, "relative"

        # since/until/before/after year
        since_y = re.search(r"\bsince\s+([12][09][0-9]{2})\b", query_lower)
        if since_y:
            y = int(since_y.group(1))
            return (datetime(y, 1, 1), now), None, "relative"

        after_y = re.search(r"\bafter\s+([12][09][0-9]{2})\b", query_lower)
        if after_y:
            y = int(after_y.group(1))
            return (datetime(y + 1, 1, 1), now), None, "relative"

        before_y = re.search(r"\b(before|until)\s+([12][09][0-9]{2})\b", query_lower)
        if before_y:
            y = int(before_y.group(2))
            # up to start of that year
            return (datetime(1900, 1, 1), datetime(y, 1, 1)), None, "relative"

        # Specific existing special case retained as fallback example
        if "march" in query_lower and "2023" in query_lower:
            date_range = (datetime(2023, 3, 1), datetime(2023, 4, 1))
            return date_range, None, "specific_month"

        return None, None, None
    
    def _extract_depth(self, query_lower: str, session_context: Optional[Dict] = None) -> Tuple[Optional[Tuple[Any, Any]], Optional[str]]:
        """Extract depth parameters with operator and range support using unified patterns"""
        from .extraction_patterns import extract_depth_threshold

        return extract_depth_threshold(query_lower)
    
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

    def _extract_parameter_thresholds(self, query_lower: str) -> Tuple[Optional[Tuple], Optional[Tuple]]:
        """Extract temperature and salinity threshold filters using unified patterns"""
        # Import the unified extraction functions
        from .extraction_patterns import extract_temperature_threshold, extract_salinity_threshold

        temperature_range = extract_temperature_threshold(query_lower)
        salinity_range = extract_salinity_threshold(query_lower)

        if temperature_range:
            print(f"DEBUG: Temperature threshold extracted: {temperature_range}")
        if salinity_range:
            print(f"DEBUG: Salinity threshold extracted: {salinity_range}")

        return temperature_range, salinity_range

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

    def _get_enhanced_location_context(self, param_context: 'ParameterContext') -> Optional[Dict[str, Any]]:
        """Get enhanced location context for RAG system"""
        if not param_context.location_bounds:
            return None

        # Get center coordinates of the location bounds
        bounds = param_context.location_bounds
        center_lat = (bounds['lat_min'] + bounds['lat_max']) / 2
        center_lon = (bounds['lon_min'] + bounds['lon_max']) / 2

        # Get depth context if available
        depth = None
        if param_context.depth_range:
            if isinstance(param_context.depth_range, tuple) and len(param_context.depth_range) == 2:
                if isinstance(param_context.depth_range[0], (int, float)):
                    depth = (param_context.depth_range[0] + param_context.depth_range[1]) / 2
                elif param_context.depth_range[0] in ['>', '>=']:
                    depth = param_context.depth_range[1] + 100  # Assume some depth below threshold
                elif param_context.depth_range[0] in ['<', '<=']:
                    depth = max(0, param_context.depth_range[1] - 50)  # Assume some depth above threshold

        # Use location intelligence if available
        if self.location_intel:
            return self.location_intel.get_location_based_context(center_lat, center_lon, depth)
        else:
            # Fallback to basic context
            return {
                'coordinates': f"{center_lat:.2f}°, {center_lon:.2f}°",
                'ocean_basin': self._basic_ocean_classification(center_lat, center_lon),
                'oceanographic_region': self._basic_oceanographic_region(center_lat),
                'depth_context': self._basic_depth_context(depth) if depth else None
            }

    def _basic_ocean_classification(self, lat: float, lon: float) -> str:
        """Basic ocean classification fallback"""
        if 0 <= lat <= 30 and 50 <= lon <= 80:
            return "Arabian Sea"
        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            return "Bay of Bengal"
        elif lat < 0:
            return "Southern Indian Ocean"
        else:
            return "Northern Indian Ocean"

    def _basic_oceanographic_region(self, lat: float) -> str:
        """Basic oceanographic region classification"""
        if -5 <= lat <= 5:
            return "Equatorial"
        elif abs(lat) <= 23.5:
            return "Tropical"
        elif abs(lat) <= 35:
            return "Subtropical"
        else:
            return "Temperate"

    def _basic_depth_context(self, depth: float) -> str:
        """Basic depth context"""
        if depth < 100:
            return "surface mixed layer"
        elif depth < 500:
            return "intermediate waters"
        elif depth < 1000:
            return "deep waters"
        else:
            return "abyssal depths"
