import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env from the server directory
env_path = os.path.join(os.path.dirname(__file__), 'apps', 'server', '.env')
load_dotenv(env_path)

# Add server directory to path
server_dir = os.path.join(os.path.dirname(__file__), 'apps', 'server', 'src')
sys.path.insert(0, server_dir)

from rag_pipeline.vector_store import VectorStore
from database.database import ArgoMeasurement

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

print("=== Rebuilding Vector Store with Updated Region Definitions ===")

# Initialize vector store
vector_store = VectorStore()

# Clear existing collection
try:
    vector_store.client.delete_collection("argo_data_enhanced")
    print("Deleted existing collection")
except:
    print("No existing collection to delete")

# Re-initialize to create new collection
vector_store = VectorStore()
print("Created new collection with updated region definitions")

# Get all measurements from database
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT float_id, latitude, longitude, date, depth, temperature, salinity, pressure
        FROM argo_measurements
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            AND temperature IS NOT NULL AND salinity IS NOT NULL
        ORDER BY id
    """)).fetchall()
    
    print(f"Found {len(result)} measurements to process")
    
    # Convert to dictionaries for vector store
    measurements = []
    for row in result:
        measurements.append({
            'float_id': row[0],
            'latitude': float(row[1]),
            'longitude': float(row[2]),
            'date': row[3],
            'depth': float(row[4]),
            'temperature': float(row[5]),
            'salinity': float(row[6]),
            'pressure': float(row[7])
        })
    
    # Add to vector store in batches
    batch_size = 1000
    total_added = 0
    
    for i in range(0, len(measurements), batch_size):
        batch = measurements[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(measurements)-1)//batch_size + 1}...")
        
        result = vector_store.add_measurements(batch)
        total_added += result.get('new_measurements', 0)
        
        print(f"  Added: {result.get('new_measurements', 0)}, Duplicates: {result.get('duplicates_skipped', 0)}")
    
    print(f"\n=== Summary ===")
    print(f"Total measurements processed: {len(measurements)}")
    print(f"Total added to vector store: {total_added}")
    
    # Test the new region distribution
    print("\n=== Testing Region Distribution ===")
    test_regions = ['southern_indian_ocean', 'southern_ocean', 'arctic_ocean', 'equatorial_indian_ocean']
    
    for region in test_regions:
        # Test search for this region
        from rag_pipeline.parameter_context import ParameterContext
        context = ParameterContext(original_query=f"test {region}", query_id="test_id", location_name=region)
        
        results = vector_store.search_with_context(context, n_results=5)
        count = len(results.get('documents', [[]])[0]) if results.get('documents') else 0
        print(f"{region}: {count} results found")
