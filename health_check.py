#!/usr/bin/env python3
"""
SynapseChat Bot Health Check
Verifies bot status and database connectivity
"""

import os
import sys
import time
import psutil
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class HealthChecker:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.discord_token = os.getenv('DISCORD_TOKEN')
        
    def check_environment(self):
        """Check required environment variables"""
        print("🔧 Checking environment configuration...")
        
        issues = []
        
        if not self.discord_token:
            issues.append("❌ DISCORD_TOKEN not set")
        elif len(self.discord_token) < 50:
            issues.append("❌ DISCORD_TOKEN appears invalid (too short)")
        else:
            print(f"✅ Discord token configured ({len(self.discord_token)} characters)")
        
        if not self.database_url:
            issues.append("❌ DATABASE_URL not set")
        else:
            print("✅ Database URL configured")
        
        return issues
    
    def check_database_connection(self):
        """Test database connectivity"""
        print("🗄️ Testing database connection...")
        
        if not self.database_url:
            return ["❌ Database URL not configured"]
        
        try:
            conn = psycopg2.connect(self.database_url, connect_timeout=10)
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result[0] != 1:
                return ["❌ Database query test failed"]
            
            # Check required tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('chat_logs', 'crosschat_channels', 'banned_users')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            required_tables = ['chat_logs', 'crosschat_channels', 'banned_users']
            missing_tables = [t for t in required_tables if t not in tables]
            
            cursor.close()
            conn.close()
            
            if missing_tables:
                return [f"❌ Missing database tables: {', '.join(missing_tables)}"]
            
            print("✅ Database connection successful")
            print("✅ Required tables present")
            return []
            
        except psycopg2.OperationalError as e:
            return [f"❌ Database connection failed: {e}"]
        except Exception as e:
            return [f"❌ Database error: {e}"]
    
    def check_bot_process(self):
        """Check if bot process is running"""
        print("🤖 Checking bot process...")
        
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if 'python' in proc.info['name'] and proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline'])
                    if 'run_bot.py' in cmdline_str or 'bot.py' in cmdline_str:
                        create_time = datetime.fromtimestamp(proc.info['create_time'])
                        uptime = datetime.now() - create_time
                        bot_processes.append({
                            'pid': proc.info['pid'],
                            'uptime': str(uptime).split('.')[0],
                            'cmdline': cmdline_str
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if not bot_processes:
            return ["❌ No bot process found"]
        
        if len(bot_processes) > 1:
            print(f"⚠️  Multiple bot processes detected ({len(bot_processes)})")
            for proc in bot_processes:
                print(f"   PID: {proc['pid']}, Uptime: {proc['uptime']}")
        else:
            proc = bot_processes[0]
            print(f"✅ Bot process running (PID: {proc['pid']}, Uptime: {proc['uptime']})")
        
        return []
    
    def check_system_resources(self):
        """Check system resource usage"""
        print("💻 Checking system resources...")
        
        issues = []
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent > 90:
            issues.append(f"❌ High memory usage: {memory_percent:.1f}%")
        elif memory_percent > 80:
            print(f"⚠️  High memory usage: {memory_percent:.1f}%")
        else:
            print(f"✅ Memory usage: {memory_percent:.1f}%")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        if disk_percent > 95:
            issues.append(f"❌ Critical disk usage: {disk_percent:.1f}%")
        elif disk_percent > 85:
            print(f"⚠️  High disk usage: {disk_percent:.1f}%")
        else:
            print(f"✅ Disk usage: {disk_percent:.1f}%")
        
        # CPU load
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 95:
            issues.append(f"❌ High CPU usage: {cpu_percent:.1f}%")
        elif cpu_percent > 80:
            print(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
        else:
            print(f"✅ CPU usage: {cpu_percent:.1f}%")
        
        return issues
    
    def check_log_files(self):
        """Check log file status"""
        print("📝 Checking log files...")
        
        issues = []
        log_dir = "logs"
        
        if not os.path.exists(log_dir):
            issues.append("❌ Logs directory not found")
            return issues
        
        log_files = os.listdir(log_dir)
        if not log_files:
            print("⚠️  No log files found")
        else:
            print(f"✅ Found {len(log_files)} log files")
            
            # Check recent activity
            recent_logs = []
            for log_file in log_files:
                log_path = os.path.join(log_dir, log_file)
                if os.path.isfile(log_path):
                    mtime = os.path.getmtime(log_path)
                    age = time.time() - mtime
                    if age < 3600:  # Modified within last hour
                        recent_logs.append(log_file)
            
            if recent_logs:
                print(f"✅ {len(recent_logs)} recently updated log files")
            else:
                print("⚠️  No recent log activity")
        
        return issues
    
    def run_full_check(self):
        """Run complete health check"""
        print("🏥 SynapseChat Bot Health Check")
        print("=" * 50)
        
        all_issues = []
        
        # Environment check
        all_issues.extend(self.check_environment())
        print()
        
        # Database check
        all_issues.extend(self.check_database_connection())
        print()
        
        # Process check
        all_issues.extend(self.check_bot_process())
        print()
        
        # System resources
        all_issues.extend(self.check_system_resources())
        print()
        
        # Log files
        all_issues.extend(self.check_log_files())
        print()
        
        # Summary
        print("=" * 50)
        if not all_issues:
            print("🎉 All health checks passed!")
            return 0
        else:
            print(f"⚠️  Found {len(all_issues)} issues:")
            for issue in all_issues:
                print(f"   {issue}")
            return 1

def main():
    """Main entry point"""
    checker = HealthChecker()
    exit_code = checker.run_full_check()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()