#!/usr/bin/env python3
"""
ChromaDB cleanup script.
This script will completely clear the ChromaDB vector store to start fresh.
"""

import os
import sys
import shutil
from dotenv import load_dotenv

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from rag_pipeline.vector_store import VectorStore

load_dotenv()

def cleanup_chroma_database():
    """Clean up the ChromaDB database completely"""
    
    print("🧹 ChromaDB Cleanup Script")
    print("=" * 40)
    
    try:
        # Initialize vector store
        print("Initializing vector store connection...")
        vector_store = VectorStore()
        
        # Get current stats before cleanup
        try:
            stats_before = vector_store.get_collection_stats()
            print(f"Current measurements in ChromaDB: {stats_before.get('total_measurements', 0)}")
        except Exception:
            print("Could not get current stats (database might already be empty)")
        
        # Method 1: Use the clear_all method
        print("\nClearing ChromaDB using clear_all method...")
        vector_store.clear_all()
        print("✓ ChromaDB collection cleared using clear_all()")
        
        # Verify it's empty
        stats_after = vector_store.get_collection_stats()
        print(f"Measurements after cleanup: {stats_after.get('total_measurements', 0)}")
        
        # Method 2: Also remove the physical files for a complete cleanup
        chroma_dir = vector_store.persist_dir
        print(f"\nChromaDB data directory: {chroma_dir}")
        
        if os.path.exists(chroma_dir):
            try:
                # Close the connection first
                del vector_store
                
                print("Removing ChromaDB data directory for complete cleanup...")
                shutil.rmtree(chroma_dir)
                print(f"✓ Removed directory: {chroma_dir}")
                
                # Recreate the vector store to ensure it's working
                print("Recreating vector store...")
                new_vector_store = VectorStore()
                final_stats = new_vector_store.get_collection_stats()
                print(f"✓ New vector store created with {final_stats.get('total_measurements', 0)} measurements")
                
            except Exception as e:
                print(f"Warning: Could not remove data directory: {e}")
                print("This is usually fine - the collection was already cleared")
        else:
            print(f"ChromaDB data directory doesn't exist: {chroma_dir}")
        
        print("\n" + "=" * 40)
        print("🎉 ChromaDB cleanup completed successfully!")
        print("\nThe vector store is now empty and ready for fresh data.")
        print("You can now upload NetCDF files to test the duplicate detection from scratch.")
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        sys.exit(1)

def main():
    """Main function"""
    
    # Ask for confirmation
    print("This will completely clear the ChromaDB vector store.")
    print("All embeddings and measurements will be permanently deleted.")
    
    response = input("\nAre you sure you want to proceed? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        cleanup_chroma_database()
    else:
        print("Cleanup cancelled.")

if __name__ == "__main__":
    main()
