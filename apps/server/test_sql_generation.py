#!/usr/bin/env python3
"""
Test SQL generation separately to debug issues
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sql_generator import SQLGenerator
from query_classifier import QueryClassifier

load_dotenv()

async def test_sql_generation():
    """Test SQL generation for sample queries"""
    
    print("=== SQL Generation Test ===")
    
    sql_gen = SQLGenerator()
    classifier = QueryClassifier()
    
    test_queries = [
        "Show me temperature profiles near Mumbai in March 2023",
        "What is the average temperature in the Arabian Sea?",
        "Find measurements with depth greater than 100 meters",
        "Analyze salinity patterns in the Indian Ocean"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        # Classify the query
        classification = classifier.classify_query(query)
        print(f"Classification: {classification}")
        
        # Generate SQL
        sql = await sql_gen.generate_sql(query, classification)
        print(f"Generated SQL: {sql}")
        
        # Validate SQL
        if sql:
            is_valid = sql_gen.validate_sql(sql)
            print(f"SQL Valid: {is_valid}")
            
            if not is_valid:
                print("Validation failed - reasons:")
                sql_clean = sql.strip().strip(';').lower()
                
                if not sql_clean.startswith("select"):
                    print("  - Does not start with SELECT")
                if " from argo_measurements" not in sql_clean:
                    print("  - Does not reference argo_measurements table")
                if " limit " not in sql_clean:
                    print("  - Missing LIMIT clause")
                
                forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", ";", "--", "/*", "*/"]
                for keyword in forbidden:
                    if keyword in sql_clean:
                        print(f"  - Contains forbidden keyword: {keyword}")
        else:
            print("No SQL generated")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_sql_generation())
