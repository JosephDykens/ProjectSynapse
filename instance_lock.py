"""
Instance Lock Manager - Self-Hosted Version
Manages bot instance locks and prevents conflicts
Cross-platform compatible (Windows/Linux/macOS)
"""

import os
import time
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional

class InstanceLockManager:
    """Manages instance locks for the self-hosted bot"""
    
    def __init__(self):
        # Use appropriate temp directory based on OS
        if platform.system() == "Windows":
            temp_dir = Path(os.environ.get('TEMP', 'C:/temp'))
        else:
            temp_dir = Path('/tmp')
        
        self.lock_dir = temp_dir / "synapsechat_locks"
        self.lock_dir.mkdir(exist_ok=True)
        self.instance_id = f"selfhost_{os.getpid()}_{int(time.time())}"
        self.locks = {}
    
    def acquire_bot_lock(self) -> bool:
        """Acquire main bot instance lock"""
        lock_file = self.lock_dir / "bot_instance.lock"
        
        try:
            if lock_file.exists():
                # Check if existing lock is stale
                with open(lock_file, 'r') as f:
                    lock_data = json.load(f)
                
                lock_age = time.time() - lock_data.get('timestamp', 0)
                if lock_age < 300:  # 5 minutes
                    print(f"❌ Another bot instance is running (PID: {lock_data.get('pid')})")
                    return False
                else:
                    print("🗑️ Removing stale lock file")
                    lock_file.unlink()
            
            # Create new lock
            lock_data = {
                'instance_id': self.instance_id,
                'pid': os.getpid(),
                'timestamp': time.time(),
                'type': 'selfhost_bot'
            }
            
            with open(lock_file, 'w') as f:
                json.dump(lock_data, f)
            
            print(f"✅ Bot instance lock acquired: {self.instance_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error acquiring bot lock: {e}")
            return False
    
    def release_bot_lock(self):
        """Release main bot instance lock"""
        lock_file = self.lock_dir / "bot_instance.lock"
        
        try:
            if lock_file.exists():
                lock_file.unlink()
                print("✅ Bot instance lock released")
        except Exception as e:
            print(f"❌ Error releasing bot lock: {e}")
    
    def acquire_discord_lock(self) -> bool:
        """Acquire Discord connection lock"""
        lock_file = self.lock_dir / "discord_connection.lock"
        
        try:
            if lock_file.exists():
                with open(lock_file, 'r') as f:
                    lock_data = json.load(f)
                
                lock_age = time.time() - lock_data.get('timestamp', 0)
                if lock_age < 180:  # 3 minutes
                    print(f"❌ Discord connection locked by another instance")
                    return False
                else:
                    lock_file.unlink()
            
            lock_data = {
                'instance_id': self.instance_id,
                'timestamp': time.time(),
                'type': 'discord_connection'
            }
            
            with open(lock_file, 'w') as f:
                json.dump(lock_data, f)
            
            print("🔒 Discord connection lock acquired")
            return True
            
        except Exception as e:
            print(f"❌ Error acquiring Discord lock: {e}")
            return False
    
    def release_discord_lock(self):
        """Release Discord connection lock"""
        lock_file = self.lock_dir / "discord_connection.lock"
        
        try:
            if lock_file.exists():
                lock_file.unlink()
                print("✅ Discord connection lock released")
        except Exception as e:
            print(f"❌ Error releasing Discord lock: {e}")
    
    def cleanup_stale_locks(self):
        """Clean up stale lock files"""
        try:
            for lock_file in self.lock_dir.glob("*.lock"):
                try:
                    with open(lock_file, 'r') as f:
                        lock_data = json.load(f)
                    
                    lock_age = time.time() - lock_data.get('timestamp', 0)
                    if lock_age > 600:  # 10 minutes
                        lock_file.unlink()
                        print(f"🗑️ Removed stale lock: {lock_file.name}")
                        
                except (json.JSONDecodeError, KeyError):
                    # Invalid lock file, remove it
                    lock_file.unlink()
                    print(f"🗑️ Removed invalid lock: {lock_file.name}")
                    
        except Exception as e:
            print(f"❌ Error cleaning stale locks: {e}")
    
    def get_active_locks(self) -> Dict[str, Any]:
        """Get information about active locks"""
        locks = {}
        
        try:
            for lock_file in self.lock_dir.glob("*.lock"):
                try:
                    with open(lock_file, 'r') as f:
                        lock_data = json.load(f)
                    
                    locks[lock_file.stem] = {
                        'instance_id': lock_data.get('instance_id'),
                        'pid': lock_data.get('pid'),
                        'timestamp': lock_data.get('timestamp'),
                        'age_seconds': time.time() - lock_data.get('timestamp', 0),
                        'type': lock_data.get('type')
                    }
                    
                except (json.JSONDecodeError, KeyError):
                    continue
                    
        except Exception as e:
            print(f"❌ Error getting active locks: {e}")
        
        return locks
    
    def force_release_all(self):
        """Force release all locks (emergency use)"""
        try:
            for lock_file in self.lock_dir.glob("*.lock"):
                lock_file.unlink()
                print(f"🔓 Force released: {lock_file.name}")
        except Exception as e:
            print(f"❌ Error force releasing locks: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.cleanup_stale_locks()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release_bot_lock()
        self.release_discord_lock()

# Global instance
instance_lock_manager = InstanceLockManager()

# Export for compatibility
InstanceLock = InstanceLockManager