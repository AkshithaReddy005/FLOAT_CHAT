"""
SQL Validation Module
Validates that generated SQL queries actually match the extracted parameters.
"""

import re
from typing import Dict, List, Tuple, Optional
from .parameter_context import ParameterContext

class SQLValidator:
    """Validates SQL queries against parameter contexts to ensure consistency"""

    def validate_sql_against_context(self, sql: str, parameter_context: ParameterContext) -> Tuple[bool, List[str]]:
        """
        Validate that the generated SQL actually implements the extracted parameters.
        Returns (is_valid, list_of_violations)
        """
        violations = []

        if not sql:
            violations.append("No SQL query generated")
            return False, violations

        sql_lower = sql.lower().strip()

        # Check temperature threshold filters
        if parameter_context.temperature_range:
            operator, value = parameter_context.temperature_range
            expected_condition = f"temperature {operator} {value}"

            if expected_condition.lower() not in sql_lower:
                violations.append(f"Missing temperature filter: {expected_condition}")

            # Also check for NOT NULL condition
            if "temperature is not null" not in sql_lower:
                violations.append("Missing temperature IS NOT NULL condition")

        # Check salinity threshold filters
        if parameter_context.salinity_range:
            operator, value = parameter_context.salinity_range
            expected_condition = f"salinity {operator} {value}"

            if expected_condition.lower() not in sql_lower:
                violations.append(f"Missing salinity filter: {expected_condition}")

            # Also check for NOT NULL condition
            if "salinity is not null" not in sql_lower:
                violations.append("Missing salinity IS NOT NULL condition")

        # Check location bounds (if present)
        if parameter_context.location_bounds:
            bounds = parameter_context.location_bounds

            # Check for latitude bounds
            lat_between = f"latitude between {bounds['lat_min']} and {bounds['lat_max']}"
            if lat_between.lower() not in sql_lower:
                violations.append(f"Missing latitude bounds: {lat_between}")

            # Check for longitude bounds
            lon_between = f"longitude between {bounds['lon_min']} and {bounds['lon_max']}"
            if lon_between.lower() not in sql_lower:
                violations.append(f"Missing longitude bounds: {lon_between}")

        # Check depth filters
        if parameter_context.depth_range and parameter_context.depth_type == "operator":
            operator, value = parameter_context.depth_range
            expected_condition = f"depth {operator} {value}"

            if expected_condition.lower() not in sql_lower:
                violations.append(f"Missing depth filter: {expected_condition}")

        # Check for parameter NOT NULL conditions (if parameters are specified)
        if parameter_context.parameters:
            for param in parameter_context.parameters:
                null_check = f"{param} is not null"
                if null_check.lower() not in sql_lower:
                    violations.append(f"Missing {param} IS NOT NULL condition")

        # Check that SQL has proper FROM clause
        if "from argo_measurements" not in sql_lower:
            violations.append("Missing FROM argo_measurements clause")

        # Check that SQL has proper SELECT clause
        if not sql_lower.strip().startswith("select") and not sql_lower.strip().startswith("with"):
            violations.append("SQL must start with SELECT or WITH")

        # Check for LIMIT clause (unless it's an aggregation query)
        if "limit" not in sql_lower:
            # Allow aggregation queries without LIMIT
            has_aggregation = any(agg in sql_lower for agg in ["avg(", "count(", "sum(", "max(", "min(", "corr("])
            if not has_aggregation:
                violations.append("Missing LIMIT clause for non-aggregation query")

        return len(violations) == 0, violations

    def validate_sql_syntax(self, sql: str) -> Tuple[bool, List[str]]:
        """
        Basic SQL syntax validation to catch obvious errors.
        Returns (is_valid, list_of_violations)
        """
        violations = []

        if not sql:
            violations.append("Empty SQL query")
            return False, violations

        sql_clean = sql.strip().lower()

        # Check basic structure
        if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
            violations.append("SQL must start with SELECT or WITH")

        # Check for balanced parentheses
        open_parens = sql_clean.count("(")
        close_parens = sql_clean.count(")")
        if open_parens != close_parens:
            violations.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")

        # Check for required FROM clause
        if "from" not in sql_clean:
            violations.append("Missing FROM clause")

        # Check for potentially dangerous keywords
        dangerous_keywords = ["drop", "delete", "insert", "update", "alter", "truncate", "create"]
        for keyword in dangerous_keywords:
            if keyword in sql_clean:
                violations.append(f"Dangerous keyword detected: {keyword}")

        # Check for proper table reference
        if "argo_measurements" not in sql_clean:
            violations.append("Must reference argo_measurements table")

        return len(violations) == 0, violations

    def validate_temperature_threshold_specifically(self, sql: str, query: str) -> Tuple[bool, List[str]]:
        """
        Specific validation for the reported temperature threshold issue.
        This tests the exact case that was failing: "temperature more than 20"
        """
        violations = []
        query_lower = query.lower()
        sql_lower = sql.lower()

        # Check for temperature threshold patterns in the original query
        temp_threshold_patterns = [
            r"temperature\s+(?:is\s+)?(?:more\s+than|greater\s+than|above|over)\s+(\d+(?:\.\d+)?)",
            r"temperatures?\s+(?:higher\s+than|above|over|greater\s+than|more\s+than)\s+(\d+(?:\.\d+)?)",
            r"temperature\s*[>]\s*(\d+(?:\.\d+)?)",
        ]

        temp_value = None
        for pattern in temp_threshold_patterns:
            match = re.search(pattern, query_lower)
            if match:
                temp_value = float(match.group(1))
                break

        if temp_value is not None:
            # The SQL should contain a temperature filter
            expected_filters = [
                f"temperature > {temp_value}",
                f"temperature >= {temp_value}",
            ]

            has_temp_filter = any(filter_expr in sql_lower for filter_expr in expected_filters)

            if not has_temp_filter:
                violations.append(f"Query mentions temperature > {temp_value} but SQL lacks temperature filter")
                violations.append(f"Expected one of: {expected_filters}")
                violations.append(f"Generated SQL: {sql}")

            # Should also have temperature IS NOT NULL
            if "temperature is not null" not in sql_lower:
                violations.append("Missing temperature IS NOT NULL condition")

        return len(violations) == 0, violations

def test_sql_validator():
    """Test the SQL validator with known good and bad cases"""

    validator = SQLValidator()

    # Test case 1: Good SQL with temperature filter
    good_sql = """SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure
                  FROM argo_measurements
                  WHERE temperature > 20 AND temperature IS NOT NULL
                  ORDER BY date DESC LIMIT 1500"""

    # Create a parameter context for temperature > 20
    from .parameter_context import ParameterContext

    context = ParameterContext(
        original_query="temperature more than 20",
        query_id="test",
        temperature_range=(">", 20.0),
        parameters=["temperature"]
    )

    is_valid, violations = validator.validate_sql_against_context(good_sql, context)
    print(f"Good SQL validation: {is_valid}")
    if violations:
        print(f"Violations: {violations}")

    # Test case 2: Bad SQL missing temperature filter (the original problem)
    bad_sql = """SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure
                 FROM argo_measurements
                 WHERE temperature IS NOT NULL
                 ORDER BY date DESC LIMIT 1500"""

    is_valid, violations = validator.validate_sql_against_context(bad_sql, context)
    print(f"Bad SQL validation: {is_valid}")
    if violations:
        print(f"Violations: {violations}")

if __name__ == "__main__":
    test_sql_validator()