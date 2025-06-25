"""
Simple Lock Manager - Self-Hosted Version
Minimal locking for self-hosted environments
"""

import os
import time
from pathlib import Path
from typing import Dict, Any

class SimpleLock:
    """Minimal lock for self-hosted bot"""
    
    def __init__(self, lock_name: str = "synapsechat_bot"):
        self.lock_name = lock_name
        self.acquired = False
    
    def acquire(self, timeout: int = 5) -> bool:
        """Simple acquire - just log the attempt"""
        print(f"🔒 Starting {self.lock_name} instance")
        self.acquired = True
        return True
    
    def release(self):
        """Simple release - just log"""
        if self.acquired:
            print(f"✅ {self.lock_name} instance stopped")
            self.acquired = False
    
    def is_locked(self) -> bool:
        """Check if locked"""
        return self.acquired
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

# Simple compatibility functions
def check_development_conflict():
    """No conflict checking needed in self-hosted"""
    return {
        'blocked': False,
        'reason': 'Self-hosted mode - no conflicts',
        'environment': 'selfhost'
    }

def block_if_development():
    """No blocking needed in self-hosted"""
    return False

# Aliases for compatibility
ProductionLock = SimpleLock
InstanceLock = SimpleLock

# Global instances
production_lock = SimpleLock()
instance_manager = SimpleLock()