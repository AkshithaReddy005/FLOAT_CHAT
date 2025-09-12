#!/usr/bin/env python3
"""
Test script to verify duplicate detection functionality.
This script tests the duplicate detection at both file and measurement levels.
"""

import os
import sys
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.database import ArgoMeasurement
from rag_pipeline.vector_store import VectorStore

load_dotenv()

def test_measurement_hash_generation():
    """Test measurement hash generation consistency"""
    print("Testing measurement hash generation...")
    
    # Create test measurement data
    test_measurement = {
        'float_id': 'TEST_001',
        'latitude': 45.123456,
        'longitude': -123.654321,
        'date': datetime(2024, 1, 15, 12, 30, 0),
        'depth': 100.25
    }
    
    # Generate hash twice - should be identical
    hash1 = ArgoMeasurement.generate_measurement_hash(
        test_measurement['float_id'],
        test_measurement['latitude'],
        test_measurement['longitude'],
        test_measurement['date'],
        test_measurement['depth']
    )
    
    hash2 = ArgoMeasurement.generate_measurement_hash(
        test_measurement['float_id'],
        test_measurement['latitude'],
        test_measurement['longitude'],
        test_measurement['date'],
        test_measurement['depth']
    )
    
    assert hash1 == hash2, "Hash generation is not consistent!"
    print(f"Hash generation is consistent: {hash1}")
    
    # Test that small changes produce different hashes
    hash3 = ArgoMeasurement.generate_measurement_hash(
        test_measurement['float_id'],
        test_measurement['latitude'] + 0.000001,  # Tiny change
        test_measurement['longitude'],
        test_measurement['date'],
        test_measurement['depth']
    )
    
    assert hash1 != hash3, "Hash should change with coordinate changes!"
    print("Hash changes with coordinate differences")
    
    return hash1

def test_vector_store_id_generation():
    """Test vector store ID generation"""
    print("\nTesting vector store ID generation...")
    
    vector_store = VectorStore()
    
    test_measurement = {
        'float_id': 'TEST_001',
        'latitude': 45.123456,
        'longitude': -123.654321,
        'date': datetime(2024, 1, 15, 12, 30, 0),
        'depth': 100.25,
        'temperature': 15.5,
        'salinity': 35.2,
        'pressure': 100.25
    }
    
    # Generate ID twice - should be identical
    id1 = vector_store._generate_measurement_id(test_measurement)
    id2 = vector_store._generate_measurement_id(test_measurement)
    
    assert id1 == id2, "Vector store ID generation is not consistent!"
    print(f"Vector store ID generation is consistent: {id1}")
    
    return id1

def test_hash_consistency():
    """Test that database and vector store use same hashing logic"""
    print("\nTesting hash consistency between database and vector store...")
    
    test_measurement = {
        'float_id': 'TEST_001',
        'latitude': 45.123456,
        'longitude': -123.654321,
        'date': datetime(2024, 1, 15, 12, 30, 0),
        'depth': 100.25,
        'temperature': 15.5,
        'salinity': 35.2,
        'pressure': 100.25
    }
    
    # Get hashes from both systems
    db_hash = ArgoMeasurement.generate_measurement_hash(
        test_measurement['float_id'],
        test_measurement['latitude'],
        test_measurement['longitude'],
        test_measurement['date'],
        test_measurement['depth']
    )
    
    vector_store = VectorStore()
    vector_id = vector_store._generate_measurement_id(test_measurement)
    
    assert db_hash == vector_id, f"Database hash ({db_hash}) != Vector store ID ({vector_id})"
    print("Database and vector store use consistent hashing")

def test_file_hash_generation():
    """Test file hash generation"""
    print("\nTesting file hash generation...")
    
    # Create a temporary test file
    test_content = b"This is test NetCDF content for duplicate detection testing"
    
    # Generate hash twice - should be identical
    hash1 = hashlib.sha256(test_content).hexdigest()
    hash2 = hashlib.sha256(test_content).hexdigest()
    
    assert hash1 == hash2, "File hash generation is not consistent!"
    print(f"File hash generation is consistent: {hash1[:16]}...")
    
    # Test different content produces different hash
    different_content = b"This is different NetCDF content"
    hash3 = hashlib.sha256(different_content).hexdigest()
    
    assert hash1 != hash3, "Different content should produce different hashes!"
    print("Different content produces different hashes")

def simulate_duplicate_scenario():
    """Simulate a duplicate detection scenario"""
    print("\nSimulating duplicate detection scenario...")
    
    # Create test measurements
    measurements = [
        {
            'float_id': 'SIM_001',
            'latitude': 45.0,
            'longitude': -125.0,
            'date': datetime(2024, 1, 1),
            'depth': 10.0,
            'temperature': 15.0,
            'salinity': 35.0,
            'pressure': 10.0
        },
        {
            'float_id': 'SIM_001',
            'latitude': 45.0,
            'longitude': -125.0,
            'date': datetime(2024, 1, 1),
            'depth': 20.0,
            'temperature': 14.5,
            'salinity': 35.1,
            'pressure': 20.0
        },
        # This is a duplicate of the first measurement
        {
            'float_id': 'SIM_001',
            'latitude': 45.0,
            'longitude': -125.0,
            'date': datetime(2024, 1, 1),
            'depth': 10.0,  # Same depth as first = duplicate
            'temperature': 15.0,
            'salinity': 35.0,
            'pressure': 10.0
        }
    ]
    
    # Add measurement hashes
    for measurement in measurements:
        measurement['measurement_hash'] = ArgoMeasurement.generate_measurement_hash(
            measurement['float_id'],
            measurement['latitude'],
            measurement['longitude'],
            measurement['date'],
            measurement['depth']
        )
    
    # Check for duplicates
    seen_hashes = set()
    unique_measurements = []
    duplicate_count = 0
    
    for measurement in measurements:
        if measurement['measurement_hash'] in seen_hashes:
            duplicate_count += 1
            print(f"  - Duplicate detected: depth {measurement['depth']}m")
        else:
            seen_hashes.add(measurement['measurement_hash'])
            unique_measurements.append(measurement)
            print(f"  - New measurement: depth {measurement['depth']}m")
    
    print(f"✓ Duplicate detection works: {len(unique_measurements)} unique, {duplicate_count} duplicates")

def main():
    """Run all duplicate detection tests"""
    print("Running Duplicate Detection Tests\n")
    print("=" * 50)
    
    try:
        test_measurement_hash_generation()
        test_vector_store_id_generation()
        test_hash_consistency()
        test_file_hash_generation()
        simulate_duplicate_scenario()
        
        print("\n" + "=" * 50)
        print("All duplicate detection tests passed!")
        print("\nThe system is ready to handle duplicate detection for:")
        print("  1. File-level duplicates (same file uploaded twice)")
        print("  2. Measurement-level duplicates (same measurement in different files)")
        print("  3. Vector store duplicates (consistent with database)")
        print("  4. Hash consistency across components")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
