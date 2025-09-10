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
    
    async def process_chat_query(self, user_query: str, db: Session) -> Dict:
        """Process a natural language query using enhanced RAG pipeline"""
        
        # Step 1: Classify the query
        query_classification = self.query_classifier.classify_query(user_query)
        print(f"Query Classification: {query_classification}")
        
        # Step 2: Retrieve relevant context from ChromaDB
        context_results = self.vector_store.search(user_query, n_results=15)
        
        # Check if context is actually relevant to avoid noise
        if context_results.get('documents') and context_results['documents'][0]:
            # Filter out very short or irrelevant context
            documents = context_results['documents'][0]
            filtered_docs = [doc for doc in documents if len(doc.strip()) > 30]
            context_results['documents'] = [filtered_docs] if filtered_docs else [[]]
        
        # Step 3: Get data if needed
        db_results = []
        sql_used = None
        
        if query_classification["needs_data"]:
            # Generate and execute SQL query
            sql_query = await self.sql_generator.generate_sql(
                user_query, query_classification, context_results
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
        
        # Step 4: Generate AI response using RAG
        ai_response = await self.rag_engine.generate_response(
            user_query, context_results, db_results, query_classification
        )
        
        # Step 5: Build visualization data
        viz_data = self.visualization_builder.build_visualization(db_results, query_classification)
        
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