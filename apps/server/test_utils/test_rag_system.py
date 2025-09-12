#!/usr/bin/env python3
"""
Test script for the enhanced RAG system
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.database import get_db
from rag_pipeline.vector_store import VectorStore
from chat_bot.chatbot_service import ChatbotService

load_dotenv()


async def test_rag_system():
    """Test the complete RAG system with sample queries"""
    
    print("=== RAG System Test ===")
    
    # Initialize components
    try:
        vector_store = VectorStore()
        chatbot_service = ChatbotService(vector_store)
        print("RAG system components initialized")
    except Exception as e:
        print(f"Failed to initialize RAG system: {e}")
        return False
    
    # Test database connection
    try:
        db_gen = get_db()
        db = next(db_gen)
        print("Database connection established")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    
    # Test queries
    test_queries = [
        "Show me temperature profiles near Mumbai in March 2023",
        "What is the average temperature in the Arabian Sea?",
        "Find measurements with depth greater than 100 meters",
        "Analyze salinity patterns in the Indian Ocean",
        "What are ARGO floats and how do they work?"
    ]
    
    print(f"\n=== Testing {len(test_queries)} Sample Queries ===")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        try:
            result = await chatbot_service.process_chat_query(query, db)
            
            # Check result structure
            required_keys = ["response", "data", "visualization", "query_params", "context_count"]
            missing_keys = [key for key in required_keys if key not in result]
            
            if missing_keys:
                print(f"Missing keys in response: {missing_keys}")
            else:
                print(f"  + Response structure valid")
                print(f"  - Data points: {len(result['data'])}")
                print(f"  - Context retrieved: {result['context_count']}")
                print(f"  - Classification: {result['query_params']['classification']['complexity_level']}")
                print(f"  - SQL used: {'Yes' if result['query_params']['sql_used'] else 'No'}")
                print(f"  - Visualizations: {result['visualization'].get('available_visualizations', [])}")
                
                # Show first part of response
                response_preview = result['response'][:150] + "..." if len(result['response']) > 150 else result['response']
                print(f"  - Response preview: {response_preview}")
                
        except Exception as e:
            print(f"Query failed: {e}")
    
    print("\n=== RAG System Test Complete ===")
    
    # Close database connection
    try:
        db.close()
    except:
        pass
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_rag_system())
    
    if success:
        print("\n+ RAG system test completed successfully!")
        sys.exit(0)
    else:
        print("\nRAG system test failed")
        sys.exit(1)