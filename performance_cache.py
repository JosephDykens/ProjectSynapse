"""
Performance Optimization Cache System
Provides in-memory caching for frequently accessed data to reduce database calls
"""

import time
import threading
from typing import Dict, Set, Optional, Any

class PerformanceCache:
    """Thread-safe cache for bot performance optimization"""
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Channel caches
        self._crosschat_channels: Set[str] = set()
        self._crosschat_channels_updated = 0
        self._crosschat_channels_ttl = 900  # 15 minutes
        
        # System config cache
        self._system_config: Dict[str, Any] = {}
        self._system_config_updated = 0
        self._system_config_ttl = 900  # 15 minutes
        
        # VIP user cache
        self._vip_users: Set[str] = set()
        self._vip_users_updated = 0
        self._vip_users_ttl = 900  # 15 minutes
        
        # Ban cache
        self._banned_users: Set[str] = set()
        self._banned_servers: Set[str] = set()
        self._bans_updated = 0
        self._bans_ttl = 900  # 15 minutes
        
        # Connection pool for database
        self._db_connections = []
        self._max_connections = 3
        
    def get_crosschat_channels(self) -> Set[str]:
        """Get cached crosschat channels with automatic refresh"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._crosschat_channels_updated) > self._crosschat_channels_ttl:
                self._refresh_crosschat_channels()
            
            return self._crosschat_channels.copy()
    
    def _refresh_crosschat_channels(self):
        """Refresh crosschat channels from database"""
        try:
            # Use MongoDB handler for crosschat channels
            from mongodb_handler import mongo_handler
            
            # Get crosschat channels from MongoDB
            channels_data = mongo_handler.get_crosschat_channels()
            channels = set()
            
            # Extract channel IDs from MongoDB data
            for guild_id, guild_data in channels_data.items():
                if isinstance(guild_data, dict) and 'channels' in guild_data:
                    for channel_id in guild_data['channels']:
                        channels.add(str(channel_id))
            
            # MongoDB operations complete - no cleanup needed
            
            self._crosschat_channels = channels
            self._crosschat_channels_updated = time.time()
            print(f"CACHE_REFRESH: Updated {len(channels)} crosschat channels")
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh crosschat channels: {e}")
            import traceback
            traceback.print_exc()
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get cached system configuration"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._system_config_updated) > self._system_config_ttl:
                self._refresh_system_config()
            
            return self._system_config.copy()
    
    def _refresh_system_config(self):
        """Refresh system configuration from database"""
        try:
            from database_storage_new import database_storage
            
            # Get system config from database
            config = {
                'cross_chat_enabled': database_storage.get_config('cross_chat_enabled', True),
                'auto_moderation_enabled': database_storage.get_config('auto_moderation_enabled', True)
            }
            
            self._system_config = config
            self._system_config_updated = time.time()
            print(f"CACHE_REFRESH: Updated system config")
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh system config: {e}")
            # Use defaults on error
            self._system_config = {
                'cross_chat_enabled': True,
                'auto_moderation_enabled': True
            }
    
    def get_vip_users(self) -> Set[str]:
        """Get cached VIP users"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._vip_users_updated) > self._vip_users_ttl:
                self._refresh_vip_users()
            
            return self._vip_users.copy()
    
    def _refresh_vip_users(self):
        """Refresh VIP users from database"""
        try:
            from database_storage_new import database_storage
            
            # Get VIP users from database
            conn = database_storage.get_connection()
                cur.execute("""
                    SELECT DISTINCT user_id FROM chat_logs 
                    WHERE is_vip = true 
                    AND timestamp > NOW() - INTERVAL '24 hours'
                """)
                vip_users = {str(row[0]) for row in cur.fetchall()}
            
            self._vip_users = vip_users
            self._vip_users_updated = time.time()
            print(f"CACHE_REFRESH: Updated {len(vip_users)} VIP users")
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh VIP users: {e}")
    
    def get_banned_users(self) -> Set[str]:
        """Get cached banned users"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._bans_updated) > self._bans_ttl:
                self._refresh_bans()
            
            return self._banned_users.copy()
    
    def get_banned_servers(self) -> Set[str]:
        """Get cached banned servers"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._bans_updated) > self._bans_ttl:
                self._refresh_bans()
            
            return self._banned_servers.copy()
    
    def _refresh_bans(self):
        """Refresh ban lists from database"""
        try:
            from database_storage_new import database_storage
            
            # Get bans from database
            banned_users = set()
            banned_servers = set()
            
            conn = database_storage.get_connection()
                # Get user bans
                cur.execute("""
                    SELECT DISTINCT user_id FROM moderation_actions 
                    WHERE action_type = 'ban' 
                    AND status = 'active'
                """)
                banned_users = {str(row[0]) for row in cur.fetchall()}
                
                # Get server bans
                cur.execute("""
                    SELECT DISTINCT guild_id FROM moderation_actions 
                    WHERE action_type = 'server_ban' 
                    AND status = 'active'
                """)
                banned_servers = {str(row[0]) for row in cur.fetchall()}
            
            self._banned_users = banned_users
            self._banned_servers = banned_servers
            self._bans_updated = time.time()
            print(f"CACHE_REFRESH: Updated {len(banned_users)} banned users, {len(banned_servers)} banned servers")
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh bans: {e}")
    
    def invalidate_crosschat_channels(self):
        """Force refresh of crosschat channels on next access"""
        with self._lock:
            self._crosschat_channels_updated = 0
            print("CACHE_INVALIDATE: CrossChat channels cache invalidated - will refresh on next access")
    
    def add_crosschat_channel(self, channel_id: str):
        """Add channel to cache immediately"""
        with self._lock:
            self._crosschat_channels.add(str(channel_id))
            print(f"CACHE_UPDATE: Added channel {channel_id} to crosschat cache")
    
    def remove_crosschat_channel(self, channel_id: str):
        """Remove channel from cache immediately"""
        with self._lock:
            self._crosschat_channels.discard(str(channel_id))
            print(f"CACHE_UPDATE: Removed channel {channel_id} from crosschat cache")
    
    def invalidate_system_config(self):
        """Force refresh of system config on next access"""
        with self._lock:
            self._system_config_updated = 0
    
    def invalidate_bans(self):
        """Force refresh of ban lists on next access"""
        with self._lock:
            self._bans_updated = 0
    
    def add_vip_user(self, user_id: str):
        """Add user to VIP cache immediately"""
        with self._lock:
            self._vip_users.add(str(user_id))
    
    def remove_vip_user(self, user_id: str):
        """Remove user from VIP cache immediately"""
        with self._lock:
            self._vip_users.discard(str(user_id))
    
    def is_cached_vip(self, user_id: str) -> Optional[bool]:
        """Check if user is VIP from cache (returns None if cache expired)"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._vip_users_updated) <= self._vip_users_ttl:
                return str(user_id) in self._vip_users
            
            return None  # Cache expired, need fresh check
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        with self._lock:
            current_time = time.time()
            
            return {
                'crosschat_channels': {
                    'count': len(self._crosschat_channels),
                    'age': current_time - self._crosschat_channels_updated,
                    'ttl': self._crosschat_channels_ttl
                },
                'system_config': {
                    'age': current_time - self._system_config_updated,
                    'ttl': self._system_config_ttl
                },
                'vip_users': {
                    'count': len(self._vip_users),
                    'age': current_time - self._vip_users_updated,
                    'ttl': self._vip_users_ttl
                },
                'bans': {
                    'users': len(self._banned_users),
                    'servers': len(self._banned_servers),
                    'age': current_time - self._bans_updated,
                    'ttl': self._bans_ttl
                }
            }

# Global cache instance
performance_cache = PerformanceCache()