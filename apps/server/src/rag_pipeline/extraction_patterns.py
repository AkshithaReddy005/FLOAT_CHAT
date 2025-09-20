
"""
Unified Pattern Configuration
Single source of truth for parameter extraction patterns.
"""

# Temperature threshold patterns - ordered from most specific to least specific
TEMPERATURE_PATTERNS = [
    # Exact phrase patterns (highest priority)
    r"\btemperature\s+more\s+than\s+(\d+(?:\.\d+)?)\b",
    r"\btemperatures?\s+(?:more\s+than|higher\s+than|above|over|greater\s+than)\s+(\d+(?:\.\d+)?)\b",
    r"\btemperatures?\s+(?:lower\s+than|below|under|less\s+than)\s+(\d+(?:\.\d+)?)\b",

    # Standard comparison patterns
    r"temperature\s*(?:is\s*)?(?:greater\s+than|above|over|more\s+than)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?",
    r"temperature\s*(?:is\s*)?(?:less\s+than|below|under)\s*(\d+(?:\.\d+)?)\s*(?:degrees?|°)?c?",

    # Mathematical operator patterns
    r"temperature\s*[>]\s*(\d+(?:\.\d+)?)",
    r"temperature\s*[<]\s*(\d+(?:\.\d+)?)",

    # Context-based patterns
    r"(?:locations|places|areas|data).*?temperatures?\s+(?:higher\s+than|above|over|greater\s+than|more\s+than)\s+(\d+(?:\.\d+)?)",
    r"(?:locations|places|areas|data).*?temperatures?\s+(?:lower\s+than|below|under|less\s+than)\s+(\d+(?:\.\d+)?)",

    # Where clause patterns
    r"where\s+temperatures?\s+(?:are\s+)?(?:higher\s+than|above|over|greater\s+than|more\s+than)\s+(\d+(?:\.\d+)?)",
    r"where\s+temperatures?\s+(?:are\s+)?(?:lower\s+than|below|under|less\s+than)\s+(\d+(?:\.\d+)?)"
]

# Pattern classification - which patterns indicate "greater than" vs "less than"
TEMPERATURE_GREATER_THAN_PATTERNS = [0, 1, 3, 5, 7, 9]  # Indices of "greater than" patterns
TEMPERATURE_LESS_THAN_PATTERNS = [2, 4, 6, 8, 10]       # Indices of "less than" patterns

# Salinity threshold patterns
SALINITY_PATTERNS = [
    r"salinity\s*(?:is\s*)?(?:greater\s+than|above|over|more\s+than)\s*(\d+(?:\.\d+)?)",
    r"salinity\s*(?:is\s*)?(?:less\s+than|below|under)\s*(\d+(?:\.\d+)?)",
    r"salinity\s*[>]\s*(\d+(?:\.\d+)?)",
    r"salinity\s*[<]\s*(\d+(?:\.\d+)?)",
]

SALINITY_GREATER_THAN_PATTERNS = [0, 2]  # Indices of "greater than" patterns
SALINITY_LESS_THAN_PATTERNS = [1, 3]     # Indices of "less than" patterns

# Depth threshold patterns
DEPTH_PATTERNS = [
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

# Location patterns - ordered from most specific to least specific
LOCATION_PATTERNS = [
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

# Coordinate patterns
COORDINATE_PATTERNS = [
    r"between\s+(\d+)-(\d+)°?n\s+and\s+(\d+)-(\d+)°?e",
    r"(\d+)-(\d+)°?n.*?(\d+)-(\d+)°?e",
    r"(\d+\.?\d*)°?n[,\s]+(\d+\.?\d*)°?e",
]

def extract_temperature_threshold(query_lower: str):
    """Extract temperature threshold with proper operator classification"""
    for i, pattern in enumerate(TEMPERATURE_PATTERNS):
        import re
        match = re.search(pattern, query_lower)
        if match:
            temp_value = float(match.group(1))

            if i in TEMPERATURE_GREATER_THAN_PATTERNS:
                return (">", temp_value)
            elif i in TEMPERATURE_LESS_THAN_PATTERNS:
                return ("<", temp_value)
            else:
                # Default fallback - analyze pattern content
                if any(op in pattern for op in ["less", "below", "under", "lower", "[<]"]):
                    return ("<", temp_value)
                else:
                    return (">", temp_value)
    return None

def extract_salinity_threshold(query_lower: str):
    """Extract salinity threshold with proper operator classification"""
    for i, pattern in enumerate(SALINITY_PATTERNS):
        import re
        match = re.search(pattern, query_lower)
        if match:
            sal_value = float(match.group(1))

            if i in SALINITY_GREATER_THAN_PATTERNS:
                return (">", sal_value)
            elif i in SALINITY_LESS_THAN_PATTERNS:
                return ("<", sal_value)
    return None

def extract_depth_threshold(query_lower: str):
    """Extract depth threshold with operator and type"""
    for pattern, operator, depth_type in DEPTH_PATTERNS:
        import re
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