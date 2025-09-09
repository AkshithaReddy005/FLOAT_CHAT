#!/usr/bin/env python3
"""
Verify ChromaDB is empty
"""

import os
import sys

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from vector_store import VectorStore

def verify_empty_chroma():
    """Verify that ChromaDB is empty"""
    
    print("🔍 Verifying ChromaDB is empty...")
    
    try:
        vector_store = VectorStore()
        stats = vector_store.get_collection_stats()
        
        total_measurements = stats.get('total_measurements', 0)
        
        print(f"Total measurements in ChromaDB: {total_measurements}")
        
        if total_measurements == 0:
            print("✅ ChromaDB is empty and ready for fresh testing!")
        else:
            print(f"⚠️  ChromaDB still contains {total_measurements} measurements")
            
        # Try a simple query to make sure it's working
        results = vector_store.search("test query", n_results=1)
        if results['documents'] and len(results['documents'][0]) > 0:
            print(f"⚠️  Found {len(results['documents'][0])} documents in search")
        else:
            print("✅ Search returns no results (as expected for empty database)")
        
    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")

if __name__ == "__main__":
    verify_empty_chroma()
