"""
Production Lock Manager - Self-Hosted Version
Prevents multiple bot instances and conflicts
Cross-platform compatible (Windows/Linux/macOS)
"""

import os
import time
import json
import platform
from pathlib import Path
from typing import Optional

# Try to import fcntl for Unix systems, fall back to file-based locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

class ProductionLock:
    """Manages production locks for self-hosted bot"""
    
    def __init__(self, lock_name: str = "synapsechat_bot"):
        self.lock_name = lock_name
        
        # Use appropriate temp directory based on OS
        if platform.system() == "Windows":
            temp_dir = Path(os.environ.get('TEMP', 'C:/temp'))
        else:
            temp_dir = Path('/tmp')
        
        temp_dir.mkdir(exist_ok=True)
        self.lock_file_path = temp_dir / f"{lock_name}.lock"
        self.lock_file = None
        self.acquired = False
    
    def acquire(self, timeout: int = 30) -> bool:
        """Acquire production lock using appropriate method for OS"""
        if HAS_FCNTL and platform.system() != "Windows":
            return self._acquire_unix(timeout)
        else:
            return self._acquire_windows(timeout)
    
    def _acquire_unix(self, timeout: int) -> bool:
        """Acquire lock using fcntl (Unix/Linux/macOS)"""
        try:
            # Create lock file
            self.lock_file = open(self.lock_file_path, 'w')
            
            # Try to acquire exclusive lock
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # Write process info
                    self.lock_file.write(f"{os.getpid()}\n{time.time()}\n")
                    self.lock_file.flush()
                    
                    self.acquired = True
                    print(f"✅ Production lock acquired (Unix): {self.lock_name}")
                    return True
                    
                except BlockingIOError:
                    # Lock is held by another process
                    time.sleep(1)
                    continue
            
            print(f"❌ Failed to acquire production lock: {self.lock_name}")
            return False
            
        except Exception as e:
            print(f"❌ Error acquiring production lock: {e}")
            return False
    
    def _acquire_windows(self, timeout: int) -> bool:
        """Acquire lock using file-based method (Windows compatible)"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Check if lock file exists and is still valid
                    if self.lock_file_path.exists():
                        try:
                            with open(self.lock_file_path, 'r') as f:
                                lock_data = json.load(f)
                            
                            # Check if lock is stale (older than 5 minutes)
                            lock_age = time.time() - lock_data.get('timestamp', 0)
                            if lock_age < 300:  # 5 minutes
                                # Check if process is still running
                                pid = lock_data.get('pid')
                                if pid and self._is_process_running(pid):
                                    print(f"❌ Another bot instance is running (PID: {pid})")
                                    time.sleep(1)
                                    continue
                                else:
                                    print("🗑️ Removing stale lock (process not running)")
                                    self.lock_file_path.unlink()
                            else:
                                print("🗑️ Removing expired lock file")
                                self.lock_file_path.unlink()
                        except (json.JSONDecodeError, KeyError):
                            print("🗑️ Removing invalid lock file")
                            self.lock_file_path.unlink()
                    
                    # Create new lock file atomically
                    lock_data = {
                        'pid': os.getpid(),
                        'timestamp': time.time(),
                        'instance': self.lock_name,
                        'platform': platform.system()
                    }
                    
                    # Write to temporary file first, then rename (atomic operation)
                    temp_path = self.lock_file_path.with_suffix('.tmp')
                    with open(temp_path, 'w') as f:
                        json.dump(lock_data, f)
                    
                    # Atomic rename
                    temp_path.replace(self.lock_file_path)
                    
                    self.acquired = True
                    print(f"✅ Production lock acquired (Windows): {self.lock_name}")
                    return True
                    
                except (OSError, PermissionError):
                    # Lock file might be in use, wait and retry
                    time.sleep(1)
                    continue
            
            print(f"❌ Failed to acquire production lock after {timeout}s")
            return False
            
        except Exception as e:
            print(f"❌ Error acquiring production lock: {e}")
            return False
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                      capture_output=True, text=True)
                return str(pid) in result.stdout
            else:
                # Unix-like systems
                os.kill(pid, 0)  # Doesn't actually kill, just checks if process exists
                return True
        except (OSError, subprocess.SubprocessError):
            return False
    
    def release(self):
        """Release production lock"""
        if self.acquired:
            try:
                if HAS_FCNTL and self.lock_file and platform.system() != "Windows":
                    # Unix release
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                    self.lock_file.close()
                
                # Remove lock file
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
                
                self.acquired = False
                print(f"✅ Production lock released: {self.lock_name}")
                
            except Exception as e:
                print(f"❌ Error releasing production lock: {e}")
    
    def is_locked(self) -> bool:
        """Check if lock is currently held"""
        return self.acquired
    
    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()

class InstanceLock:
    """Manages instance locks to prevent duplicates"""
    
    def __init__(self):
        self.locks = {}
    
    def acquire_instance_lock(self, instance_id: str) -> bool:
        """Acquire lock for specific instance"""
        lock = ProductionLock(f"synapsechat_instance_{instance_id}")
        if lock.acquire():
            self.locks[instance_id] = lock
            return True
        return False
    
    def release_instance_lock(self, instance_id: str):
        """Release lock for specific instance"""
        if instance_id in self.locks:
            self.locks[instance_id].release()
            del self.locks[instance_id]
    
    def release_all(self):
        """Release all instance locks"""
        for instance_id in list(self.locks.keys()):
            self.release_instance_lock(instance_id)

# Global instance
production_lock = ProductionLock()
instance_manager = InstanceLock()

# Global functions for compatibility
def check_development_conflict():
    """Check for development mode conflicts"""
    return {
        'blocked': False,
        'reason': 'Self-hosted mode allows all configurations',
        'environment': 'selfhost'
    }

def get_production_status():
    """Get production status"""
    return {
        'production': True,
        'selfhost': True,
        'platform': platform.system()
    }