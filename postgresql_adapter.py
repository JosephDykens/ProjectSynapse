"""
PostgreSQL Adapter for Database Logging
Adapts existing PostgreSQL storage to match MongoDB interface
"""

from datetime import datetime
from typing import Dict, List

class PostgreSQLAdapter:
    """Adapter to use PostgreSQL storage with MongoDB-like interface"""
    
    def __init__(self, pg_storage):
        self.pg_storage = pg_storage
    
    def add_warning(self, user_id: str, moderator_id: str, reason: str) -> bool:
        """Add warning to PostgreSQL database"""
        try:
            warning_data = {
                'user_id': user_id,
                'username': f"User {user_id}",  # Will be updated with actual username
                'reason': reason,
                'warned_by': moderator_id,
                'timestamp': datetime.now()
            }
            self.pg_storage.add_warning(warning_data)
            return True
        except Exception as e:
            print(f"PostgreSQL warning logging error: {e}")
            return False
    
    def ban_user(self, user_id: str, moderator_id: str, reason: str) -> bool:
        """Add ban to PostgreSQL database"""
        try:
            ban_data = {
                'user_id': user_id,
                'username': f"User {user_id}",  # Will be updated with actual username
                'reason': reason,
                'banned_by': moderator_id,
                'banned_at': datetime.now(),
                'is_active': True
            }
            self.pg_storage.add_ban(ban_data)
            return True
        except Exception as e:
            print(f"PostgreSQL ban logging error: {e}")
            return False
    
    def is_user_banned(self, user_id: str) -> bool:
        """Check if user is banned"""
        try:
            return self.pg_storage.is_user_banned(user_id)
        except Exception:
            return False
    
    def get_user_warnings(self, user_id: str) -> List[Dict]:
        """Get user warnings"""
        try:
            return self.pg_storage.get_user_warnings(user_id)
        except Exception:
            return []