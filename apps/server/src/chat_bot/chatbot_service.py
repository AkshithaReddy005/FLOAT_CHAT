"""
Enhanced Chatbot Service with Modular RAG Implementation
Uses separated modules for query classification, SQL generation, visualization, and RAG responses.
"""

from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from database.database import ArgoMeasurement
from analysis.oceanographic_intelligence import OceanographicIntelligence, AnalysisResult
from analysis.query_intelligence import QueryIntelligence, QueryEnhancement
from rag_pipeline.vector_store import VectorStore
from rag_pipeline.query_classifier import QueryClassifier
from rag_pipeline.sql_generator import SQLGenerator
from utils.visualization_builder import VisualizationBuilder
from rag_pipeline.rag_engine import RAGEngine
from rag_pipeline.unified_query_parser import UnifiedQueryParser
from rag_pipeline.consistency_validator import ConsistencyValidator
from rag_pipeline.parameter_logger import parameter_logger
import time
import os

load_dotenv()


class ChatbotService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        
        # Initialize services
        self.query_classifier = QueryClassifier()
        self.sql_generator = SQLGenerator()
        
        # Initialize parser with LLM strategy if API key available
        gemini_key = os.getenv('GEMINI_API_KEY')
        extraction_strategy = os.getenv('PARAM_EXTRACTOR', 'llm_first' if gemini_key else 'heuristic_only')
        self.query_parser = UnifiedQueryParser(gemini_key, extraction_strategy)
        self.visualization_builder = VisualizationBuilder()
        self.rag_engine = RAGEngine()
        
        # Initialize new unified components
        self.consistency_validator = ConsistencyValidator()

        # Initialize intelligent analysis engines
        try:
            self.oceanographic_intelligence = OceanographicIntelligence()
            self.query_intelligence = QueryIntelligence()
            print("Enhanced Chatbot Service initialized with intelligent analysis capabilities")
        except ImportError as e:
            print(f"Warning: Advanced analysis libraries not available: {e}")
            self.oceanographic_intelligence = None
            self.query_intelligence = None
            print("Enhanced Chatbot Service initialized with basic capabilities")
    
    async def process_chat_query(self, user_query: str, db: Session, session_context: dict = None) -> Dict:
        """Process a natural language query using intelligent analysis"""

        start_time = time.time()
        timing_data = {}

        # Step 1: Intelligent Query Enhancement
        if self.query_intelligence:
            query_enhancement = self.query_intelligence.enhance_query(user_query)
            print(f"Query Intelligence: Intent={query_enhancement.intent}, Complexity={query_enhancement.complexity_level}")
        else:
            query_enhancement = None

        # Initialize pipeline flow tracking
        pipeline_flow = {
            "total_duration": "0.000s",
            "steps": [],
            "parameter_extraction": {},
            "sql_generation": {},
            "chroma_search": {},
            "api_response": {},
            "consistency_validation": {}
        }
        
        try:
            # Step 1: Classify the query
            classify_start = time.time()
            query_classification = self.query_classifier.classify_query(user_query)
            timing_data['classification'] = time.time() - classify_start
            
            # Step 2: UNIFIED PARAMETER EXTRACTION (Single Source of Truth)
            parse_start = time.time()
            parameter_context = self.query_parser.parse_query(user_query, session_context, query_classification)
            step_time = time.time() - parse_start
            timing_data['parameter_extraction'] = step_time
            
            # Track parameter extraction in pipeline flow
            pipeline_flow["parameter_extraction"] = {
                "duration": f"{step_time:.4f}s",
                "input_query": user_query,
                "extracted_location": parameter_context.location_name or "Not specified",
                "extracted_parameters": parameter_context.parameters or [],
                "extracted_years": parameter_context.date_years or [],
                "confidence_score": parameter_context.confidence_score,
                "complexity_level": parameter_context.complexity_level,
                "is_chart_request": parameter_context.is_chart_request,
                "summary": parameter_context.get_summary()
            }
            pipeline_flow["steps"].append({
                "step": "Parameter Extraction",
                "duration": f"{step_time:.4f}s",
                "status": "success",
                "details": f"Extracted {len(parameter_context.parameters or [])} parameters with {(parameter_context.confidence_score * 100):.1f}% confidence"
            })
            
            # Log parameter extraction
            parameter_logger.log_parameter_extraction(user_query, parameter_context)
            
            print(f"Unified Parameters: {parameter_context.get_summary()}")
            
        except Exception as e:
            print(f"Query processing failed: {e}")
            # Create fallback response
            return await self.create_fallback_response(user_query, db)
        
        try:
            # Step 3: Retrieve comprehensive context using unified parameter context
            context_start = time.time()

            # Dynamically determine context size based on query complexity and expected data volume
            base_context_size = 25
            if parameter_context.complexity_level == "complex":
                context_size = 75  # More context for complex queries
            elif parameter_context.is_full_data_request:
                context_size = 100  # Comprehensive context for full data requests
            elif parameter_context.is_analytical:
                context_size = 50  # Enhanced context for analytical queries
            else:
                context_size = base_context_size

            print(f"Requesting {context_size} context documents for query complexity: {parameter_context.complexity_level}")
            context_results = self.vector_store.search_with_context(parameter_context, n_results=context_size)
            step_time = time.time() - context_start
            timing_data['context_retrieval'] = step_time
            
            # Track ChromaDB search in pipeline flow
            chroma_filters = parameter_context.to_chroma_filters()
            documents_found = len(context_results.get('documents', [[]])[0])
            
            pipeline_flow["chroma_search"] = {
                "duration": f"{step_time:.4f}s",
                "search_filters": chroma_filters,
                "documents_found": documents_found,
                "n_results_requested": context_size,
                "sample_documents": context_results.get('documents', [[]])[0][:3] if documents_found > 0 else [],
                "distances": context_results.get('distances', [[]])[0][:3] if documents_found > 0 else []
            }
            pipeline_flow["steps"].append({
                "step": "ChromaDB Vector Search",
                "duration": f"{step_time:.4f}s",
                "status": "success",
                "details": f"Vector search returned {documents_found} documents"
            })
            
            # Log ChromaDB search
            parameter_logger.log_chroma_search(
                parameter_context, chroma_filters, documents_found
            )
            
            # Filter out very short or irrelevant context
            if context_results.get('documents') and context_results['documents'][0]:
                documents = context_results['documents'][0]
                filtered_docs = [doc for doc in documents if len(doc.strip()) > 30]
                context_results['documents'] = [filtered_docs] if filtered_docs else [[]]
        except Exception as e:
            print(f"Context retrieval failed: {e}")
            context_results = {'documents': [[]], 'distances': [[]]}
        
        # Step 4: Get data using unified parameter context
        db_results = []
        sql_used = None
        
        if parameter_context.is_chart_request or query_classification["needs_data"]:
            try:
                # Generate SQL using unified parameter context
                sql_start = time.time()
                sql_query = await self.sql_generator.generate_sql_from_context(parameter_context)
                sql_gen_time = time.time() - sql_start
                timing_data['sql_generation'] = sql_gen_time
                
                # Debug: Log SQL query to check if it's filtering properly
                print(f"DEBUG: Generated SQL query: {sql_query}")
                print(f"DEBUG: Parameter context location: {parameter_context.location_name}")
                print(f"DEBUG: Parameter context bounds: {parameter_context.location_bounds}")
                print(f"DEBUG: Parameter context depth_range: {parameter_context.depth_range}")
                print(f"DEBUG: Parameter context depth_type: {parameter_context.depth_type}")
                print(f"DEBUG: Parameter extraction method: {getattr(parameter_context, 'extraction_method', 'unknown')}")
                
                if sql_query and self.sql_generator.validate_sql(sql_query):
                    # Log SQL generation
                    parameter_logger.log_sql_generation(
                        parameter_context, sql_query, "unified_context"
                    )
                    
                    # Execute SQL
                    execute_start = time.time()
                    db_results = self._execute_sql_query(db, sql_query)
                    execute_time = time.time() - execute_start
                    timing_data['sql_execution'] = execute_time
                    sql_used = sql_query
                    
                    # Track SQL generation and execution in pipeline flow
                    pipeline_flow["sql_generation"] = {
                        "generation_duration": f"{sql_gen_time:.4f}s",
                        "execution_duration": f"{execute_time:.4f}s",
                        "total_duration": f"{(sql_gen_time + execute_time):.4f}s",
                        "generated_query": sql_query,
                        "sql_filters": parameter_context.to_sql_filters(),
                        "records_returned": len(db_results),
                        "sample_results": [dict(row) if hasattr(row, '_asdict') else row for row in db_results[:3]] if db_results else []
                    }
                    pipeline_flow["steps"].append({
                        "step": "SQL Generation & Execution",
                        "duration": f"{(sql_gen_time + execute_time):.4f}s",
                        "status": "success",
                        "details": f"Generated and executed SQL query, returned {len(db_results)} records"
                    })
                    
                    print(f"Unified SQL returned {len(db_results)} results")
                    
                    # Log service call
                    parameter_logger.log_service_call(
                        "SQL", parameter_context, parameter_context.to_sql_filters(), len(db_results)
                    )
                else:
                    print(f"SQL validation failed, using fallback")
                    db_results = self._fallback_data_retrieval(db, user_query)
                    sql_used = "Fallback query due to validation failure"
                    
            except Exception as e:
                print(f"Unified data retrieval failed: {e}")
                db_results = self._fallback_data_retrieval(db, user_query)
                sql_used = "Emergency fallback query"
        
        # Step 5: Validate consistency before proceeding
        validation_start = time.time()
        validation_report = self.consistency_validator.validate_service_consistency(
            parameter_context, db_results, context_results, ""
        )
        step_time = time.time() - validation_start
        timing_data['consistency_validation'] = step_time
        
        # Track consistency validation in pipeline flow
        pipeline_flow["consistency_validation"] = {
            "duration": f"{step_time:.4f}s",
            "is_consistent": validation_report["is_consistent"],
            "violations_count": len(validation_report.get("violations", [])),
            "violations": validation_report.get("violations", []),
            # derive a simple score if not provided
            "consistency_score": 1.0 if validation_report.get("is_consistent", True) else max(0.0, 1.0 - (len(validation_report.get("violations", [])) / 10.0)),
            "detailed_report": {
                "warnings": validation_report.get("warnings", []),
                "service_stats": validation_report.get("service_stats", {})
            }
        }
        pipeline_flow["steps"].append({
            "step": "Consistency Validation",
            "duration": f"{step_time:.4f}s",
            "status": "success" if validation_report["is_consistent"] else "warning",
            "details": f"Found {len(validation_report.get('violations', []))} violations, consistency score: "
                       f"{(1.0 if validation_report.get('is_consistent', True) else max(0.0, 1.0 - (len(validation_report.get('violations', [])) / 10.0))):.2f}"
        })
        
        # Log validation results
        parameter_logger.log_consistency_validation(parameter_context, validation_report)
        
        # Check if we should fail the request due to consistency issues
        should_fail, failure_reason = self.consistency_validator.should_fail_request(validation_report)
        if should_fail:
            parameter_logger.log_request_failure(
                parameter_context, failure_reason, 
                {'sql_results': db_results, 'chroma_results': context_results}
            )
            
            # Generate fallback with explanation
            fallback_explanation = self.consistency_validator.generate_fallback_explanation(
                parameter_context, validation_report
            )
            
            return {
                "response": f"I found some inconsistencies in the data that don't match your request exactly. {fallback_explanation}",
                "data": db_results[:10],  # Limited data for safety
                "visualization": {"map": {"points": []}, "depth_profile": {"data": []}},
                "query_params": {
                    "consistency_failed": True,
                    "failure_reason": failure_reason,
                    "parameter_summary": parameter_context.get_summary()
                },
                "context_count": 0
            }
        
        # Step 6: Apply accurate filtering and get real counts BEFORE AI generation
        filtered_data, actual_count, display_count = self._apply_accurate_filtering_and_limiting(db_results, user_query, query_classification, parameter_context)

        try:
            # Step 7: Generate AI response using intelligent analysis + RAG
            ai_start = time.time()

            # Step 7a: Perform Intelligent Oceanographic Analysis
            intelligent_analysis = None
            if self.oceanographic_intelligence and filtered_data:
                try:
                    intelligent_analysis = self.oceanographic_intelligence.perform_intelligent_analysis(
                        user_query, filtered_data
                    )
                    print(f"Intelligent Analysis: {intelligent_analysis.analysis_type} with {len(intelligent_analysis.primary_findings)} findings")
                except Exception as e:
                    print(f"Intelligent analysis failed: {e}")

            # Pass comprehensive context to AI
            enhanced_session_context = session_context.copy() if session_context else {}
            enhanced_session_context['actual_count'] = actual_count
            enhanced_session_context['sql_limit_applied'] = len(db_results) < actual_count
            enhanced_session_context['display_limited'] = display_count < actual_count
            enhanced_session_context['intelligent_analysis'] = intelligent_analysis
            enhanced_session_context['query_enhancement'] = query_enhancement

            ai_response = await self.rag_engine.generate_response(
                user_query, context_results, db_results, query_classification,
                enhanced_session_context, parameter_context.is_chart_request
            )
            step_time = time.time() - ai_start
            timing_data['ai_generation'] = step_time
            
            # Track AI response generation in pipeline flow
            pipeline_flow["api_response"] = {
                "duration": f"{step_time:.4f}s",
                "response_type": "ai_generated",
                "data_points": len(db_results),
                "context_documents_used": len(context_results.get('documents', [[]])[0]),
                "visualization_requested": parameter_context.is_chart_request,
                "ai_summary": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
            }
            pipeline_flow["steps"].append({
                "step": "AI Response Generation",
                "duration": f"{step_time:.4f}s",
                "status": "success",
                "details": f"Generated AI response using {len(context_results.get('documents', [[]])[0])} context documents"
            })
        except Exception as e:
            print(f"AI response generation failed: {e}")
            ai_response = self._generate_emergency_response(user_query, db_results, query_classification)
        
        try:
            # Step 8: Build visualization data using FILTERED data for consistency
            viz_start = time.time()
            min_data_required = 5 if parameter_context.is_chart_request else 10

            if len(filtered_data) >= min_data_required:
                print(f"Building visualization with {len(filtered_data)} filtered results (from {len(db_results)} raw results)")
                if filtered_data:
                    sample = filtered_data[0]
                    print(f"Visualization sample - lat/lon: {sample.get('latitude')}, {sample.get('longitude')}, temp: {sample.get('temperature')}")

                viz_data = await self.visualization_builder.build_visualization(
                    filtered_data, query_classification, user_query, context_results
                )

                if parameter_context.is_chart_request or self._has_meaningful_visualizations(viz_data):
                    print(f"Visualization data generated successfully with {len(filtered_data)} consistent data points")
                else:
                    viz_data = {"map": {"points": []}, "depth_profile": {"data": []},
                              "reasoning": "Insufficient data quality for meaningful visualizations"}
            else:
                viz_data = {"map": {"points": []}, "depth_profile": {"data": []},
                          "reasoning": f"Only {len(filtered_data)} filtered data points - minimum {min_data_required} required"}

            timing_data['visualization'] = time.time() - viz_start
                
        except Exception as e:
            print(f"Visualization building failed: {e}")
            viz_data = {"map": {"points": []}, "depth_profile": {"data": []}, 
                       "reasoning": "Visualization generation error"}
        
        # Step 9: Generate response summary and finalize
        try:
            response_summary = self.rag_engine.generate_response_summary(ai_response, db_results, query_classification)
        except Exception as e:
            print(f"Failed to generate response summary: {e}")
            response_summary = "AI response generated"

        # Calculate total processing time
        total_time = time.time() - start_time
        timing_data['total'] = total_time
        
        # Finalize pipeline flow tracking
        pipeline_flow["total_duration"] = f"{total_time:.4f}s"
        
        # Log performance metrics
        parameter_logger.log_performance_metrics(parameter_context, timing_data)
        
        # Prepare unified response with accurate counting
        return {
            "response": ai_response,
            "data": filtered_data,
            "visualization": viz_data,
            "pipeline_flow": pipeline_flow,  # Add pipeline flow data to response
            "query_params": {
                "classification": query_classification,
                "parameter_summary": parameter_context.get_summary(),
                "sql_used": sql_used,
                "context_retrieved": len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0,
                "actual_data_count": actual_count,    # Real count from database
                "data_points": len(db_results),       # SQL result count (may be limited by LIMIT clause)
                "display_count": display_count,       # What's actually shown to user
                "limited_to": display_count,          # Backward compatibility
                "data_transparency": {
                    "total_matching": actual_count,
                    "sql_returned": len(db_results),
                    "displayed": display_count,
                    "is_limited": display_count < actual_count,
                    "limitation_reason": "Display optimization" if display_count < actual_count else None
                },
                "consistency_status": "passed" if validation_report["is_consistent"] else "failed",
                "processing_time": f"{timing_data['total']:.2f}s"
            },
            "context_count": len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0,
            "response_summary": response_summary
        }

    async def create_fallback_response(self, user_query: str, db: Session) -> Dict:
        """Create a fallback response when the main pipeline fails"""
        
        try:
            # Try to get some recent data to show the system is working
            recent_data = self._get_sample_data(db)
            
            # Create a helpful response explaining what we can do
            fallback_response = (
                f"I understand you're asking about '{user_query}'. While I'm experiencing some technical "
                f"difficulties with my advanced analysis features, I can still help you explore our ARGO data! "
                f"\n\nOur database contains {len(recent_data)} sample measurements from ARGO oceanographic floats "
                f"with temperature, salinity, depth, and location data. You can:\n\n"
                f"• Ask about specific ocean regions or geographic areas\n"
                f"• Request recent measurements or data from particular time periods\n"
                f"• Compare temperature or salinity between different areas\n"
                f"• Explore depth profiles and vertical ocean structure\n\n"
                f"Try rephrasing your question or asking about what data is available. "
                f"I'm working to resolve the technical issue and provide better responses."
            )
            
            return {
                "response": fallback_response,
                "data": recent_data,
                "visualization": {"map": {"points": []}, "depth_profile": {"data": []}},
                "query_params": {
                    "classification": {"needs_data": True, "is_analytical": False},
                    "sql_used": None,
                    "context_retrieved": 0,
                    "data_points": len(recent_data)
                },
                "context_count": 0
            }
        except Exception as e:
            print(f"Even fallback response failed: {e}")
            # Ultimate fallback
            return {
                "response": (
                    "I'm experiencing technical difficulties, but I'm here to help you explore ARGO oceanographic data. "
                    "Our system contains measurements of temperature, salinity, depth, and pressure from ARGO floats "
                    "across ocean regions. Please try asking about specific locations, recent data, or measurement types. "
                    "I'll do my best to provide useful information once the technical issue is resolved."
                ),
                "data": [],
                "visualization": {"map": {"points": []}, "depth_profile": {"data": []}},
                "query_params": {"classification": {"needs_data": False}, "sql_used": None, 
                               "context_retrieved": 0, "data_points": 0},
                "context_count": 0
            }
    
    def _execute_sql_query(self, db: Session, sql: str) -> List[Dict]:
        """Execute a validated SQL query and return results"""
        try:
            sql_no_semicolon = sql.strip().rstrip(';')
            rows = db.execute(text(sql_no_semicolon)).mappings().all()
            
            results = []
            for r in rows:
                # Ensure all expected keys exist with proper handling
                result = {
                    "float_id": str(r.get("float_id", "")),
                    "latitude": float(r.get("latitude")) if r.get("latitude") is not None else None,
                    "longitude": float(r.get("longitude")) if r.get("longitude") is not None else None,
                    "date": r.get("date").isoformat() if r.get("date") else None,
                    "depth": float(r.get("depth")) if r.get("depth") is not None else None,
                    "temperature": float(r.get("temperature")) if r.get("temperature") is not None else None,
                    "salinity": float(r.get("salinity")) if r.get("salinity") is not None else None,
                    "pressure": float(r.get("pressure")) if r.get("pressure") is not None else None,
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error executing SQL query: {e}")
            return []
    
    def _fallback_data_retrieval(self, db: Session, user_query: str) -> List[Dict]:
        """Smart fallback method for data retrieval when SQL generation fails - only real data"""
        try:
            query_lower = user_query.lower()
            from sqlalchemy import and_, or_
            
            # Start with base query filtering out fake data
            base_query = db.query(ArgoMeasurement).filter(
                ArgoMeasurement.latitude != 0,
                ArgoMeasurement.longitude != 0,
                ArgoMeasurement.latitude.isnot(None),
                ArgoMeasurement.longitude.isnot(None)
            )
            
            # Apply intelligent filters based on query content
            filters_applied = []
            
            # Temperature-related queries
            if any(word in query_lower for word in ['temperature', 'temp', 'warm', 'cold', 'thermal']):
                base_query = base_query.filter(ArgoMeasurement.temperature.isnot(None))
                filters_applied.append("temperature data")
            
            # Salinity-related queries  
            if any(word in query_lower for word in ['salinity', 'salt', 'saline']):
                base_query = base_query.filter(ArgoMeasurement.salinity.isnot(None))
                filters_applied.append("salinity data")
                
            # Depth-related queries
            if any(word in query_lower for word in ['depth', 'deep', 'shallow', 'surface', 'bottom']):
                if 'surface' in query_lower or 'shallow' in query_lower:
                    base_query = base_query.filter(ArgoMeasurement.depth < 100)
                    filters_applied.append("shallow water")
                elif 'deep' in query_lower or 'bottom' in query_lower:
                    base_query = base_query.filter(ArgoMeasurement.depth > 500)
                    filters_applied.append("deep water")
            
            # Geographic filters (basic)
            if any(word in query_lower for word in ['mumbai', 'bombay']):
                # Mumbai area: roughly 19°N, 73°E with some tolerance
                base_query = base_query.filter(
                    ArgoMeasurement.latitude.between(18, 20),
                    ArgoMeasurement.longitude.between(72, 74)
                )
                filters_applied.append("Mumbai region")
            elif any(word in query_lower for word in ['arabian sea', 'arabian']):
                # Arabian Sea: roughly 15-25°N, 65-75°E
                base_query = base_query.filter(
                    ArgoMeasurement.latitude.between(15, 25),
                    ArgoMeasurement.longitude.between(65, 75)
                )
                filters_applied.append("Arabian Sea")
            elif any(word in query_lower for word in ['indian ocean', 'indian']):
                # Broader Indian Ocean
                base_query = base_query.filter(
                    ArgoMeasurement.latitude.between(-30, 30),
                    ArgoMeasurement.longitude.between(40, 100)
                )
                filters_applied.append("Indian Ocean")
            
            # Recent data preference
            if any(word in query_lower for word in ['recent', 'latest', 'current', 'now']):
                base_query = base_query.order_by(ArgoMeasurement.date.desc())
                filters_applied.append("recent data first")
            else:
                # Default to diverse sampling
                base_query = base_query.order_by(ArgoMeasurement.id.desc())
            
            # Limit results intelligently
            if any(word in query_lower for word in ['all', 'every', 'total', 'complete']):
                limit = 500  # More comprehensive for broad requests
            else:
                limit = 150  # Reasonable sample for most queries
            
            results = base_query.limit(limit).all()
            
            print(f"Fallback retrieval: Applied filters: {', '.join(filters_applied) if filters_applied else 'none'}, returned {len(results)} results")
            
            # Filter results to ensure only real data is returned
            return [
                {
                    "float_id": r.float_id,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "date": r.date.isoformat() if r.date else None,
                    "depth": r.depth,
                    "temperature": r.temperature,
                    "salinity": r.salinity,
                    "pressure": r.pressure
                }
                for r in results
                if (r.float_id and 
                    not r.float_id.startswith('float_') and 
                    not r.float_id.startswith('FLOAT_00000') and
                    r.latitude != 0 and r.longitude != 0)
            ]
        except Exception as e:
            print(f"Error in fallback data retrieval: {e}")
            # Final fallback - just get some recent data (but still filter out fake data)
            try:
                results = db.query(ArgoMeasurement).filter(
                    ArgoMeasurement.latitude != 0,
                    ArgoMeasurement.longitude != 0,
                    ArgoMeasurement.latitude.isnot(None),
                    ArgoMeasurement.longitude.isnot(None)
                ).order_by(ArgoMeasurement.date.desc()).limit(50).all()
                
                return [
                    {
                        "float_id": r.float_id,
                        "latitude": r.latitude, 
                        "longitude": r.longitude,
                        "date": r.date.isoformat() if r.date else None,
                        "depth": r.depth,
                        "temperature": r.temperature,
                        "salinity": r.salinity,
                        "pressure": r.pressure
                    }
                    for r in results
                    if (r.float_id and 
                        not r.float_id.startswith('float_') and 
                        not r.float_id.startswith('FLOAT_00000') and
                        r.latitude != 0 and r.longitude != 0)
                ]
            except:
                return []

    def _generate_emergency_response(self, user_query: str, db_results: List[Dict]) -> str:
        """Generate an emergency response when AI response generation fails"""
        
        if not db_results:
            return (
                f"I understand you're asking about '{user_query}'. While I'm having some technical "
                f"difficulties with my analysis capabilities, I want to help you find relevant ARGO data. "
                f"Unfortunately, I couldn't find specific measurements matching your query right now. "
                f"\n\nThis could be because:\n"
                f"• The specific location or time period you're interested in isn't in our current dataset\n"
                f"• The combination of parameters you're looking for requires a different search approach\n"
                f"• There might be a temporary technical issue\n\n"
                f"You can try:\n"
                f"• Asking about broader geographic regions or longer time periods\n"
                f"• Requesting recent measurements from major ocean areas\n"
                f"• Exploring what data is available in our system\n\n"
                f"I'm working to resolve any technical issues and provide better responses."
            )
        
        # Generate basic statistical response
        count = len(db_results)
        unique_floats = len(set(r['float_id'] for r in db_results))
        
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        
        response_parts = [
            f"I found {count} ARGO measurements from {unique_floats} different floats that relate to your query: '{user_query}'."
        ]
        
        if temps:
            avg_temp = sum(temps) / len(temps)
            min_temp, max_temp = min(temps), max(temps)
            response_parts.append(
                f"Temperature data shows values from {min_temp:.1f}°C to {max_temp:.1f}°C (average: {avg_temp:.1f}°C)."
            )
        
        if salinities:
            avg_sal = sum(salinities) / len(salinities)
            min_sal, max_sal = min(salinities), max(salinities)
            response_parts.append(
                f"Salinity measurements range from {min_sal:.2f} to {max_sal:.2f} (average: {avg_sal:.2f})."
            )
        
        if depths:
            min_depth, max_depth = min(depths), max(depths)
            response_parts.append(
                f"Depth coverage spans from {min_depth:.0f}m to {max_depth:.0f}m."
            )
        
        response_parts.append(
            "\nWhile I'm experiencing some technical difficulties with advanced analysis, "
            "you can explore this data using the interactive visualizations below. "
            "Feel free to ask more specific questions about what you see in the data!"
        )
        
        return " ".join(response_parts)

    def _apply_accurate_filtering_and_limiting(self, db_results: List[Dict], user_query: str,
                                             query_classification: Dict, parameter_context) -> Tuple[List[Dict], int, int]:
        """Apply accurate filtering based on user query and return transparent counts"""

        if not db_results:
            return [], 0, 0

        # First, get the actual count that matches the query criteria
        # We need to execute a COUNT query to get the true total
        actual_count = self._get_actual_count(parameter_context)

        # Apply post-SQL filtering for exact parameter matches (like temp > 20)
        filtered_results = self._apply_parameter_specific_filtering(db_results, parameter_context, user_query)

        # Apply intelligent limiting for display purposes
        display_results = self._intelligently_limit_data(filtered_results, user_query, query_classification)

        return display_results, actual_count, len(display_results)

    def _get_actual_count(self, parameter_context) -> int:
        """Get the actual count of data that matches the query criteria"""
        try:
            from database.database import SessionLocal
            from sqlalchemy import text

            db = SessionLocal()
            try:
                # Build a COUNT query using the same filters as the main query
                count_sql = self._build_count_query(parameter_context)
                print(f"DEBUG: Executing count query: {count_sql}")

                if count_sql:
                    result = db.execute(text(count_sql)).fetchone()
                    actual_count = result[0] if result else 0
                    print(f"DEBUG: Count query returned: {actual_count}")
                    return actual_count
                else:
                    # Fallback: get total database count if no filters
                    result = db.execute(text("SELECT COUNT(*) FROM argo_measurements")).fetchone()
                    fallback_count = result[0] if result else 0
                    print(f"DEBUG: Fallback count query returned: {fallback_count}")
                    return fallback_count
            finally:
                db.close()
        except Exception as e:
            print(f"ERROR: Failed to get actual count: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _build_count_query(self, parameter_context) -> Optional[str]:
        """Build a COUNT query based on parameter context"""
        try:
            where_conditions = []

            # Location filter
            if parameter_context.location_bounds:
                bounds = parameter_context.location_bounds
                where_conditions.append(f"latitude BETWEEN {bounds['lat_min']} AND {bounds['lat_max']}")
                where_conditions.append(f"longitude BETWEEN {bounds['lon_min']} AND {bounds['lon_max']}")

            # Temporal filter
            if parameter_context.date_years:
                year_conditions = [f"(date >= '{year}-01-01' AND date <= '{year}-12-31')" for year in parameter_context.date_years]
                where_conditions.append(f"({' OR '.join(year_conditions)})")
            elif parameter_context.date_range:
                start_date, end_date = parameter_context.date_range
                where_conditions.append(f"date >= '{start_date.isoformat()}'")
                where_conditions.append(f"date <= '{end_date.isoformat()}'")

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

            # Temperature threshold filter
            if parameter_context.temperature_range:
                operator, temp_value = parameter_context.temperature_range
                where_conditions.append(f"temperature {operator} {temp_value}")
                where_conditions.append(f"temperature IS NOT NULL")

            # Salinity threshold filter
            if parameter_context.salinity_range:
                operator, sal_value = parameter_context.salinity_range
                where_conditions.append(f"salinity {operator} {sal_value}")
                where_conditions.append(f"salinity IS NOT NULL")

            # Float ID filter
            if parameter_context.float_ids:
                float_list = "', '".join(parameter_context.float_ids)
                where_conditions.append(f"float_id IN ('{float_list}')")

            # Build final count query
            count_sql = "SELECT COUNT(*) FROM argo_measurements"
            if where_conditions:
                count_sql += " WHERE " + " AND ".join(where_conditions)

            return count_sql

        except Exception as e:
            print(f"Error building count query: {e}")
            return None

    def _apply_parameter_specific_filtering(self, db_results: List[Dict], parameter_context, user_query: str) -> List[Dict]:
        """Apply parameter-specific filtering to ensure data matches exact user criteria"""

        filtered_results = db_results.copy()

        try:
            # Apply temperature threshold filtering
            if parameter_context.temperature_range:
                operator, temp_value = parameter_context.temperature_range
                if operator == '>':
                    filtered_results = [r for r in filtered_results if r.get('temperature') is not None and r['temperature'] > temp_value]
                elif operator == '<':
                    filtered_results = [r for r in filtered_results if r.get('temperature') is not None and r['temperature'] < temp_value]
                elif operator == '>=':
                    filtered_results = [r for r in filtered_results if r.get('temperature') is not None and r['temperature'] >= temp_value]
                elif operator == '<=':
                    filtered_results = [r for r in filtered_results if r.get('temperature') is not None and r['temperature'] <= temp_value]

                print(f"Temperature filter ({operator} {temp_value}): {len(db_results)} -> {len(filtered_results)} results")

            # Apply salinity threshold filtering
            if parameter_context.salinity_range:
                operator, sal_value = parameter_context.salinity_range
                if operator == '>':
                    filtered_results = [r for r in filtered_results if r.get('salinity') is not None and r['salinity'] > sal_value]
                elif operator == '<':
                    filtered_results = [r for r in filtered_results if r.get('salinity') is not None and r['salinity'] < sal_value]
                elif operator == '>=':
                    filtered_results = [r for r in filtered_results if r.get('salinity') is not None and r['salinity'] >= sal_value]
                elif operator == '<=':
                    filtered_results = [r for r in filtered_results if r.get('salinity') is not None and r['salinity'] <= sal_value]

                print(f"Salinity filter ({operator} {sal_value}): {len(db_results)} -> {len(filtered_results)} results")

            # Apply depth filtering if not already handled by SQL
            if parameter_context.depth_range and parameter_context.depth_type == 'operator':
                operator, depth_value = parameter_context.depth_range
                if operator == '>=' or operator == '>':
                    filtered_results = [r for r in filtered_results if r.get('depth') is not None and r['depth'] >= depth_value]
                elif operator == '<=' or operator == '<':
                    filtered_results = [r for r in filtered_results if r.get('depth') is not None and r['depth'] <= depth_value]

                print(f"Depth filter ({operator} {depth_value}): {len(db_results)} -> {len(filtered_results)} results")

        except Exception as e:
            print(f"Parameter filtering failed: {e}, returning unfiltered results")
            return db_results

        return filtered_results

    def _intelligently_limit_data(self, db_results: List[Dict], user_query: str, query_classification: Dict) -> List[Dict]:
        """Intelligently limit data based on query context and scientific requirements"""

        if not db_results:
            return []

        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        query_lower = user_query.lower()
        data_size = len(db_results)

        # Scientific data analysis requires adequate sample sizes
        min_samples_for_analysis = {
            'statistical': max(30, int(data_size * 0.05)),    # 5% minimum, at least 30
            'trend': max(50, int(data_size * 0.10)),          # 10% minimum, at least 50
            'spatial': max(100, int(data_size * 0.15)),       # 15% minimum, at least 100
            'depth_profile': max(200, int(data_size * 0.20)), # 20% minimum, at least 200
            'comprehensive': max(500, int(data_size * 0.30))  # 30% minimum, at least 500
        }

        # Determine analysis type and required sample size
        if any(word in query_lower for word in ['sample', 'example', 'few', 'some']):
            limit = min(50, data_size)  # Still provide meaningful sample
        elif any(word in query_lower for word in ['depth', 'profile', 'vertical', 'layers']):
            limit = min(min_samples_for_analysis['depth_profile'], data_size)
        elif any(word in query_lower for word in ['trend', 'pattern', 'time series', 'temporal']):
            limit = min(min_samples_for_analysis['trend'], data_size)
        elif any(word in query_lower for word in ['spatial', 'geographic', 'region', 'area', 'distribution']):
            limit = min(min_samples_for_analysis['spatial'], data_size)
        elif any(word in query_lower for word in ['analysis', 'statistical', 'correlation', 'compare']):
            limit = min(min_samples_for_analysis['statistical'], data_size)
        elif query_classification.get("complexity_level") == "complex":
            limit = min(min_samples_for_analysis['comprehensive'], data_size)
        elif any(word in query_lower for word in ['knowledge base', 'all data', 'full data', 'entire data', 'complete data', 'everything']):
            limit = min(1000, data_size)  # Show substantial portion for comprehensive requests
        elif any(word in query_lower for word in ['various', 'different', 'range', 'multiple']):
            # For diversity-focused queries, ensure good coverage
            limit = min(min_samples_for_analysis['spatial'], data_size)
        else:
            # Default: balance performance with scientific validity
            limit = min(min_samples_for_analysis['statistical'], data_size)  
        
        # Smart sampling using scientific methods to maintain representativeness
        if len(db_results) <= limit:
            return db_results

        print(f"Scientific sampling: {data_size} -> {limit} ({limit/data_size*100:.1f}%) for query type analysis")

        # Use scientific sampling methods to ensure representativeness
        try:
            return self._scientific_stratified_sampling(db_results, limit, query_lower)
        except Exception as e:
            print(f"Scientific sampling failed: {e}, using fallback")
            return self._fallback_sampling(db_results, limit)

    def _scientific_stratified_sampling(self, db_results: List[Dict], limit: int, query_context: str) -> List[Dict]:
        """Use scientific sampling methods to ensure representative data"""
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import pandas as pd

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(db_results)

        # Create features for stratification
        features = []
        feature_names = []

        # Geographic stratification
        if 'latitude' in df.columns and 'longitude' in df.columns:
            features.extend([df['latitude'].fillna(0), df['longitude'].fillna(0)])
            feature_names.extend(['lat', 'lon'])

        # Depth stratification (critical for oceanographic data)
        if 'depth' in df.columns and df['depth'].notna().sum() > 0:
            features.append(df['depth'].fillna(df['depth'].mean()))
            feature_names.append('depth')

        # Temporal stratification
        if 'date' in df.columns:
            # Convert dates to numeric for clustering
            dates_numeric = pd.to_datetime(df['date'], errors='coerce').astype('int64') / 10**18
            features.append(dates_numeric.fillna(dates_numeric.mean()))
            feature_names.append('date')

        # Parameter value stratification (if specific parameter requested)
        if 'temperature' in query_context and 'temperature' in df.columns:
            features.append(df['temperature'].fillna(df['temperature'].mean()))
            feature_names.append('temp')

        if 'salinity' in query_context and 'salinity' in df.columns:
            features.append(df['salinity'].fillna(df['salinity'].mean()))
            feature_names.append('sal')

        if not features:
            # Fallback to random sampling if no features available
            return self._fallback_sampling(db_results, limit)

        # Create feature matrix
        X = np.column_stack(features)

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Determine optimal number of clusters (strata)
        n_clusters = min(max(5, limit // 20), 20, len(db_results) // 10)

        # Perform k-means clustering to create strata
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        # Stratified sampling within each cluster
        selected_indices = []
        samples_per_cluster = limit // n_clusters
        remaining_samples = limit % n_clusters

        for cluster_id in range(n_clusters):
            cluster_indices = np.where(clusters == cluster_id)[0]

            if len(cluster_indices) == 0:
                continue

            # Calculate samples for this cluster
            n_samples = samples_per_cluster
            if remaining_samples > 0:
                n_samples += 1
                remaining_samples -= 1

            n_samples = min(n_samples, len(cluster_indices))

            # Random sampling within cluster
            selected_cluster_indices = np.random.choice(
                cluster_indices, size=n_samples, replace=False
            )
            selected_indices.extend(selected_cluster_indices)

        # Ensure we have exactly the right number of samples
        if len(selected_indices) > limit:
            selected_indices = np.random.choice(selected_indices, size=limit, replace=False)

        return [db_results[i] for i in selected_indices]

    def _fallback_sampling(self, db_results: List[Dict], limit: int) -> List[Dict]:
        """Fallback sampling method"""
        import random

        # Systematic sampling with random start
        step = len(db_results) / limit
        start = random.randint(0, int(step))
        indices = [int(start + i * step) for i in range(limit)]
        indices = [min(i, len(db_results) - 1) for i in indices]  # Ensure within bounds

        return [db_results[i] for i in indices]

    def _old_stratified_sampling(self, db_results: List[Dict], limit: int) -> List[Dict]:
        """Legacy stratified sampling method"""
        try:
            # Sample across different dimensions to preserve patterns
            sorted_by_depth = sorted(db_results, key=lambda x: x.get('depth', 0))
            depth_step = max(1, len(sorted_by_depth) // (limit // 3))
            depth_sample = sorted_by_depth[::depth_step][:limit//3]
            
            # Sample by location diversity
            remaining = [r for r in db_results if r not in depth_sample]
            if remaining:
                remaining_by_lat = sorted(remaining, key=lambda x: (x.get('latitude', 0), x.get('longitude', 0)))
                location_step = max(1, len(remaining_by_lat) // (limit // 3))
                location_sample = remaining_by_lat[::location_step][:limit//3]
            else:
                location_sample = []
            
            # Fill remaining with most recent data
            used_ids = set(id(r) for r in depth_sample + location_sample)
            time_sample = [r for r in db_results if id(r) not in used_ids]
            time_sample = sorted(time_sample, key=lambda x: x.get('date', ''), reverse=True)[:limit - len(depth_sample) - len(location_sample)]
            
            final_sample = depth_sample + location_sample + time_sample
            print(f"Intelligently limited {len(db_results)} results to {len(final_sample)} using stratified sampling")
            return final_sample
            
        except Exception as e:
            print(f"Error in intelligent sampling: {e}, using simple limit")
            return db_results[:limit]

    def _get_sample_data(self, db: Session) -> List[Dict]:
        """Get a small sample of recent data to show system is working - only real data"""
        try:
            # Only get data with valid coordinates and measurements
            from sqlalchemy import and_, or_
            
            results = db.query(ArgoMeasurement).filter(
                ArgoMeasurement.latitude != 0,
                ArgoMeasurement.longitude != 0,
                ArgoMeasurement.latitude.isnot(None),
                ArgoMeasurement.longitude.isnot(None),
                # Ensure at least one measurement parameter is not zero/null
                or_(
                    and_(ArgoMeasurement.temperature.isnot(None), ArgoMeasurement.temperature != 0),
                    and_(ArgoMeasurement.salinity.isnot(None), ArgoMeasurement.salinity != 0),
                    and_(ArgoMeasurement.pressure.isnot(None), ArgoMeasurement.pressure != 0)
                )
            ).order_by(ArgoMeasurement.date.desc()).limit(20).all()
            
            # Filter out any remaining fake/invalid data
            valid_results = []
            for r in results:
                if (r.float_id and 
                    not r.float_id.startswith('float_') and 
                    not r.float_id.startswith('FLOAT_00000') and
                    r.latitude != 0 and r.longitude != 0):
                    valid_results.append({
                        "float_id": r.float_id,
                        "latitude": r.latitude,
                        "longitude": r.longitude,
                        "date": r.date.isoformat() if r.date else None,
                        "depth": r.depth,
                        "temperature": r.temperature,
                        "salinity": r.salinity,
                        "pressure": r.pressure
                    })
            
            return valid_results
        except Exception as e:
            print(f"Error getting sample data: {e}")
            return []

    def _has_meaningful_visualizations(self, viz_data: Dict) -> bool:
        """Check if visualization data contains meaningful content"""
        if not viz_data:
            return False
        
        # Check for custom charts (highest priority)
        if viz_data.get('is_custom_chart', False):
            print(f"Custom chart detected, considered meaningful")
            return True
            
        # Check for custom chart configuration
        if viz_data.get('custom_chart') is not None:
            print(f"Custom chart config found, considered meaningful")
            return True
            
        # Check map data
        map_points = viz_data.get('map', {}).get('points', [])
        if len(map_points) >= 10:
            return True
            
        # Check depth profile data  
        depth_data = viz_data.get('depth_profile', {}).get('data', [])
        if len(depth_data) >= 8:
            return True
            
        return False
    
    def _chart_optimized_data_retrieval(self, db: Session, user_query: str, chart_classification: Dict) -> List[Dict]:
        """Retrieve data optimized for chart generation based on chart type and parameters"""
        try:
            chart_type = chart_classification.get("chart_type", "line")
            
            # Build optimized query based on chart requirements - ensure only real data
            conditions = [
                "latitude IS NOT NULL", 
                "longitude IS NOT NULL", 
                "latitude != 0", 
                "longitude != 0"
            ]
            
            # Always ensure we have the required data for the chart
            if chart_type in ["scatter", "line"] and ("temperature" in user_query.lower() or "temp" in user_query.lower()):
                conditions.extend(["temperature IS NOT NULL", "temperature != 0"])
            if chart_type in ["scatter", "line"] and ("salinity" in user_query.lower() or "salt" in user_query.lower()):
                conditions.extend(["salinity IS NOT NULL", "salinity != 0"])
            if "depth" in user_query.lower():
                conditions.extend(["depth IS NOT NULL", "depth != 0"])
                
            # For temperature vs depth specifically
            if "temperature" in user_query.lower() and "depth" in user_query.lower():
                conditions.extend(["temperature IS NOT NULL", "depth IS NOT NULL", "depth > 0", "temperature != 0"])
                
            # Default conditions for chart data quality
            if len(conditions) == 4:  # Only the coordinate conditions
                conditions.append("(temperature IS NOT NULL AND temperature != 0) OR (salinity IS NOT NULL AND salinity != 0)")
            
            # Build the query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql_query = f"""
            SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure 
            FROM argo_measurements 
            WHERE {where_clause}
            ORDER BY date DESC, depth ASC
            LIMIT 500
            """
            
            print(f"Chart-optimized SQL: {sql_query}")
            results = self._execute_sql_query(db, sql_query)
            
            # Filter out fake data from results
            filtered_results = [
                r for r in results 
                if (r.get('float_id') and 
                    not r['float_id'].startswith('float_') and 
                    not r['float_id'].startswith('FLOAT_00000') and
                    r.get('latitude', 0) != 0 and r.get('longitude', 0) != 0)
            ]
            
            # If we don't get enough results, try a broader query
            if len(filtered_results) < 10:
                print(f"Chart query returned {len(filtered_results)} valid results, trying broader query")
                broader_sql = """
                SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure 
                FROM argo_measurements 
                WHERE (temperature IS NOT NULL AND temperature != 0) OR (salinity IS NOT NULL AND salinity != 0)
                AND latitude IS NOT NULL AND longitude IS NOT NULL 
                AND latitude != 0 AND longitude != 0
                ORDER BY date DESC
                LIMIT 200
                """
                broader_results = self._execute_sql_query(db, broader_sql)
                # Filter broader results too
                filtered_results = [
                    r for r in broader_results 
                    if (r.get('float_id') and 
                        not r['float_id'].startswith('float_') and 
                        not r['float_id'].startswith('FLOAT_00000') and
                        r.get('latitude', 0) != 0 and r.get('longitude', 0) != 0)
                ]
            
            return filtered_results
            
        except Exception as e:
            print(f"Chart-optimized data retrieval failed: {e}")
            # Fall back to basic query
            return self._fallback_data_retrieval(db, user_query)