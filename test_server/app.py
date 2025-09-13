#!/usr/bin/env python3
"""
Standalone Test Server for Unified Parameter Flow
Runs on port 8001 (separate from main backend on 8000)
"""

from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import sys
import os
import traceback
import json
from datetime import datetime
import time
import threading
from queue import Queue

# Add the main server source to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'server', 'src'))

try:
    from rag_pipeline.unified_query_parser import UnifiedQueryParser
    from rag_pipeline.parameter_context import ParameterContext
    from rag_pipeline.consistency_validator import ConsistencyValidator
    from rag_pipeline.parameter_logger import parameter_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure the main server modules are available")

app = Flask(__name__)
CORS(app)

# Initialize test components
parser = UnifiedQueryParser()
validator = ConsistencyValidator()

# Global state for real-time testing
active_tests = {}
test_results_queue = Queue()

# Comprehensive test cases covering all edge cases
TEST_CASES = {
    "location_tests": [
        # Simple location queries
        "Temperature data from Mumbai",
        "Show me salinity near Mumbai",
        "Data from Arabian Sea",
        "Measurements around Indian Ocean",
        
        # Coordinate-based queries
        "Data between 18-20°N and 72-74°E",
        "Show measurements at 19.5°N, 73.2°E",
        "Temperature from coordinates 15-25°N, 65-75°E",
        
        # Regional comparisons
        "Compare Mumbai vs Arabian Sea temperature",
        "Coastal vs offshore salinity differences",
        "Northern vs Southern Arabian Sea data",
        
        # Edge cases
        "Data from nonexistent location XYZ",
        "Measurements at 0°N, 0°E",  # Null island
        "Show me data from everywhere",  # No location specified
    ],
    
    "temporal_tests": [
        # Simple temporal queries
        "Data from 2023",
        "Show me recent measurements",
        "Temperature data from March 2023",
        "Salinity in winter 2022",
        
        # Year comparisons
        "Compare 2020 vs 2010 temperature",
        "Temperature difference between 2015 and 2023",
        "Salinity comparison 2018 and 2022",
        
        # Date ranges
        "Data from 2020 to 2023",
        "Measurements between 2015-2020",
        "Show me data from 2010-2025",
        
        # Edge cases
        "Data from year 1900",  # Very old date
        "Show me future data from 2030",  # Future date
        "Compare 2023 vs 2023",  # Same year comparison
        "Data from yesterday",  # Relative date
    ],
    
    "depth_tests": [
        # Simple depth queries
        "Surface temperature data",
        "Deep ocean measurements",
        "Data below 1000m",
        "Measurements above 500m",
        
        # Specific depth ranges
        "Temperature at 100m depth",
        "Data between 50-200m",
        "Thermocline layer measurements",
        "Abyssal zone data",
        
        # Depth comparisons
        "Surface vs deep temperature",
        "Shallow vs deep salinity",
        "Temperature profile with depth",
        
        # Edge cases
        "Data below 10000m",  # Very deep
        "Measurements at exactly 0m",  # Surface
        "Data deeper than ocean floor",  # Impossible depth
        "Negative depth measurements",  # Invalid depth
    ],
    
    "parameter_tests": [
        # Single parameter queries
        "Temperature measurements",
        "Salinity data only",
        "Pressure readings",
        "Density calculations",
        
        # Multi-parameter queries
        "Temperature and salinity data",
        "All oceanographic parameters",
        "Temperature, salinity, and pressure",
        
        # Parameter relationships
        "Temperature vs salinity correlation",
        "Pressure-temperature relationship",
        "Density vs depth analysis",
        
        # Edge cases
        "Show me pH data",  # Parameter not available
        "All parameters except temperature",
        "Missing parameter values",
    ],
    
    "analytical_tests": [
        # Statistical queries
        "Average temperature in Mumbai",
        "Maximum salinity in Arabian Sea",
        "Minimum depth measurements",
        "Standard deviation of temperature",
        
        # Trend analysis
        "Temperature trends over time",
        "Seasonal salinity variations",
        "Long-term ocean warming",
        "Climate change indicators",
        
        # Complex analytics
        "Correlation between temperature and depth",
        "Water mass identification",
        "Thermocline depth analysis",
        "Ocean stratification patterns",
        
        # Edge cases
        "Calculate impossible statistics",
        "Trend analysis with no data",
        "Correlation with single data point",
    ],
    
    "comparative_tests": [
        # Area comparisons
        "Mumbai vs Arabian Sea temperature",
        "Coastal vs offshore differences",
        "Northern vs Southern regions",
        "East vs West ocean basins",
        
        # Temporal comparisons
        "2020 vs 2010 ocean conditions",
        "Summer vs winter temperatures",
        "Pre vs post monsoon salinity",
        "Decade-over-decade changes",
        
        # Depth comparisons
        "Surface vs deep ocean",
        "Thermocline vs mixed layer",
        "Shallow vs abyssal waters",
        
        # Edge cases
        "Compare identical regions",
        "Compare non-overlapping time periods",
        "Compare with no data available",
    ],
    
    "complex_queries": [
        # Multi-constraint queries
        "Temperature below 1000m in Mumbai during 2023",
        "Salinity data from Arabian Sea in winter between 50-200m",
        "Deep ocean temperature trends in Southern Indian Ocean",
        "Surface warming patterns near Mumbai from 2015-2023",
        
        # Analytical combinations
        "Average temperature difference between surface and 1000m in Mumbai",
        "Seasonal thermocline depth variations in Arabian Sea",
        "Long-term salinity trends in deep waters near Mumbai",
        "Temperature-salinity relationships in different water masses",
        
        # Chart/visualization requests
        "Plot temperature vs depth profile for Mumbai",
        "Create map of temperature distribution in Arabian Sea",
        "Show time series of salinity changes",
        "Generate scatter plot of temperature vs salinity",
        
        # Edge cases
        "Show me everything about everything everywhere",
        "Complex query with contradictory constraints",
        "Multi-parameter analysis with insufficient data",
    ],
    
    "session_context_tests": [
        # Relative queries (require session context)
        "What about below 500m?",
        "Show me the same area but deeper",
        "How about in winter?",
        "What's the temperature there?",
        
        # Follow-up queries
        "And what about salinity?",
        "Compare that with last year",
        "Show me more recent data",
        "What about other parameters?",
        
        # Context switching
        "Now show me Arabian Sea data",
        "Switch to pressure measurements",
        "Change to 2022 data",
        "Focus on surface waters",
    ],
    
    "edge_cases": [
        # Empty/minimal queries
        "",
        "data",
        "show me",
        "temperature",
        
        # Ambiguous queries
        "some ocean data please",
        "interesting measurements",
        "good temperature readings",
        "nice salinity values",
        
        # Contradictory queries
        "Surface data below 1000m",
        "Future historical data",
        "Dry ocean measurements",
        "Hot ice temperature",
        
        # Very long queries
        "I need comprehensive temperature and salinity measurements from the Mumbai coastal region specifically between 18-20 degrees north latitude and 72-74 degrees east longitude during the year 2023 particularly focusing on the thermocline layer between 50-200 meters depth with special attention to seasonal variations and comparison with historical data from previous decades",
        
        # Special characters
        "Temperature data from Mumbai!@#$%",
        "Salinity measurements with émojis 🌊🌡️",
        "Data from location with numbers 123456",
        
        # Multiple languages (if applicable)
        "Mumbai ka temperature data",
        "Arabian Sea mein salinity",
    ]
}

