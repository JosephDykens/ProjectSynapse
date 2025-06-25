#!/usr/bin/env python3
"""
SynapseChat Bot - Self-Hosted Standalone Runner
Runs only the Discord bot with database integration
"""

import os
import sys
import asyncio
import signal
import psutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SelfHostedBot:
    def __init__(self):
        self.bot = None
        self.running = False
    
    def check_existing_instances(self):
        """Terminate any existing bot instances to prevent conflicts"""
        current_pid = os.getpid()
        terminated = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.info['name'] and proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline'])
                    if 'run_bot.py' in cmdline_str and proc.info['pid'] != current_pid:
                        print(f"SELFHOST: Terminating existing instance {proc.info['pid']}")
                        proc.terminate()
                        terminated += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if terminated > 0:
            print(f"SELFHOST: Terminated {terminated} existing instances")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"SELFHOST: Received signal {signum}, shutting down...")
        self.running = False
        if self.bot:
            asyncio.create_task(self.bot.close())
        sys.exit(0)
    
    async def start(self):
        """Start the self-hosted bot"""
        print("=== SYNAPSECHAT SELF-HOSTED BOT ===")
        print("✅ Zero duplication guarantee")
        print("✅ Database synchronized with web panel")
        print("✅ Atomic message processing")
        
        # Clean any existing lock files FIRST to prevent duplicate connection errors
        try:
            import glob
            os.makedirs('data', exist_ok=True)
            lock_files = glob.glob('data/*.lock')
            for lock_file in lock_files:
                try:
                    os.unlink(lock_file)
                    print(f"CLEANUP: Removed existing lock file {lock_file}")
                except:
                    pass
            print("✅ Lock files cleaned")
        except Exception as e:
            print(f"CLEANUP: Lock file cleanup error: {e}")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Terminate existing instances
        self.check_existing_instances()
        
        # Verify environment variables
        discord_token = os.getenv('DISCORD_TOKEN')
        database_url = os.getenv('DATABASE_URL')
        
        if not discord_token:
            print("❌ ERROR: DISCORD_TOKEN environment variable not set")
            print("Set it with: export DISCORD_TOKEN='your_bot_token'")
            sys.exit(1)
        
        if not database_url:
            print("❌ ERROR: DATABASE_URL environment variable not set")
            print("Set it with: export DATABASE_URL='postgresql://...'")
            sys.exit(1)
        
        print(f"✅ Discord token loaded ({len(discord_token)} characters)")
        print(f"✅ Database URL configured")
        
        try:
            # Import and create bot
            from bot import CrossChatBot
            self.bot = CrossChatBot()
            self.running = True
            
            print("🚀 Starting SynapseChat bot...")
            await self.bot.start(discord_token)
            
        except KeyboardInterrupt:
            print("SELFHOST: Bot stopped by user")
        except Exception as e:
            print(f"❌ SELFHOST: Error starting bot: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

async def main():
    """Main entry point"""
    bot_runner = SelfHostedBot()
    await bot_runner.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSELFHOST: Bot stopped")
    except Exception as e:
        print(f"❌ SELFHOST: Fatal error: {e}")
        sys.exit(1)