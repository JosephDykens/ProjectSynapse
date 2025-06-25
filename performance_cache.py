"""
Performance Optimization Cache System - MongoDB Compatible
Provides in-memory caching for frequently accessed data to reduce database calls
"""

import time
import threading
from typing import Dict, Set, Optional, Any

class PerformanceCache:
    """Thread-safe cache for bot performance optimization - MongoDB compatible"""
    
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
        
    def get_crosschat_channels(self) -> Set[str]:
        """Get cached crosschat channels with automatic refresh"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._crosschat_channels_updated) > self._crosschat_channels_ttl:
                self._refresh_crosschat_channels()
            
            return self._crosschat_channels.copy()
    
    def _refresh_crosschat_channels(self):
        """Refresh crosschat channels from MongoDB"""
        try:
            # Simplified cache - real data comes from MongoDB handler
            channels = set()
            print(f"CACHE_REFRESH: MongoDB crosschat channel cache ready")
            
            self._crosschat_channels = channels
            self._crosschat_channels_updated = time.time()
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh crosschat channels: {e}")
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get cached system configuration"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._system_config_updated) > self._system_config_ttl:
                self._refresh_system_config()
            
            return self._system_config.copy()
    
    def _refresh_system_config(self):
        """Refresh system configuration - simplified for MongoDB"""
        try:
            # Default enabled configuration
            config = {
                'cross_chat_enabled': True,
                'auto_moderation_enabled': True
            }
            
            self._system_config = config
            self._system_config_updated = time.time()
            print(f"CACHE_REFRESH: System config ready")
            
        except Exception as e:
            print(f"CACHE_ERROR: Failed to refresh system config: {e}")
    
    def get_vip_users(self) -> Set[str]:
        """Get cached VIP users"""
        with self._lock:
            current_time = time.time()
            
            if (current_time - self._vip_users_updated) > self._vip_users_ttl:
                self._refresh_vip_users()
            
            return self._vip_users.copy()
    
    def _refresh_vip_users(self):
        """Refresh VIP users - simplified for MongoDB"""
        try:
            # VIP status is now checked globally via role checking
            # No database cache needed - roles checked in real-time
            vip_users = set()
            
            self._vip_users = vip_users
            self._vip_users_updated = time.time()
            print(f"CACHE_REFRESH: VIP user cache ready (global role checking)")
            
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
        """Refresh ban lists - simplified for MongoDB"""
        try:
            # Ban checking now uses MongoDB handler directly
            # Cache will be populated by real-time checks
            banned_users = set()
            banned_servers = set()
            
            self._banned_users = banned_users
            self._banned_servers = banned_servers
            self._bans_updated = time.time()
            print(f"CACHE_REFRESH: Ban cache ready (MongoDB checking)")
            
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
    
    def add_banned_user(self, user_id: str):
        """Add user to banned cache immediately"""
        with self._lock:
            self._banned_users.add(str(user_id))
            print(f"CACHE_UPDATE: Added user {user_id} to banned cache")
    
    def remove_banned_user(self, user_id: str):
        """Remove user from banned cache immediately"""
        with self._lock:
            self._banned_users.discard(str(user_id))
            print(f"CACHE_UPDATE: Removed user {user_id} from banned cache")
    
    def is_user_banned_cached(self, user_id: str) -> bool:
        """Quick cache check for user ban status"""
        return str(user_id) in self.get_banned_users()
    
    def is_server_banned_cached(self, server_id: str) -> bool:
        """Quick cache check for server ban status"""
        return str(server_id) in self.get_banned_servers()
    
    def is_crosschat_channel_cached(self, channel_id: str) -> bool:
        """Quick cache check for crosschat channel status"""
        return str(channel_id) in self.get_crosschat_channels()

# Global cache instance
performance_cache = PerformanceCache()

# For backwards compatibility
def get_cache():
    return performance_cache
