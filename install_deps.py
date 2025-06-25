#!/usr/bin/env python3
"""
Dependency installer for SynapseChat Bot
Forces installation of critical dependencies
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Installed {package}")
        return True
    except Exception as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    """Install all required dependencies"""
    print("🔧 Installing SynapseChat dependencies...")
    
    dependencies = [
        "discord.py==2.4.0",
        "pymongo==4.6.1",
        "dnspython==2.4.2",
        "python-dotenv==1.0.0",
        "aiohttp==3.9.1", 
        "flask==3.0.0"
    ]
    
    success_count = 0
    for dep in dependencies:
        if install_package(dep):
            success_count += 1
    
    print(f"✅ Successfully installed {success_count}/{len(dependencies)} dependencies")
    
    # Test pymongo import
    try:
        import pymongo
        print("✅ pymongo import test successful")
    except ImportError:
        print("❌ pymongo import test failed")
        return False
    
    return success_count == len(dependencies)

if __name__ == "__main__":
    main()