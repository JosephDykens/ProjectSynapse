"""
Development Block Manager - Self-Hosted Version
Prevents development mode conflicts in production
"""

import os
from typing import Dict, Any

class DevelopmentBlocker:
    """Blocks development mode in production environment"""
    
    def __init__(self):
        self.is_production = os.getenv('PRODUCTION_MODE', 'true').lower() == 'true'
        self.selfhost_mode = True
    
    def check_development_conflict(self) -> Dict[str, Any]:
        """Check for development mode conflicts"""
        result = {
            'blocked': False,
            'reason': '',
            'environment': 'production' if self.is_production else 'development'
        }
        
        # In self-hosted mode, we allow both development and production
        if self.selfhost_mode:
            result['reason'] = 'Self-hosted mode allows all configurations'
            return result
        
        # Check for development indicators
        dev_indicators = [
            os.getenv('DEBUG', '').lower() == 'true',
            os.getenv('DEVELOPMENT', '').lower() == 'true',
            os.getenv('DEV_MODE', '').lower() == 'true'
        ]
        
        if self.is_production and any(dev_indicators):
            result['blocked'] = True
            result['reason'] = 'Development mode detected in production environment'
        
        return result
    
    def block_if_development(self) -> bool:
        """Block if development mode is detected"""
        conflict = self.check_development_conflict()
        return conflict['blocked']
    
    def enforce_production_mode(self) -> bool:
        """Enforce production mode settings"""
        if not self.is_production:
            return True
        
        # Set production environment variables
        os.environ['DEBUG'] = 'false'
        os.environ['DEVELOPMENT'] = 'false'
        os.environ['DEV_MODE'] = 'false'
        
        print("🔒 Production mode enforced")
        return True
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information"""
        return {
            'is_production': self.is_production,
            'is_selfhost': self.selfhost_mode,
            'debug_mode': os.getenv('DEBUG', 'false').lower() == 'true',
            'development_mode': os.getenv('DEVELOPMENT', 'false').lower() == 'true'
        }

# Global instance
development_blocker = DevelopmentBlocker()

# Export functions for compatibility
def check_development_conflict():
    """Check for development mode conflicts"""
    return development_blocker.check_development_conflict()

def block_if_development():
    """Block if development mode is detected"""
    return development_blocker.block_if_development()