@app.route('/')
def index():
    """Main test interface"""
    return render_template('test_interface.html')

@app.route('/api/test-categories')
def get_test_categories():
    """Get all test categories and their queries"""
    return jsonify({
        "categories": list(TEST_CASES.keys()),
        "test_cases": TEST_CASES,
        "total_tests": sum(len(queries) for queries in TEST_CASES.values())
    })

@app.route('/api/test-single', methods=['POST'])
def test_single_query():
    """Test a single query and return detailed results"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        session_context = data.get('session_context', None)
        
        # Track detailed pipeline execution
        pipeline_flow = {
            "steps": [],
            "total_time": 0,
            "parameter_extraction": {},
            "sql_generation": {},
            "chromadb_search": {},
            "consistency_validation": {},
            "api_simulation": {}
        }
        
        # Step 1: Parameter Extraction
        step_start = datetime.now()
        parameter_context = parser.parse_query(query, session_context)
        step_time = (datetime.now() - step_start).total_seconds()
        
        pipeline_flow["parameter_extraction"] = {
            "duration": f"{step_time:.4f}s",
            "input_query": query,
            "extracted_parameters": {
                "location_name": parameter_context.location_name,
                "location_bounds": parameter_context.location_bounds,
                "date_range": [d.isoformat() for d in parameter_context.date_range] if parameter_context.date_range else None,
                "date_years": parameter_context.date_years,
                "depth_range": parameter_context.depth_range,
                "depth_type": parameter_context.depth_type,
                "parameters": parameter_context.parameters,
                "complexity_level": parameter_context.complexity_level,
                "confidence_score": parameter_context.confidence_score
            },
            "summary": parameter_context.get_summary()
        }
        pipeline_flow["steps"].append({
            "step": "Parameter Extraction",
            "duration": f"{step_time:.4f}s",
            "status": "success",
            "details": f"Extracted {len([p for p in [parameter_context.location_name, parameter_context.parameters, parameter_context.date_years] if p])} parameter types"
        })
        
        # Step 2: SQL Generation
        step_start = datetime.now()
        sql_filters = parameter_context.to_sql_filters()
        mock_sql_query = generate_mock_sql_query(parameter_context)
        mock_sql_results = generate_mock_sql_data(parameter_context)
        step_time = (datetime.now() - step_start).total_seconds()
        
        pipeline_flow["sql_generation"] = {
            "duration": f"{step_time:.4f}s",
            "generated_filters": sql_filters,
            "mock_query": mock_sql_query,
            "result_count": len(mock_sql_results),
            "sample_results": mock_sql_results[:3] if mock_sql_results else []
        }
        pipeline_flow["steps"].append({
            "step": "SQL Generation & Execution",
            "duration": f"{step_time:.4f}s",
            "status": "success",
            "details": f"Generated SQL query, returned {len(mock_sql_results)} records"
        })
        
        # Step 3: ChromaDB Search
        step_start = datetime.now()
        chroma_filters = parameter_context.to_chroma_filters()
        mock_chroma_results = generate_mock_chroma_data(parameter_context)
        step_time = (datetime.now() - step_start).total_seconds()
        
        pipeline_flow["chromadb_search"] = {
            "duration": f"{step_time:.4f}s",
            "search_filters": chroma_filters,
            "result_count": len(mock_chroma_results.get('documents', [[]])[0]),
            "sample_documents": mock_chroma_results.get('documents', [[]])[0][:2],
            "sample_metadata": mock_chroma_results.get('metadatas', [[]])[0][:2],
            "distances": mock_chroma_results.get('distances', [[]])[0][:2]
        }
        pipeline_flow["steps"].append({
            "step": "ChromaDB Vector Search",
            "duration": f"{step_time:.4f}s",
            "status": "success",
            "details": f"Vector search returned {len(mock_chroma_results.get('documents', [[]])[0])} documents"
        })
        
        # Step 4: API Response Simulation
        step_start = datetime.now()
        mock_api_response = generate_mock_api_response(parameter_context, mock_sql_results, mock_chroma_results, pipeline_flow)
        step_time = (datetime.now() - step_start).total_seconds()
        
        pipeline_flow["api_simulation"] = {
            "duration": f"{step_time:.4f}s",
            "response_type": mock_api_response.get("type", "data"),
            "data_points": mock_api_response.get("data_count", 0),
            "visualization_type": mock_api_response.get("visualization", "none"),
            "ai_summary": mock_api_response.get("summary", "")
        }
        pipeline_flow["steps"].append({
            "step": "API Response Generation",
            "duration": f"{step_time:.4f}s",
            "status": "success",
            "details": f"Generated {mock_api_response.get('type', 'data')} response with {mock_api_response.get('data_count', 0)} data points"
        })
        
        # Step 5: Consistency Validation
        validation_start = datetime.now()
        validation_report = validator.validate_service_consistency(
            parameter_context, mock_sql_results, mock_chroma_results, ""
        )
        validation_time = (datetime.now() - validation_start).total_seconds()
        
        pipeline_flow["consistency_validation"] = {
            "duration": f"{validation_time:.4f}s",
            "is_consistent": validation_report["is_consistent"],
            "violations_found": len(validation_report["violations"]),
            "warnings_found": len(validation_report.get("warnings", [])),
            "validation_details": validation_report
        }
        pipeline_flow["steps"].append({
            "step": "Consistency Validation",
            "duration": f"{validation_time:.4f}s",
            "status": "success" if validation_report["is_consistent"] else "warning",
            "details": f"Found {len(validation_report['violations'])} violations, {len(validation_report.get('warnings', []))} warnings"
        })
        
        # Calculate total pipeline time
        pipeline_flow["total_time"] = sum(float(step["duration"].replace("s", "")) for step in pipeline_flow["steps"])
        
        # Check if request should fail
        should_fail, failure_reason = validator.should_fail_request(validation_report)
        
        return jsonify({
            "query": query,
            "parameter_context": {
                "query_id": parameter_context.query_id,
                "summary": parameter_context.get_summary(),
                "location_name": parameter_context.location_name,
                "location_bounds": parameter_context.location_bounds,
                "date_range": [d.isoformat() for d in parameter_context.date_range] if parameter_context.date_range else None,
                "date_years": parameter_context.date_years,
                "depth_range": parameter_context.depth_range,
                "depth_type": parameter_context.depth_type,
                "parameters": parameter_context.parameters,
                "is_analytical": parameter_context.is_analytical,
                "is_comparative": parameter_context.is_comparative,
                "is_chart_request": parameter_context.is_chart_request,
                "complexity_level": parameter_context.complexity_level,
                "confidence_score": parameter_context.confidence_score
            },
            "sql_filters": parameter_context.to_sql_filters(),
            "chroma_filters": parameter_context.to_chroma_filters(),
            "validation_report": validation_report,
            "should_fail": should_fail,
            "failure_reason": failure_reason,
            "pipeline_flow": pipeline_flow,
            "timing": {
                "total_pipeline_time": f"{pipeline_flow['total_time']:.4f}s",
                "parameter_extraction": pipeline_flow["parameter_extraction"]["duration"],
                "sql_generation": pipeline_flow["sql_generation"]["duration"],
                "chromadb_search": pipeline_flow["chromadb_search"]["duration"],
                "api_simulation": pipeline_flow["api_simulation"]["duration"],
                "consistency_validation": pipeline_flow["consistency_validation"]["duration"]
            },
            "mock_data": {
                "sql_results_count": len(mock_sql_results),
                "chroma_results_count": len(mock_chroma_results.get('documents', [[]])[0])
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/test-batch', methods=['POST'])
def test_batch_queries():
    """Test multiple queries in batch"""
    try:
        data = request.get_json()
        queries = data.get('queries', [])
        category = data.get('category', 'unknown')
        
        results = []
        for i, query in enumerate(queries):
            try:
                parameter_context = parser.parse_query(query)
                mock_sql_results = generate_mock_sql_data(parameter_context)
                mock_chroma_results = generate_mock_chroma_data(parameter_context)
                
                validation_report = validator.validate_service_consistency(
                    parameter_context, mock_sql_results, mock_chroma_results, ""
                )
                
                should_fail, failure_reason = validator.should_fail_request(validation_report)
                
                results.append({
                    "index": i,
                    "query": query,
                    "success": True,
                    "summary": parameter_context.get_summary(),
                    "complexity": parameter_context.complexity_level,
                    "confidence": parameter_context.confidence_score,
                    "consistent": validation_report["is_consistent"],
                    "violations": len(validation_report["violations"]),
                    "should_fail": should_fail
                })
                
            except Exception as e:
                results.append({
                    "index": i,
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        return jsonify({
            "category": category,
            "total_queries": len(queries),
            "results": results,
            "summary": {
                "successful": len([r for r in results if r.get("success", False)]),
                "failed": len([r for r in results if not r.get("success", False)]),
                "consistent": len([r for r in results if r.get("consistent", False)]),
                "should_fail": len([r for r in results if r.get("should_fail", False)])
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/test-batch-stream', methods=['POST'])
def test_batch_queries_stream():
    """Test multiple queries with real-time streaming results"""
    try:
        data = request.get_json()
        queries = data.get('queries', [])
        category = data.get('category', 'unknown')
        test_id = f"{category}_{int(time.time())}"
        
        # Start background test execution
        thread = threading.Thread(
            target=execute_batch_test_async,
            args=(test_id, queries, category)
        )
        thread.start()
        
        return jsonify({
            "test_id": test_id,
            "status": "started",
            "total_queries": len(queries)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/api/test-progress/<test_id>')
def get_test_progress(test_id):
    """Get real-time progress of a running test"""
    if test_id not in active_tests:
        return jsonify({"error": "Test not found"}), 404
    
    test_info = active_tests[test_id]
    return jsonify({
        "test_id": test_id,
        "status": test_info["status"],
        "progress": test_info["progress"],
        "total_queries": test_info["total_queries"],
        "completed": test_info["completed"],
        "current_query": test_info.get("current_query", ""),
        "results": test_info.get("results", []),
        "summary": test_info.get("summary", {})
    })

@app.route('/api/test-stream/<test_id>')
def stream_test_results(test_id):
    """Server-sent events stream for real-time test results"""
    def generate():
        if test_id not in active_tests:
            yield f"data: {{\"error\": \"Test not found\"}}\n\n"
            return
            
        while True:
            test_info = active_tests.get(test_id)
            if not test_info:
                break
                
            # Send current progress
            progress_data = {
                "type": "progress",
                "test_id": test_id,
                "status": test_info["status"],
                "progress": test_info["progress"],
                "completed": test_info["completed"],
                "total_queries": test_info["total_queries"],
                "current_query": test_info.get("current_query", "")
            }
            
            yield f"data: {json.dumps(progress_data)}\n\n"
            
            # Send new results if available
            if "new_results" in test_info and test_info["new_results"]:
                for result in test_info["new_results"]:
                    result_data = {
                        "type": "result",
                        "test_id": test_id,
                        "result": result
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"
                test_info["new_results"] = []
            
            # Check if test is complete
            if test_info["status"] == "completed":
                final_data = {
                    "type": "complete",
                    "test_id": test_id,
                    "summary": test_info["summary"]
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                break
                
            time.sleep(0.5)  # Update every 500ms
    
    return Response(generate(), mimetype='text/event-stream')

def execute_batch_test_async(test_id, queries, category):
    """Execute batch test asynchronously with progress tracking"""
    active_tests[test_id] = {
        "status": "running",
        "progress": 0,
        "total_queries": len(queries),
        "completed": 0,
        "results": [],
        "new_results": [],
        "summary": {}
    }
    
    results = []
    
    try:
        for i, query in enumerate(queries):
            # Update current query
            active_tests[test_id]["current_query"] = query
            
            try:
                start_time = time.time()
                
                # Quick pipeline execution for batch mode
                parameter_context = parser.parse_query(query)
                sql_filters = parameter_context.to_sql_filters()
                chroma_filters = parameter_context.to_chroma_filters()
                mock_sql_results = generate_mock_sql_data(parameter_context)
                mock_chroma_results = generate_mock_chroma_data(parameter_context)
                
                validation_report = validator.validate_service_consistency(
                    parameter_context, mock_sql_results, mock_chroma_results, ""
                )
                
                should_fail, failure_reason = validator.should_fail_request(validation_report)
                execution_time = time.time() - start_time
                
                # Create mini pipeline summary for batch results
                pipeline_summary = {
                    "sql_query_generated": bool(sql_filters),
                    "sql_records_returned": len(mock_sql_results),
                    "chromadb_filters_applied": bool(chroma_filters),
                    "chromadb_documents_found": len(mock_chroma_results.get('documents', [[]])[0]),
                    "consistency_check_passed": validation_report["is_consistent"]
                }
                
                result = {
                    "index": i,
                    "query": query,
                    "success": True,
                    "summary": parameter_context.get_summary(),
                    "complexity": parameter_context.complexity_level,
                    "confidence": parameter_context.confidence_score,
                    "consistent": validation_report["is_consistent"],
                    "violations": len(validation_report["violations"]),
                    "should_fail": should_fail,
                    "execution_time": f"{execution_time:.3f}s",
                    "timestamp": datetime.now().isoformat(),
                    "pipeline_summary": pipeline_summary
                }
                
            except Exception as e:
                result = {
                    "index": i,
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            
            results.append(result)
            active_tests[test_id]["results"].append(result)
            active_tests[test_id]["new_results"].append(result)
            
            # Update progress
            active_tests[test_id]["completed"] = i + 1
            active_tests[test_id]["progress"] = int(((i + 1) / len(queries)) * 100)
            
            # Small delay to make progress visible
            time.sleep(0.1)
        
        # Calculate final summary
        summary = {
            "successful": len([r for r in results if r.get("success", False)]),
            "failed": len([r for r in results if not r.get("success", False)]),
            "consistent": len([r for r in results if r.get("consistent", False)]),
            "should_fail": len([r for r in results if r.get("should_fail", False)]),
            "avg_execution_time": sum([float(r.get("execution_time", "0s").replace("s", "")) for r in results if r.get("success")]) / max(1, len([r for r in results if r.get("success")]))
        }
        
        active_tests[test_id]["summary"] = summary
        active_tests[test_id]["status"] = "completed"
        
    except Exception as e:
        active_tests[test_id]["status"] = "error"
        active_tests[test_id]["error"] = str(e)
    
    # Clean up after 5 minutes
    def cleanup():
        time.sleep(300)  # 5 minutes
        if test_id in active_tests:
            del active_tests[test_id]
    
    threading.Thread(target=cleanup).start()

def generate_mock_sql_data(parameter_context):
    """Generate mock SQL data based on parameter context"""
    mock_data = []
    
    # Generate data that should match the parameters
    if parameter_context.location_bounds:
        bounds = parameter_context.location_bounds
        lat = (bounds['lat_min'] + bounds['lat_max']) / 2
        lon = (bounds['lon_min'] + bounds['lon_max']) / 2
    else:
        lat, lon = 19.0, 73.0  # Default Mumbai
    
    if parameter_context.date_range:
        date_str = parameter_context.date_range[0].isoformat()
    elif parameter_context.date_years:
        date_str = f"{parameter_context.date_years[0]}-06-15T12:00:00Z"
    else:
        date_str = "2023-06-15T12:00:00Z"
    
    if parameter_context.depth_range:
        if parameter_context.depth_type == 'operator':
            depth = parameter_context.depth_range[1] + 50  # Slightly beyond the constraint
        else:
            depth = (parameter_context.depth_range[0] + parameter_context.depth_range[1]) / 2
    else:
        depth = 100.0
    
    # Generate 5-10 mock records
    for i in range(5, 11):
        mock_data.append({
            'latitude': lat + (i * 0.1),
            'longitude': lon + (i * 0.1),
            'date': date_str,
            'depth': depth + (i * 10),
            'temperature': 25.0 + (i * 0.5),
            'salinity': 35.0 + (i * 0.1),
            'pressure': depth * 10 + i,
            'float_id': f'FLOAT_{i:04d}'
        })
    
    # Add some inconsistent data for testing (10% of records)
    if len(mock_data) > 0:
        # Make one record inconsistent
        mock_data[0]['latitude'] = 50.0  # Way outside bounds
        mock_data[0]['date'] = "2000-01-01T00:00:00Z"  # Wrong year
    
    return mock_data

def generate_mock_chroma_data(parameter_context):
    """Generate mock ChromaDB data"""
    return {
        'documents': [["Mock oceanographic context document 1", "Mock context document 2"]],
        'metadatas': [[
            {'latitude': 19.0, 'longitude': 73.0, 'depth': 100, 'year': 2023},
            {'latitude': 19.1, 'longitude': 73.1, 'depth': 150, 'year': 2023}
        ]],
        'distances': [[0.1, 0.2]],
        'ids': [['doc1', 'doc2']]
    }

def generate_mock_sql_query(parameter_context):
    """Generate a mock SQL query based on parameter context"""
    base_query = "SELECT latitude, longitude, date, depth, temperature, salinity, pressure, float_id FROM argo_measurements"
    conditions = []
    
    if parameter_context.location_bounds:
        bounds = parameter_context.location_bounds
        conditions.append(f"latitude BETWEEN {bounds['lat_min']} AND {bounds['lat_max']}")
        conditions.append(f"longitude BETWEEN {bounds['lon_min']} AND {bounds['lon_max']}")
    
    if parameter_context.date_years:
        years = parameter_context.date_years
        if len(years) == 1:
            conditions.append(f"EXTRACT(year FROM date) = {years[0]}")
        else:
            conditions.append(f"EXTRACT(year FROM date) IN ({', '.join(map(str, years))})")
    
    if parameter_context.depth_range:
        if parameter_context.depth_type == 'operator':
            op = '>=' if parameter_context.depth_range[0] > 0 else '<='
            conditions.append(f"depth {op} {parameter_context.depth_range[1]}")
        else:
            conditions.append(f"depth BETWEEN {parameter_context.depth_range[0]} AND {parameter_context.depth_range[1]}")
    
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    base_query += " ORDER BY date DESC LIMIT 100"
    return base_query

def generate_mock_api_response(parameter_context, sql_results, chroma_results, pipeline_flow=None):
    """Generate mock API response based on the pipeline results"""
    response = {
        "type": "data_analysis",
        "data_count": len(sql_results),
        "visualization": "none",
        "summary": ""
    }
    
    # Determine response type based on query characteristics
    if parameter_context.is_chart_request:
        # Use the query from parameter extraction step
        query_text = pipeline_flow.get("parameter_extraction", {}).get("input_query", "").lower()
        if "map" in query_text:
            response["visualization"] = "geographic_map"
        elif "plot" in query_text or "profile" in query_text:
            response["visualization"] = "line_chart"
        else:
            response["visualization"] = "scatter_plot"
        response["type"] = "visualization"
    
    if parameter_context.is_analytical:
        response["type"] = "statistical_analysis"
        response["summary"] = f"Statistical analysis of {parameter_context.parameters or 'oceanographic data'} showing trends and patterns."
    
    if parameter_context.is_comparative:
        response["type"] = "comparative_analysis"
        response["summary"] = f"Comparative analysis between different {parameter_context.location_name or 'regions'} and time periods."
    
    # Add context from ChromaDB
    context_docs = len(chroma_results.get('documents', [[]])[0])
    if context_docs > 0:
        response["context_documents"] = context_docs
        response["summary"] += f" Enhanced with {context_docs} relevant context documents."
    
    if not response["summary"]:
        response["summary"] = f"Retrieved {len(sql_results)} data points for {parameter_context.get_summary()}"
    
    return response

if __name__ == '__main__':
    print("🧪 Starting Unified Parameter Flow Test Server")
    print("📍 Running on http://localhost:8001")
    print("🔄 Separate from main backend (port 8000)")
    print("🔍 Enhanced with detailed pipeline flow visualization")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=8001, debug=True)
