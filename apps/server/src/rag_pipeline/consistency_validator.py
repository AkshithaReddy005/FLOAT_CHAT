"""
Consistency Validator Module
Validates that returned data matches the requested parameters across all services.
"""

import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime
from .parameter_context import ParameterContext


class ConsistencyValidator:
    """
    Validates data consistency across SQL, ChromaDB, and AI services.
    Ensures all services return data that matches the requested parameters.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_service_consistency(self, parameter_context: ParameterContext, 
                                   sql_results: List[Dict], 
                                   chroma_results: Dict,
                                   ai_response: str) -> Dict[str, Any]:
        """
        Comprehensive consistency validation across all services.
        Returns validation report with any violations found.
        """
        
        validation_report = {
            "is_consistent": True,
            "violations": [],
            "warnings": [],
            "service_stats": {
                "sql_records": len(sql_results),
                "chroma_matches": len(chroma_results.get('documents', [[]])[0]) if chroma_results else 0,
                "parameter_summary": parameter_context.get_summary()
            },
            "validation_timestamp": datetime.now().isoformat()
        }
        
        # Validate SQL results consistency
        sql_consistent, sql_violations = self._validate_sql_consistency(parameter_context, sql_results)
        if not sql_consistent:
            validation_report["is_consistent"] = False
            validation_report["violations"].extend([f"SQL: {v}" for v in sql_violations])
        
        # Validate ChromaDB results consistency
        chroma_consistent, chroma_violations = self._validate_chroma_consistency(parameter_context, chroma_results)
        if not chroma_consistent:
            validation_report["is_consistent"] = False
            validation_report["violations"].extend([f"ChromaDB: {v}" for v in chroma_violations])
        
        # Cross-service consistency checks
        cross_violations = self._validate_cross_service_consistency(parameter_context, sql_results, chroma_results)
        if cross_violations:
            validation_report["warnings"].extend(cross_violations)
        
        # Log validation results
        self._log_validation_results(parameter_context, validation_report)
        
        return validation_report
    
    def _validate_sql_consistency(self, context: ParameterContext, sql_results: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate SQL results match parameter context"""
        violations = []
        
        if not sql_results:
            return True, []  # Empty results are consistent
        
        # Sample first 10 records for validation
        sample_size = min(10, len(sql_results))
        sample_records = sql_results[:sample_size]
        
        for i, record in enumerate(sample_records):
            # Location validation
            if context.location_bounds:
                lat = record.get('latitude')
                lon = record.get('longitude')
                if lat is not None and lon is not None:
                    bounds = context.location_bounds
                    if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and 
                           bounds['lon_min'] <= lon <= bounds['lon_max']):
                        violations.append(
                            f"Record {i}: location ({lat:.2f}, {lon:.2f}) outside bounds "
                            f"({bounds['lat_min']}-{bounds['lat_max']}°N, {bounds['lon_min']}-{bounds['lon_max']}°E)"
                        )
            
            # Temporal validation
            if context.date_years:
                date_str = record.get('date')
                if date_str:
                    try:
                        year = datetime.fromisoformat(date_str.replace('Z', '+00:00')).year
                        if year not in context.date_years:
                            violations.append(f"Record {i}: year {year} not in requested years {context.date_years}")
                    except Exception as e:
                        violations.append(f"Record {i}: invalid date format '{date_str}'")
            
            elif context.date_range:
                date_str = record.get('date')
                if date_str:
                    try:
                        record_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        start_date, end_date = context.date_range
                        if not (start_date <= record_date <= end_date):
                            violations.append(
                                f"Record {i}: date {record_date.date()} outside range "
                                f"{start_date.date()}-{end_date.date()}"
                            )
                    except Exception as e:
                        violations.append(f"Record {i}: invalid date format '{date_str}'")
            
            # Depth validation
            if context.depth_range:
                depth = record.get('depth')
                if depth is not None:
                    if context.depth_type == 'operator':
                        operator, value = context.depth_range
                        if operator == '>=' and depth < value:
                            violations.append(f"Record {i}: depth {depth}m violates {operator} {value}m")
                        elif operator == '<=' and depth > value:
                            violations.append(f"Record {i}: depth {depth}m violates {operator} {value}m")
                    else:
                        min_depth, max_depth = context.depth_range
                        if not (min_depth <= depth <= max_depth):
                            violations.append(f"Record {i}: depth {depth}m outside range {min_depth}-{max_depth}m")
            
            # Float ID validation
            if context.float_ids:
                float_id = record.get('float_id')
                if float_id and float_id not in context.float_ids:
                    violations.append(f"Record {i}: float_id {float_id} not in requested list {context.float_ids}")
            
            # Parameter validation (ensure requested parameters have values)
            if context.parameters:
                for param in context.parameters:
                    if record.get(param) is None:
                        violations.append(f"Record {i}: requested parameter '{param}' is null")
        
        return len(violations) == 0, violations
    
    def _validate_chroma_consistency(self, context: ParameterContext, chroma_results: Dict) -> Tuple[bool, List[str]]:
        """Validate ChromaDB results match parameter context"""
        violations = []
        
        if not chroma_results or not chroma_results.get('documents'):
            return True, []  # Empty results are consistent
        
        documents = chroma_results.get('documents', [[]])[0]
        metadatas = chroma_results.get('metadatas', [[]])[0] if chroma_results.get('metadatas') else []
        
        # If we have metadata, validate it matches our filters
        if metadatas and len(metadatas) > 0:
            sample_size = min(5, len(metadatas))
            for i, metadata in enumerate(metadatas[:sample_size]):
                if not metadata:
                    continue
                
                # Location validation
                if context.location_bounds:
                    lat = metadata.get('latitude')
                    lon = metadata.get('longitude')
                    if lat is not None and lon is not None:
                        bounds = context.location_bounds
                        if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and 
                               bounds['lon_min'] <= lon <= bounds['lon_max']):
                            violations.append(
                                f"ChromaDB metadata {i}: location ({lat}, {lon}) outside bounds"
                            )
                
                # Temporal validation
                if context.date_years:
                    year = metadata.get('year')
                    if year and year not in context.date_years:
                        violations.append(f"ChromaDB metadata {i}: year {year} not in requested years")
                
                # Depth validation
                if context.depth_range and context.depth_type != 'operator':
                    depth = metadata.get('depth')
                    if depth is not None:
                        min_depth, max_depth = context.depth_range
                        if not (min_depth <= depth <= max_depth):
                            violations.append(f"ChromaDB metadata {i}: depth {depth} outside range")
        
        return len(violations) == 0, violations
    
    def _validate_cross_service_consistency(self, context: ParameterContext, 
                                          sql_results: List[Dict], 
                                          chroma_results: Dict) -> List[str]:
        """Validate consistency between different services"""
        warnings = []
        
        sql_count = len(sql_results)
        chroma_count = len(chroma_results.get('documents', [[]])[0]) if chroma_results else 0
        
        # Check for significant discrepancies in result counts
        if sql_count > 0 and chroma_count == 0:
            warnings.append(f"SQL returned {sql_count} records but ChromaDB returned 0 matches")
        elif sql_count == 0 and chroma_count > 0:
            warnings.append(f"ChromaDB returned {chroma_count} matches but SQL returned 0 records")
        elif sql_count > 0 and chroma_count > 0:
            ratio = max(sql_count, chroma_count) / min(sql_count, chroma_count)
            if ratio > 10:  # More than 10x difference
                warnings.append(
                    f"Large discrepancy: SQL={sql_count} records, ChromaDB={chroma_count} matches (ratio: {ratio:.1f}x)"
                )
        
        # Check for parameter coverage
        if context.parameters and sql_results:
            for param in context.parameters:
                non_null_count = sum(1 for r in sql_results[:10] if r.get(param) is not None)
                if non_null_count < len(sql_results[:10]) * 0.5:  # Less than 50% coverage
                    warnings.append(f"Low coverage for parameter '{param}': only {non_null_count}/10 records have values")
        
        return warnings
    
    def _log_validation_results(self, context: ParameterContext, validation_report: Dict):
        """Log validation results for audit trail"""
        
        log_entry = {
            "query_id": context.query_id,
            "query": context.original_query,
            "parameters": context.get_summary(),
            "is_consistent": validation_report["is_consistent"],
            "violation_count": len(validation_report["violations"]),
            "warning_count": len(validation_report["warnings"]),
            "service_stats": validation_report["service_stats"]
        }
        
        if validation_report["is_consistent"]:
            self.logger.info(f"Consistency validation PASSED for query {context.query_id}: {log_entry}")
        else:
            self.logger.warning(f"Consistency validation FAILED for query {context.query_id}: {log_entry}")
            for violation in validation_report["violations"]:
                self.logger.warning(f"  VIOLATION: {violation}")
        
        for warning in validation_report["warnings"]:
            self.logger.info(f"  WARNING: {warning}")
    
    def should_fail_request(self, validation_report: Dict) -> Tuple[bool, str]:
        """
        Determine if request should fail based on validation results.
        Returns (should_fail, reason)
        """
        
        violations = validation_report["violations"]
        
        # Critical violations that should fail the request
        critical_patterns = [
            "outside bounds",
            "not in requested years",
            "violates",
            "not in requested list"
        ]
        
        critical_violations = [
            v for v in violations 
            if any(pattern in v for pattern in critical_patterns)
        ]
        
        if len(critical_violations) >= 3:  # Multiple critical violations
            return True, f"Multiple consistency violations detected: {len(critical_violations)} critical issues"
        
        # Check for systematic violations (affecting >30% of sample)
        if len(violations) > 3:
            return True, f"Systematic consistency failure: {len(violations)} violations detected"
        
        return False, ""
    
    def generate_fallback_explanation(self, context: ParameterContext, 
                                    validation_report: Dict) -> str:
        """Generate user-friendly explanation of what went wrong and what fallback was applied"""
        
        violations = validation_report["violations"]
        if not violations:
            return ""
        
        explanation_parts = [
            f"I found some data that doesn't exactly match your request for: {context.get_summary()}"
        ]
        
        # Categorize violations
        location_issues = [v for v in violations if "location" in v or "bounds" in v]
        temporal_issues = [v for v in violations if "year" in v or "date" in v]
        depth_issues = [v for v in violations if "depth" in v]
        
        if location_issues:
            explanation_parts.append("• Some results are outside the requested geographic area")
        if temporal_issues:
            explanation_parts.append("• Some data is from different time periods than requested")
        if depth_issues:
            explanation_parts.append("• Some measurements are from different depths than specified")
        
        explanation_parts.append(
            "I've filtered the results to show the closest matches available. "
            "You might want to try a broader search or different parameters."
        )
        
        return "\n".join(explanation_parts)
