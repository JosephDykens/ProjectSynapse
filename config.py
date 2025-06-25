"""
Configuration Manager - Self-Hosted Version
Handles bot configuration and settings
"""

import os
from typing import Dict, Any, Optional

class ConfigManager:
    """Configuration management for self-hosted bot"""
    
    def __init__(self):
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables"""
        self.config = {
            # Discord Configuration
            'DISCORD_TOKEN': os.getenv('DISCORD_BOT_TOKEN', ''),
            'BOT_OWNER_ID': int(os.getenv('BOT_OWNER_ID', '0')) if os.getenv('BOT_OWNER_ID') else None,
            
            # Database Configuration
            'DATABASE_URL': os.getenv('DATABASE_URL', ''),
            
            # VIP Configuration
            'SYNAPSECHAT_GUILD_ID': int(os.getenv('SYNAPSECHAT_GUILD_ID', '0')) if os.getenv('SYNAPSECHAT_GUILD_ID') else None,
            'VIP_ROLE_ID': int(os.getenv('VIP_ROLE_ID', '0')) if os.getenv('VIP_ROLE_ID') else None,
            'STAFF_ROLE_ID': int(os.getenv('STAFF_ROLE_ID', '0')) if os.getenv('STAFF_ROLE_ID') else None,
            
            # Bot Settings
            'PRODUCTION_MODE': os.getenv('PRODUCTION_MODE', 'true').lower() == 'true',
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            'MAX_MESSAGE_LENGTH': int(os.getenv('MAX_MESSAGE_LENGTH', '2000')),
            'CROSSCHAT_COOLDOWN': int(os.getenv('CROSSCHAT_COOLDOWN', '1')),
            'AUTO_RECONNECT': os.getenv('AUTO_RECONNECT', 'true').lower() == 'true',
            'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '3')),
            
            # Self-Host Specific
            'SELFHOST_MODE': True,
            'WEB_PANEL_SYNC': os.getenv('WEB_PANEL_SYNC', 'true').lower() == 'true',
            'AUTO_MODERATION': os.getenv('AUTO_MODERATION', 'true').lower() == 'true',
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def get_discord_token(self) -> str:
        """Get Discord bot token"""
        return self.config.get('DISCORD_TOKEN', '')
    
    def get_database_url(self) -> str:
        """Get database URL"""
        return self.config.get('DATABASE_URL', '')
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.config.get('PRODUCTION_MODE', True)
    
    def is_selfhost(self) -> bool:
        """Check if running in self-host mode"""
        return self.config.get('SELFHOST_MODE', True)
    
    def get_vip_config(self) -> Dict[str, Optional[int]]:
        """Get VIP configuration"""
        return {
            'guild_id': self.config.get('SYNAPSECHAT_GUILD_ID'),
            'vip_role_id': self.config.get('VIP_ROLE_ID'),
            'staff_role_id': self.config.get('STAFF_ROLE_ID')
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return status"""
        issues = []
        warnings = []
        
        # Check required settings
        if not self.config.get('DISCORD_TOKEN'):
            issues.append('DISCORD_TOKEN is required')
        
        if not self.config.get('DATABASE_URL'):
            issues.append('DATABASE_URL is required')
        
        # Check optional but recommended settings
        if not self.config.get('BOT_OWNER_ID'):
            warnings.append('BOT_OWNER_ID not set - some admin commands may not work')
        
        if not self.config.get('SYNAPSECHAT_GUILD_ID'):
            warnings.append('SYNAPSECHAT_GUILD_ID not set - VIP features disabled')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'config': self.config
        }
    
    def update_from_dict(self, new_config: Dict[str, Any]):
        """Update configuration from dictionary"""
        self.config.update(new_config)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        return self.config.copy()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value (alias for get method for compatibility)"""
        return self.get(key, default)

# Global configuration instance
config = ConfigManager()