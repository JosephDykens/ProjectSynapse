#!/usr/bin/env python3
"""
Database Setup Script for SynapseChat Bot
Creates all required tables and initial data
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        database_url = input("Enter DATABASE_URL: ").strip()
    
    if not database_url:
        print("ERROR: DATABASE_URL is required")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        print("Setting up SynapseChat database tables...")
        
        # Read and execute schema
        with open('database_schema_unified.sql', 'r') as f:
            schema = f.read()
            cursor.execute(schema)
        
        conn.commit()
        print("✅ Database setup complete")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()