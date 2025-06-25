"""
Simple Database Handler with Graceful Error Handling
Prevents bot startup failures when database is unavailable
"""

import os
import psycopg2
import psycopg2.pool
import threading
import time
from typing import Optional, Dict, Any

class SafeDatabaseHandler:
    """Database handler that gracefully handles connection failures"""
    
    def __init__(self):
        self.pool = None
        self._pool_lock = threading.Lock()
        self.connection_failed = False
        
    def _create_pool(self) -> bool:
        """Create database connection pool"""
        try:
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                print("⚠️ DATABASE_URL not set - running without database")
                return False
                
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                1, 10,  # Reduced pool size for stability
                database_url,
                keepalives_idle=600,
                keepalives_interval=30,
                keepalives_count=3
            )
            print("✅ Database connection pool created")
            return True
            
        except Exception as e:
            print(f"⚠️ Database connection failed: {e}")
            print("Bot will start without database features")
            self.connection_failed = True
            return False
    
    def get_connection(self):
        """Get database connection with lazy initialization"""
        if self.connection_failed:
            return None
            
        if self.pool is None:
            with self._pool_lock:
                if self.pool is None:
                    if not self._create_pool():
                        return None
        
        try:
            return self.pool.getconn() if self.pool else None
        except Exception as e:
            print(f"Failed to get database connection: {e}")
            return None
    
    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            if self.pool and conn:
                self.pool.putconn(conn)
        except Exception as e:
            print(f"Error returning connection: {e}")
    
    def execute_query(self, query: str, params=None) -> Optional[list]:
        """Execute query with error handling"""
        conn = self.get_connection()
        if not conn:
            return None
            
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                try:
                    return cursor.fetchall()
                except psycopg2.ProgrammingError:
                    # No results to fetch (INSERT/UPDATE/DELETE)
                    return []
        except Exception as e:
            print(f"Database query error: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def is_available(self) -> bool:
        """Check if database is available"""
        return self.pool is not None and not self.connection_failed

# Global instance
db_handler = SafeDatabaseHandler()