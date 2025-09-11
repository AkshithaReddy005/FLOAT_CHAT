"""
Enhanced Chatbot Service with Modular RAG Implementation
Uses separated modules for query classification, SQL generation, visualization, and RAG responses.
"""

import os
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from database import ArgoMeasurement
from vector_store import VectorStore
from query_classifier import QueryClassifier
from sql_generator import SQLGenerator
from visualization_builder import VisualizationBuilder
from rag_engine import RAGEngine

load_dotenv()


class ChatbotService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        
        # Initialize modular components
        self.query_classifier = QueryClassifier()
        self.sql_generator = SQLGenerator()
        self.visualization_builder = VisualizationBuilder()
        self.rag_engine = RAGEngine()
        
        print("Enhanced Chatbot Service initialized with modular RAG components")
    
    async def process_chat_query(self, user_query: str, db: Session, session_context: dict = None) -> Dict:
        """Process a natural language query using enhanced RAG pipeline"""
        
        try:
            # Step 1: Classify the query
            query_classification = self.query_classifier.classify_query(user_query)
            print(f"Query Classification: {query_classification}")
        except Exception as e:
            print(f"Query classification failed: {e}")
            # Use default classification
            query_classification = {
                "needs_data": True,
                "is_analytical": False,
                "has_temporal": False,
                "has_spatial": False,
                "complexity_level": "simple"
            }
        
        try:
            # Step 2: Retrieve relevant context from ChromaDB
            context_results = self.vector_store.search(user_query, n_results=15)
            
            # Check if context is actually relevant to avoid noise
            if context_results.get('documents') and context_results['documents'][0]:
                # Filter out very short or irrelevant context
                documents = context_results['documents'][0]
                filtered_docs = [doc for doc in documents if len(doc.strip()) > 30]
                context_results['documents'] = [filtered_docs] if filtered_docs else [[]]
        except Exception as e:
            print(f"Context retrieval failed: {e}")
            # Use empty context
            context_results = {'documents': [[]], 'distances': [[]]}
        
        # Step 3: Get data if needed
        db_results = []
        sql_used = None
        
        if query_classification["needs_data"]:
            try:
                # Generate and execute SQL query with session context
                sql_query = await self.sql_generator.generate_sql(
                    user_query, query_classification, context_results, session_context
                )
                
                if sql_query and self.sql_generator.validate_sql(sql_query):
                    print(f"Executing validated SQL: {sql_query}")
                    db_results = self._execute_sql_query(db, sql_query)
                    sql_used = sql_query
                    print(f"SQL returned {len(db_results)} results")
                else:
                    if sql_query:
                        print(f"SQL validation failed for: {sql_query}")
                    else:
                        print("SQL generation failed")
                    print("Using fallback data retrieval")
                    db_results = self._fallback_data_retrieval(db, user_query)
            except Exception as e:
                print(f"Data retrieval failed: {e}")
                print("Using emergency fallback data retrieval")
                db_results = self._fallback_data_retrieval(db, user_query)
        
        try:
            # Step 4: Generate AI response using RAG with session context
            ai_response = await self.rag_engine.generate_response(
                user_query, context_results, db_results, query_classification, session_context
            )
        except Exception as e:
            print(f"AI response generation failed: {e}")
            # Use built-in fallback response
            ai_response = self._generate_emergency_response(user_query, db_results, query_classification)
        
        try:
            # Step 5: Build visualization data
            viz_data = self.visualization_builder.build_visualization(db_results, query_classification)
        except Exception as e:
            print(f"Visualization building failed: {e}")
            # Use default visualization structure
            viz_data = {"map": {"points": []}, "depth_profile": {"data": []}}
        
        # Step 6: Prepare response
        return {
            "response": ai_response,
            "data": db_results[:500],  # Limit for frontend performance
            "visualization": viz_data,
            "query_params": {
                "classification": query_classification,
                "sql_used": sql_used,
                "context_retrieved": len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0,
                "data_points": len(db_results)
            },
            "context_count": len(context_results.get('documents', [[]])[0]) if context_results.get('documents') else 0
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
        """Smart fallback method for data retrieval when SQL generation fails"""
        try:
            query_lower = user_query.lower()
            base_query = db.query(ArgoMeasurement)
            
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
            ]
        except Exception as e:
            print(f"Error in fallback data retrieval: {e}")
            # Final fallback - just get some recent data
            try:
                results = db.query(ArgoMeasurement).order_by(ArgoMeasurement.date.desc()).limit(50).all()
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
                ]
            except:
                return []

    def _generate_emergency_response(self, user_query: str, db_results: List[Dict], 
                                   query_classification: Dict) -> str:
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

    def _get_sample_data(self, db: Session) -> List[Dict]:
        """Get a small sample of recent data to show system is working"""
        try:
            results = db.query(ArgoMeasurement).order_by(ArgoMeasurement.date.desc()).limit(20).all()
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
            ]
        except Exception as e:
            print(f"Error getting sample data: {e}")
            return []