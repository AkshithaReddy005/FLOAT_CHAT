"""
Test script for sophisticated SQL query generation
Tests edge cases and complex query patterns
"""

import asyncio
import sys
import os

# Add the src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sql_generator import SQLGenerator
from query_classifier import QueryClassifier

async def test_sophisticated_queries():
    """Test various sophisticated query patterns"""
    
    # Initialize components
    sql_generator = SQLGenerator()
    query_classifier = QueryClassifier()
    
    # Test cases for sophisticated queries
    test_queries = [
        # Comparative queries
        "Average temperature difference between Mumbai coast and Arabian Sea",
        "Compare salinity between coastal and offshore regions",
        "Temperature difference between surface and deep water near Mumbai",
        "What's warmer - northern Arabian Sea vs southern Arabian Sea?",
        
        # Statistical queries
        "Show correlation between temperature and depth",
        "Calculate median temperature at different depths",
        "Find temperature percentiles for each depth layer",
        "Statistical analysis of salinity distribution",
        
        # Complex analytical queries
        "Average temperature by depth categories with standard deviation",
        "Temperature gradient analysis from surface to deep water",
        "Seasonal temperature variations in different regions",
        "Water mass properties analysis near Mumbai",
        
        # Edge cases
        "Find outliers in temperature measurements",
        "Compare this year vs last year temperature trends",
        "Temperature anomalies detection",
        "Depth-stratified analysis of all parameters"
    ]
    
    print("Testing Sophisticated SQL Query Generation")
    print("=" * 60)
    
    success_count = 0
    total_queries = len(test_queries)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        
        try:
            # Classify the query
            classification = query_classifier.classify_query(query)
            print(f"   Classification: {classification['complexity_level']}, needs_data: {classification['needs_data']}")
            
            # Generate SQL
            sql = await sql_generator.generate_sql(query, classification)
            
            if sql:
                # Validate SQL
                is_valid = sql_generator.validate_sql(sql)
                status = "VALID" if is_valid else "INVALID"
                print(f"   Status: {status}")
                
                if is_valid:
                    # Clean up SQL for display
                    clean_sql = sql.strip().replace('\n            ', '\n   ')
                    print(f"   Generated SQL:\n   {clean_sql}")
                    success_count += 1
                else:
                    print(f"   Validation Error: SQL failed safety checks")
                    print(f"   SQL: {sql[:100]}...")
            else:
                print(f"   Status: GENERATION FAILED")
                
        except Exception as e:
            print(f"   Status: ERROR - {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {success_count}/{total_queries} queries successfully generated and validated")
    print(f"   Success Rate: {(success_count/total_queries)*100:.1f}%")
    
    return success_count, total_queries

def test_query_classification():
    """Test query classification for edge cases"""
    
    print("\nTesting Query Classification Edge Cases")
    print("=" * 60)
    
    classifier = QueryClassifier()
    
    edge_cases = [
        "What is ocean?",  # General query
        "Temperature",  # Single word
        "Show me everything",  # Vague request
        "Average difference between area A and area B temperature",  # Complex comparative
        "Find correlation between all parameters at all depths",  # Extremely complex
        "",  # Empty query
        "   ",  # Whitespace only
    ]
    
    for query in edge_cases:
        print(f"\nQuery: '{query}'")
        try:
            result = classifier.classify_query(query)
            print(f"  Complexity: {result['complexity_level']}")
            print(f"  Needs data: {result['needs_data']}")
            print(f"  Confidence: {result['confidence']:.2f}")
        except Exception as e:
            print(f"  Error: {str(e)}")

if __name__ == "__main__":
    print("Starting Sophisticated Query Testing Suite\n")
    
    # Test query classification
    test_query_classification()
    
    # Test SQL generation
    asyncio.run(test_sophisticated_queries())
    
    print("\nTesting Complete!")