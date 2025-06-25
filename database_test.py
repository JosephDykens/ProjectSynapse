#!/usr/bin/env python3
"""
Database Connection Test Script
Tests both PostgreSQL and MongoDB connections
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_postgresql():
    """Test PostgreSQL connection"""
    database_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL: {database_url[:50]}..." if database_url else "DATABASE_URL: NOT SET")
    
    if not database_url:
        print("❌ PostgreSQL: DATABASE_URL not set")
        return False
        
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL: Connected successfully - {version[0][:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: Connection failed - {e}")
        return False

def test_mongodb():
    """Test MongoDB connection"""
    mongodb_url = os.environ.get('MONGODB_URL') or os.environ.get('MONGODB_URI')
    print(f"MONGODB_URL: {mongodb_url[:50]}..." if mongodb_url else "MONGODB_URL: NOT SET")
    
    if not mongodb_url:
        print("❌ MongoDB: MONGODB_URL/MONGODB_URI not set")
        return False
        
    try:
        from pymongo import MongoClient
        client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db_info = client.server_info()
        print(f"✅ MongoDB: Connected successfully - Version {db_info['version']}")
        client.close()
        return True
    except Exception as e:
        print(f"❌ MongoDB: Connection failed - {e}")
        return False

def test_database_storage():
    """Test existing database storage module"""
    try:
        from database_storage_new import DatabaseStorage
        storage = DatabaseStorage()
        print("✅ DatabaseStorage: Module loaded successfully")
        
        # Test basic connection
        if hasattr(storage, 'get_connection'):
            conn = storage.get_connection()
            if conn:
                print("✅ DatabaseStorage: Connection pool working")
                storage.return_connection(conn)
            else:
                print("❌ DatabaseStorage: Failed to get connection")
        
        return True
    except Exception as e:
        print(f"❌ DatabaseStorage: Failed to load - {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing Database Connections...\n")
    
    pg_works = test_postgresql()
    print()
    
    mongo_works = test_mongodb()
    print()
    
    storage_works = test_database_storage()
    print()
    
    print("📊 Summary:")
    print(f"PostgreSQL: {'✅ Available' if pg_works else '❌ Not Available'}")
    print(f"MongoDB: {'✅ Available' if mongo_works else '❌ Not Available'}")
    print(f"DatabaseStorage: {'✅ Working' if storage_works else '❌ Not Working'}")
    
    if not (pg_works or mongo_works):
        print("\n❌ CRITICAL: No database connections available!")
        print("Set DATABASE_URL (PostgreSQL) or MONGODB_URL (MongoDB) environment variable")
    else:
        print(f"\n✅ Database logging will work with: {'PostgreSQL' if pg_works else 'MongoDB'}")