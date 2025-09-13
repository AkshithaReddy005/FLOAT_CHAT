"""
Parameter Logger Module
Comprehensive logging for parameter tracking and audit trail.
"""

import logging
import json
from typing import Dict, List, Any
from datetime import datetime
from .parameter_context import ParameterContext


class ParameterLogger:
    """
    Centralized logging for parameter extraction, service calls, and consistency validation.
    Provides full audit trail for debugging inconsistent data flow.
    """
    
    def __init__(self):
        # Set up dedicated logger for parameter tracking
        self.logger = logging.getLogger('parameter_tracker')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for parameter logs
        handler = logging.FileHandler('parameter_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        # Also log to console for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def log_parameter_extraction(self, user_query: str, parameter_context: ParameterContext):
        """Log parameter extraction results"""
        
        log_entry = {
            "event": "parameter_extraction",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "extracted_parameters": {
                "location_name": parameter_context.location_name,
                "location_bounds": parameter_context.location_bounds,
                "date_range": [d.isoformat() for d in parameter_context.date_range] if parameter_context.date_range else None,
                "date_years": parameter_context.date_years,
                "depth_range": parameter_context.depth_range,
                "depth_type": parameter_context.depth_type,
                "parameters": parameter_context.parameters,
                "float_ids": parameter_context.float_ids,
                "is_analytical": parameter_context.is_analytical,
                "is_comparative": parameter_context.is_comparative,
                "complexity_level": parameter_context.complexity_level
            },
            "extraction_method": parameter_context.extraction_method,
            "confidence_score": parameter_context.confidence_score,
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.info(f"PARAMETER_EXTRACTION: {json.dumps(log_entry, indent=2)}")
    
    def log_service_call(self, service_name: str, parameter_context: ParameterContext, 
                        filters_applied: Dict, results_count: int):
        """Log service calls with applied filters"""
        
        log_entry = {
            "event": "service_call",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "filters_applied": filters_applied,
            "results_count": results_count,
            "original_parameters": parameter_context.get_summary()
        }
        
        self.logger.info(f"SERVICE_CALL: {json.dumps(log_entry, indent=2)}")
    
    def log_sql_generation(self, parameter_context: ParameterContext, sql_query: str, 
                          generation_method: str):
        """Log SQL query generation"""
        
        log_entry = {
            "event": "sql_generation",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "generation_method": generation_method,
            "sql_query": sql_query,
            "sql_filters": parameter_context.to_sql_filters(),
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.info(f"SQL_GENERATION: {json.dumps(log_entry, indent=2)}")
    
    def log_chroma_search(self, parameter_context: ParameterContext, chroma_filters: Dict, 
                         results_count: int):
        """Log ChromaDB search with filters"""
        
        log_entry = {
            "event": "chroma_search",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "chroma_filters": chroma_filters,
            "results_count": results_count,
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.info(f"CHROMA_SEARCH: {json.dumps(log_entry, indent=2)}")
    
    def log_consistency_validation(self, parameter_context: ParameterContext, 
                                 validation_report: Dict):
        """Log consistency validation results"""
        
        log_entry = {
            "event": "consistency_validation",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "is_consistent": validation_report["is_consistent"],
            "violations": validation_report["violations"],
            "warnings": validation_report["warnings"],
            "service_stats": validation_report["service_stats"],
            "parameter_summary": parameter_context.get_summary()
        }
        
        if validation_report["is_consistent"]:
            self.logger.info(f"CONSISTENCY_PASS: {json.dumps(log_entry, indent=2)}")
        else:
            self.logger.warning(f"CONSISTENCY_FAIL: {json.dumps(log_entry, indent=2)}")
    
    def log_fallback_applied(self, original_context: ParameterContext, 
                           fallback_context: ParameterContext, reason: str):
        """Log when fallback parameters are applied"""
        
        log_entry = {
            "event": "fallback_applied",
            "query_id": original_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "fallback_reason": reason,
            "original_parameters": original_context.get_summary(),
            "fallback_parameters": fallback_context.get_summary(),
            "parameters_changed": self._compare_contexts(original_context, fallback_context)
        }
        
        self.logger.warning(f"FALLBACK_APPLIED: {json.dumps(log_entry, indent=2)}")
    
    def log_request_failure(self, parameter_context: ParameterContext, failure_reason: str, 
                           service_results: Dict):
        """Log when a request fails due to consistency issues"""
        
        log_entry = {
            "event": "request_failure",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "failure_reason": failure_reason,
            "parameter_summary": parameter_context.get_summary(),
            "service_results": {
                "sql_count": len(service_results.get('sql_results', [])),
                "chroma_count": len(service_results.get('chroma_results', {}).get('documents', [[]])[0]),
                "ai_response_length": len(service_results.get('ai_response', ''))
            }
        }
        
        self.logger.error(f"REQUEST_FAILURE: {json.dumps(log_entry, indent=2)}")
    
    def log_performance_metrics(self, parameter_context: ParameterContext, 
                              timing_data: Dict):
        """Log performance metrics for the request"""
        
        log_entry = {
            "event": "performance_metrics",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "timings": timing_data,
            "total_time": sum(timing_data.values()),
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.info(f"PERFORMANCE: {json.dumps(log_entry, indent=2)}")
    
    def _compare_contexts(self, original: ParameterContext, fallback: ParameterContext) -> List[str]:
        """Compare two parameter contexts and return list of changes"""
        changes = []
        
        # Compare key fields
        if original.location_bounds != fallback.location_bounds:
            changes.append("location_bounds")
        if original.date_range != fallback.date_range:
            changes.append("date_range")
        if original.date_years != fallback.date_years:
            changes.append("date_years")
        if original.depth_range != fallback.depth_range:
            changes.append("depth_range")
        if original.parameters != fallback.parameters:
            changes.append("parameters")
        if original.float_ids != fallback.float_ids:
            changes.append("float_ids")
        
        return changes
    
    def generate_audit_summary(self, query_id: str) -> Dict:
        """Generate summary of all events for a specific query"""
        
        # This would typically read from log files or database
        # For now, return a placeholder structure
        return {
            "query_id": query_id,
            "events_logged": [
                "parameter_extraction",
                "sql_generation", 
                "chroma_search",
                "consistency_validation"
            ],
            "consistency_status": "passed",
            "fallbacks_applied": 0,
            "total_processing_time": "1.2s"
        }
    
    def log_debug_info(self, parameter_context: ParameterContext, debug_data: Dict):
        """Log debug information for troubleshooting"""
        
        log_entry = {
            "event": "debug_info",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "debug_data": debug_data,
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.debug(f"DEBUG: {json.dumps(log_entry, indent=2)}")
    
    def log_user_feedback(self, parameter_context: ParameterContext, feedback_type: str, 
                         feedback_data: Dict):
        """Log user feedback about results quality"""
        
        log_entry = {
            "event": "user_feedback",
            "query_id": parameter_context.query_id,
            "timestamp": datetime.now().isoformat(),
            "feedback_type": feedback_type,  # 'positive', 'negative', 'correction'
            "feedback_data": feedback_data,
            "parameter_summary": parameter_context.get_summary()
        }
        
        self.logger.info(f"USER_FEEDBACK: {json.dumps(log_entry, indent=2)}")


# Global logger instance
parameter_logger = ParameterLogger()
