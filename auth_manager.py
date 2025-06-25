"""
Authentication Manager - Self-Hosted Version
Handles authentication and authorization for self-hosted bot
"""

import os
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class AuthManager:
    """Authentication and authorization manager for self-hosted bot"""
    
    def __init__(self, database_storage=None):
        self.database = database_storage
        self.owner_id = os.getenv('BOT_OWNER_ID')
        self.staff_role_id = os.getenv('STAFF_ROLE_ID')
        self.vip_role_id = os.getenv('VIP_ROLE_ID')
        self.synapsechat_guild_id = os.getenv('SYNAPSECHAT_GUILD_ID')
        
        # Permission levels
        self.PERMISSION_LEVELS = {
            'owner': 100,
            'admin': 80,
            'staff': 60,
            'vip': 40,
            'user': 20,
            'banned': 0
        }
    
    def get_user_permission_level(self, user, guild=None) -> int:
        """Get user's permission level"""
        user_id = str(user.id)
        
        # Owner has highest permissions
        if self.owner_id and user_id == self.owner_id:
            return self.PERMISSION_LEVELS['owner']
        
        # Check guild-based permissions
        if guild and hasattr(user, 'roles'):
            # Check for admin permissions
            if any(role.permissions.administrator for role in user.roles):
                return self.PERMISSION_LEVELS['admin']
            
            # Check for staff role
            if self.staff_role_id:
                staff_role_id = int(self.staff_role_id)
                if any(role.id == staff_role_id for role in user.roles):
                    return self.PERMISSION_LEVELS['staff']
            
            # Check for VIP role
            if self.vip_role_id:
                vip_role_id = int(self.vip_role_id)
                if any(role.id == vip_role_id for role in user.roles):
                    return self.PERMISSION_LEVELS['vip']
        
        # Check if user is banned
        if self.is_user_banned(user_id):
            return self.PERMISSION_LEVELS['banned']
        
        return self.PERMISSION_LEVELS['user']
    
    def has_permission(self, user, required_level: str, guild=None) -> bool:
        """Check if user has required permission level"""
        user_level = self.get_user_permission_level(user, guild)
        required_value = self.PERMISSION_LEVELS.get(required_level, 0)
        
        return user_level >= required_value
    
    def is_owner(self, user) -> bool:
        """Check if user is the bot owner"""
        return self.owner_id and str(user.id) == self.owner_id
    
    def is_staff(self, user, guild=None) -> bool:
        """Check if user is staff or higher"""
        return self.has_permission(user, 'staff', guild)
    
    def is_vip(self, user, guild=None) -> bool:
        """Check if user is VIP or higher"""
        return self.has_permission(user, 'vip', guild)
    
    def is_user_banned(self, user_id: str) -> bool:
        """Check if user is banned"""
        try:
            if self.database:
                return self.database.is_user_banned(user_id)
            return False
        except Exception:
            return False
    
    def ban_user(self, user_id: str, reason: str = None, moderator_id: str = None) -> bool:
        """Ban a user"""
        try:
            if self.database:
                ban_data = {
                    'user_id': user_id,
                    'reason': reason or 'No reason provided',
                    'moderator_id': moderator_id,
                    'banned_at': datetime.now().isoformat()
                }
                return self.database.ban_user(user_id, ban_data)
            return False
        except Exception as e:
            print(f"❌ Error banning user {user_id}: {e}")
            return False
    
    def unban_user(self, user_id: str, moderator_id: str = None) -> bool:
        """Unban a user"""
        try:
            if self.database:
                return self.database.unban_user(user_id, moderator_id)
            return False
        except Exception as e:
            print(f"❌ Error unbanning user {user_id}: {e}")
            return False
    
    def get_banned_users(self) -> List[Dict[str, Any]]:
        """Get list of banned users"""
        try:
            if self.database:
                return self.database.get_banned_users()
            return []
        except Exception:
            return []
    
    def check_vip_status(self, user, guild=None) -> Dict[str, Any]:
        """Check user's VIP status with detailed information"""
        result = {
            'is_vip': False,
            'has_role': False,
            'in_support_server': False,
            'permission_level': self.get_user_permission_level(user, guild)
        }
        
        # Check if user has VIP role
        if self.vip_role_id and guild and hasattr(user, 'roles'):
            vip_role_id = int(self.vip_role_id)
            result['has_role'] = any(role.id == vip_role_id for role in user.roles)
        
        # Check if in SynapseChat support server
        if self.synapsechat_guild_id:
            result['in_support_server'] = guild and str(guild.id) == self.synapsechat_guild_id
        
        # Determine VIP status
        result['is_vip'] = (
            result['has_role'] or 
            result['permission_level'] >= self.PERMISSION_LEVELS['vip']
        )
        
        return result
    
    def create_api_token(self, user_id: str, permissions: List[str] = None) -> str:
        """Create API token for user"""
        # Simple token generation for self-hosted version
        timestamp = str(int(datetime.now().timestamp()))
        user_hash = hashlib.sha256(f"{user_id}_{timestamp}".encode()).hexdigest()[:16]
        return f"selfhost_{user_hash}_{timestamp}"
    
    def validate_api_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate API token"""
        if not token or not token.startswith('selfhost_'):
            return None
        
        try:
            parts = token.split('_')
            if len(parts) != 3:
                return None
            
            _, user_hash, timestamp = parts
            token_time = datetime.fromtimestamp(int(timestamp))
            
            # Check if token is not too old (24 hours)
            if datetime.now() - token_time > timedelta(hours=24):
                return None
            
            return {
                'valid': True,
                'user_hash': user_hash,
                'created_at': token_time,
                'expires_at': token_time + timedelta(hours=24)
            }
            
        except (ValueError, IndexError):
            return None
    
    def get_user_permissions(self, user, guild=None) -> Dict[str, bool]:
        """Get detailed user permissions"""
        level = self.get_user_permission_level(user, guild)
        
        return {
            'can_moderate': level >= self.PERMISSION_LEVELS['staff'],
            'can_ban': level >= self.PERMISSION_LEVELS['staff'],
            'can_kick': level >= self.PERMISSION_LEVELS['staff'],
            'can_mute': level >= self.PERMISSION_LEVELS['staff'],
            'can_announce': level >= self.PERMISSION_LEVELS['staff'],
            'can_manage_channels': level >= self.PERMISSION_LEVELS['admin'],
            'can_manage_bot': level >= self.PERMISSION_LEVELS['owner'],
            'has_vip_features': level >= self.PERMISSION_LEVELS['vip'],
            'can_bypass_cooldowns': level >= self.PERMISSION_LEVELS['vip']
        }
    
    def log_auth_event(self, event_type: str, user_id: str, details: Dict[str, Any] = None):
        """Log authentication event"""
        try:
            if self.database:
                log_data = {
                    'event_type': event_type,
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat(),
                    'details': details or {}
                }
                self.database.log_auth_event(log_data)
        except Exception as e:
            print(f"❌ Error logging auth event: {e}")

# Global auth manager instance
auth_manager = None

def initialize_auth_manager(database_storage=None):
    """Initialize the global auth manager"""
    global auth_manager
    auth_manager = AuthManager(database_storage)
    return auth_manager