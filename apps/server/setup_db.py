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
    
    # Get database connection parameters from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', '5432'))
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'password')
    database_name = os.getenv('DB_NAME', 'floatchat')
    
    # Database connection parameters
    db_params = {
        'host': db_host,
        'port': db_port,
        'user': db_user, 
        'password': db_password
    }
    
    print(f"Connecting to PostgreSQL at {db_host}:{db_port} as user '{db_user}'")
    print(f"Target database: {database_name}")
    
    try:
        # Validate required environment variables
        required_vars = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please check your .env file and ensure all required variables are set.")
            return False
            
        # Connect to PostgreSQL server (not to a specific database)
        print("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        
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
        error_msg = str(e).strip()
        print(f"❌ PostgreSQL error: {error_msg}")
        
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
        print(f"❌ Unexpected error: {e}")
        print("💡 Please check your environment configuration and try again.")
        return False

if __name__ == "__main__":
    print("=== FloatChat Database Setup ===")
    print("")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  WARNING: .env file not found!")
        print("Please copy .env.example to .env and configure your database settings:")
        print("  cp .env.example .env")
        print("")
        print("Required environment variables:")
        print("  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        print("")
        
    success = setup_database()
    if success:
        print("")
        print("✅ Database setup completed successfully!")
        print("🚀 You can now start the server with: python src/main.py")
    else:
        print("")
        print("❌ Database setup failed!")
        print("Please ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. The database user has necessary permissions")
        print("")
        print("To test connection manually:")
        print("  psql -h localhost -U postgres -d postgres")