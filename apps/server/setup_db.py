#!/usr/bin/env python3
"""
Database setup script for FloatChat ARGO Data System
This script creates the PostgreSQL database and tables if they don't exist
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up PostgreSQL database"""
    
    # Database connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres', 
        'password': 'password'
    }
    
    database_name = 'floatchat'
    
    try:
        # Connect to PostgreSQL server (not to a specific database)
        print("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database_name,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{database_name}'...")
            cursor.execute(f"CREATE DATABASE {database_name}")
            print(f"Database '{database_name}' created successfully!")
        else:
            print(f"Database '{database_name}' already exists.")
        
        cursor.close()
        conn.close()
        
        # Now connect to the specific database and create tables
        db_params['database'] = database_name
        print(f"Connecting to database '{database_name}'...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Create the argo_measurements table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS argo_measurements (
            id SERIAL PRIMARY KEY,
            float_id VARCHAR(255),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            date TIMESTAMP,
            depth DOUBLE PRECISION,
            temperature DOUBLE PRECISION,
            salinity DOUBLE PRECISION,
            pressure DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_argo_float_id ON argo_measurements(float_id);
        CREATE INDEX IF NOT EXISTS idx_argo_date ON argo_measurements(date);
        CREATE INDEX IF NOT EXISTS idx_argo_location ON argo_measurements(latitude, longitude);
        """
        
        print("Creating tables and indexes...")
        cursor.execute(create_table_sql)
        conn.commit()
        print("Tables created successfully!")
        
        cursor.close()
        conn.close()
        
        print("Database setup completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== FloatChat Database Setup ===")
    success = setup_database()
    if success:
        print("Database setup completed successfully!")
        print("You can now start the server with: python src/main.py")
    else:
        print("Database setup failed!")
        print("Please ensure PostgreSQL is running and the connection parameters are correct.")