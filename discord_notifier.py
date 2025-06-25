"""
Discord Notifier - Self-Hosted Version
Handles Discord notifications and DM management
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

class DiscordNotifier:
    """Handles Discord notifications for self-hosted bot"""
    
    def __init__(self, bot=None, database_storage=None):
        self.bot = bot
        self.database = database_storage
        self.sent_notifications = set()
        self.notification_queue = []
        self.dm_cache = {}
        
        # Load persistent sent notifications
        self.load_sent_notifications()
    
    def load_sent_notifications(self):
        """Load sent notification IDs from database or file"""
        try:
            if self.database:
                # Try to load from database
                notifications = self.database.get_sent_dm_notifications()
                self.sent_notifications = set(notifications)
                print(f"DM_PERSIST: Loaded {len(self.sent_notifications)} sent notification IDs from database")
            else:
                # Fallback to file storage
                dm_file = Path("data/sent_notifications.json")
                if dm_file.exists():
                    with open(dm_file, 'r') as f:
                        data = json.load(f)
                        self.sent_notifications = set(data.get('sent_ids', []))
                        print(f"DM_PERSIST: Loaded {len(self.sent_notifications)} sent notification IDs from file")
        except Exception as e:
            print(f"DM_PERSIST: Error loading sent notifications: {e}")
            self.sent_notifications = set()
    
    def save_sent_notifications(self):
        """Save sent notification IDs to database or file"""
        try:
            if self.database:
                # Save to database
                self.database.save_sent_dm_notifications(list(self.sent_notifications))
            else:
                # Fallback to file storage
                Path("data").mkdir(exist_ok=True)
                dm_file = Path("data/sent_notifications.json")
                with open(dm_file, 'w') as f:
                    json.dump({
                        'sent_ids': list(self.sent_notifications),
                        'last_updated': datetime.now().isoformat()
                    }, f)
        except Exception as e:
            print(f"DM_PERSIST: Error saving sent notifications: {e}")
    
    async def send_dm(self, user_id: int, message: str, notification_id: str = None) -> bool:
        """Send direct message to user"""
        if not self.bot:
            return False
        
        # Generate notification ID if not provided
        if not notification_id:
            notification_id = f"dm_{user_id}_{int(datetime.now().timestamp())}"
        
        # Check if already sent
        if notification_id in self.sent_notifications:
            return False
        
        try:
            user = await self.bot.fetch_user(user_id)
            if user:
                await user.send(message)
                
                # Mark as sent
                self.sent_notifications.add(notification_id)
                self.save_sent_notifications()
                
                print(f"📨 DM sent to {user.name} ({user_id}): {notification_id}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to send DM to {user_id}: {e}")
            return False
        
        return False
    
    async def send_announcement(self, message: str, target_users: List[int] = None) -> Dict[str, Any]:
        """Send announcement to multiple users"""
        results = {
            'sent': 0,
            'failed': 0,
            'total': 0,
            'errors': []
        }
        
        if not target_users:
            return results
        
        results['total'] = len(target_users)
        
        for user_id in target_users:
            notification_id = f"announcement_{user_id}_{int(datetime.now().timestamp())}"
            
            if await self.send_dm(user_id, message, notification_id):
                results['sent'] += 1
            else:
                results['failed'] += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        print(f"📢 Announcement sent: {results['sent']}/{results['total']} successful")
        return results
    
    async def send_moderation_notice(self, user_id: int, action: str, reason: str = None) -> bool:
        """Send moderation notice to user"""
        if reason:
            message = f"You have received a {action} in SynapseChat for: {reason}"
        else:
            message = f"You have received a {action} in SynapseChat."
        
        notification_id = f"mod_{action}_{user_id}_{int(datetime.now().timestamp())}"
        return await self.send_dm(user_id, message, notification_id)
    
    async def send_system_alert(self, admin_users: List[int], alert: str) -> Dict[str, Any]:
        """Send system alert to administrators"""
        message = f"🚨 SynapseChat System Alert: {alert}"
        
        return await self.send_announcement(message, admin_users)
    
    async def queue_notification(self, user_id: int, message: str, delay_seconds: int = 0):
        """Queue notification for later delivery"""
        send_time = datetime.now() + timedelta(seconds=delay_seconds)
        
        self.notification_queue.append({
            'user_id': user_id,
            'message': message,
            'send_time': send_time,
            'notification_id': f"queued_{user_id}_{int(send_time.timestamp())}"
        })
        
        print(f"📋 Notification queued for {user_id} at {send_time}")
    
    async def process_notification_queue(self):
        """Process queued notifications"""
        current_time = datetime.now()
        processed = 0
        
        # Process due notifications
        pending = []
        for notification in self.notification_queue:
            if notification['send_time'] <= current_time:
                success = await self.send_dm(
                    notification['user_id'],
                    notification['message'],
                    notification['notification_id']
                )
                if success:
                    processed += 1
            else:
                pending.append(notification)
        
        # Update queue with pending notifications
        self.notification_queue = pending
        
        if processed > 0:
            print(f"📮 Processed {processed} queued notifications")
    
    async def start_queue_processor(self):
        """Start the notification queue processor"""
        while True:
            try:
                await self.process_notification_queue()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"❌ Error in notification queue processor: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def get_dm_stats(self) -> Dict[str, Any]:
        """Get DM notification statistics"""
        return {
            'total_sent': len(self.sent_notifications),
            'queued_notifications': len(self.notification_queue),
            'cache_size': len(self.dm_cache)
        }
    
    def cleanup_old_notifications(self, days: int = 30):
        """Clean up old notification records"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        # Clean sent notifications (keep format: "type_userid_timestamp")
        old_notifications = set()
        for notification_id in self.sent_notifications:
            try:
                parts = notification_id.split('_')
                if len(parts) >= 3:
                    timestamp = int(parts[-1])
                    if timestamp < cutoff_timestamp:
                        old_notifications.add(notification_id)
            except (ValueError, IndexError):
                continue
        
        # Remove old notifications
        self.sent_notifications -= old_notifications
        self.save_sent_notifications()
        
        print(f"🗑️ Cleaned up {len(old_notifications)} old notification records")

# Global instance
discord_notifier = None

def initialize_notifier(bot, database_storage=None):
    """Initialize the global notifier instance"""
    global discord_notifier
    discord_notifier = DiscordNotifier(bot, database_storage)
    return discord_notifier