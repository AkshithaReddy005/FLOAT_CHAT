#!/usr/bin/env python3
"""
Database setup script for FloatChat ARGO Data System
This script creates the PostgreSQL database and tables with duplicate detection features.

Required environment variable:
- DATABASE_URL: PostgreSQL connection string (e.g., postgresql://username:password@localhost:5432/db_name)
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up PostgreSQL database"""
    
    # Get database connection URL from environment variable
    database_url = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/db_name')
    
    # Parse the DATABASE_URL to extract components
    import urllib.parse
    parsed = urllib.parse.urlparse(database_url)
    
    db_host = parsed.hostname
    db_port = parsed.port or 5432
    db_user = parsed.username
    db_password = parsed.password
    database_name = parsed.path.lstrip('/')
    
    # Database connection parameters
    db_params = {
        'host': db_host,
        'port': db_port,
        'user': db_user, 
        'password': db_password
    }
    
    print(f"Using DATABASE_URL: {database_url}")
    print(f"Connecting to PostgreSQL at {db_host}:{db_port} as user '{db_user}'")
    print(f"Target database: {database_name}")
    
    try:
        # Validate DATABASE_URL is provided
        if not database_url or database_url == 'postgresql://username:password@localhost:5432/db_name':
            print("DATABASE_URL environment variable is not properly set.")
            print("Please check your .env file and ensure DATABASE_URL is configured.")
            return False
            
        # Connect to PostgreSQL server (not to a specific database)
        print("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"Connected to PostgreSQL: {version[0]}")
        
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
        
        # Create the tables with duplicate detection features
        create_tables_sql = """
        -- Create uploaded_files table for file-level duplicate detection
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            file_hash VARCHAR(64) UNIQUE NOT NULL,
            file_size INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            measurements_count INTEGER DEFAULT 0
        );
        
        -- Create argo_measurements table with duplicate detection features
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
            file_hash VARCHAR(64),
            measurement_hash VARCHAR(32) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_argo_float_id ON argo_measurements(float_id);
        CREATE INDEX IF NOT EXISTS idx_argo_date ON argo_measurements(date);
        CREATE INDEX IF NOT EXISTS idx_argo_location ON argo_measurements(latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_location_date ON argo_measurements(latitude, longitude, date);
        CREATE INDEX IF NOT EXISTS idx_float_date ON argo_measurements(float_id, date);
        CREATE INDEX IF NOT EXISTS idx_file_hash ON argo_measurements(file_hash);
        CREATE INDEX IF NOT EXISTS idx_measurement_hash ON argo_measurements(measurement_hash);
        CREATE INDEX IF NOT EXISTS idx_uploaded_files_hash ON uploaded_files(file_hash);
        
        -- Create unique constraint to prevent duplicate measurements
        -- This will create the constraint only if it doesn't already exist
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'unique_measurement'
            ) THEN
                ALTER TABLE argo_measurements 
                ADD CONSTRAINT unique_measurement 
                UNIQUE (float_id, latitude, longitude, date, depth);
            END IF;
        END $$;
        """
        
        print("Creating tables and indexes...")
        cursor.execute(create_tables_sql)
        conn.commit()
        print("Tables created successfully!")
        print("✓ uploaded_files table - tracks uploaded files for duplicate detection")
        print("✓ argo_measurements table - stores measurements with duplicate prevention")
        print("✓ Indexes created for optimal query performance")
        print("✓ Unique constraints applied to prevent duplicate data")
        
        cursor.close()
        conn.close()
        
        print("Database setup completed successfully!")
        return True
        
    except psycopg2.Error as e:
        error_msg = str(e).strip()
        print(f"PostgreSQL error: {error_msg}")
        
        # Provide specific guidance based on common errors
        if "authentication failed" in error_msg.lower():
            print("💡 This is likely a credential issue. Please check:")
            print("   - DB_USER and DB_PASSWORD in your .env file")
            print("   - PostgreSQL user permissions")
        elif "could not connect" in error_msg.lower():
            print("💡 This is likely a connection issue. Please check:")
            print("   - PostgreSQL is running (try: pg_ctl status)")
            print("   - DB_HOST and DB_PORT in your .env file")
            print("   - Firewall settings")
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            print("💡 Database creation failed. Please check:")
            print("   - User has CREATEDB permission")
            print("   - Sufficient disk space")
            
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Please check your environment configuration and try again.")
        return False

if __name__ == "__main__":
    print("=== FloatChat Database Setup ===")
    print("")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("WARNING: .env file not found!")
        print("Please copy .env.example to .env and configure your database settings:")
        print("  cp .env.example .env")
        print("")
        print("Required environment variables:")
        print("  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        print("")
        
    success = setup_database()
    if success:
        print("")
        print("Database setup completed successfully!")
        print("You can now start the server with: python src/main.py")
    else:
        print("")
        print("Database setup failed!")
        print("Please ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. The database user has necessary permissions")
        print("")
        print("To test connection manually:")
        print("  psql -h localhost -U postgres -d postgres")