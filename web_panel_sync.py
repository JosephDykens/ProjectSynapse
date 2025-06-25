#!/usr/bin/env python3
"""
Web Panel Synchronization Module
Ensures real-time synchronization between self-hosted bot and web panel
"""

import os
import asyncio
import json
import time
import aiohttp
from datetime import datetime
from mongodb_handler import mongo_handler

class WebPanelSync:
    def __init__(self, bot):
        self.bot = bot
        # Using MongoDB handler instead of PostgreSQL
        # self.database_storage = DatabaseStorage()
        self.panel_url = os.getenv('WEB_PANEL_URL', '')
        self.sync_interval = 5  # seconds
        self.last_sync = 0
        self.sync_task = None
        
    async def start_sync(self):
        """Start the synchronization loop"""
        if self.sync_task and not self.sync_task.done():
            return
        
        self.sync_task = asyncio.create_task(self._sync_loop())
        print("✅ Web panel synchronization started")
    
    async def stop_sync(self):
        """Stop the synchronization loop"""
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        print("🛑 Web panel synchronization stopped")
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while True:
            try:
                await self._perform_sync()
                await asyncio.sleep(self.sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"SYNC_ERROR: {e}")
                await asyncio.sleep(self.sync_interval * 2)  # Back off on error
    
    async def _perform_sync(self):
        """Perform one synchronization cycle"""
        current_time = time.time()
        
        # Update bot status in database
        await self._update_bot_status()
        
        # Process pending commands from web panel
        await self._process_web_commands()
        
        # Sync configuration changes
        await self._sync_configuration()
        
        # Update statistics
        await self._update_statistics()
        
        self.last_sync = current_time
    
    async def _update_bot_status(self):
        """Update bot status in database for web panel"""
        try:
            status_data = {
                'bot_status': 'online' if self.bot.is_ready() else 'starting',
                'guilds_connected': len(self.bot.guilds),
                'channels_active': len(self._get_crosschat_channels()),
                'latency': round(self.bot.latency * 1000),
                'uptime': self._calculate_uptime(),
                'last_heartbeat': datetime.now().isoformat(),
                'process_id': os.getpid()
            }
            
            # Store in database for web panel to read
            conn = self.database_storage.get_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO bot_status (data, updated_at) 
                            VALUES (%s, NOW())
                            ON CONFLICT (id) DO UPDATE SET 
                            data = EXCLUDED.data, 
                            updated_at = EXCLUDED.updated_at
                        """, (json.dumps(status_data),))
                        conn.commit()
                finally:
                    self.database_storage.return_connection(conn)
                    
        except Exception as e:
            print(f"STATUS_UPDATE_ERROR: {e}")
    
    async def _process_web_commands(self):
        """Process commands queued from web panel"""
        try:
            conn = self.database_storage.get_connection()
            if not conn:
                return
            
            try:
                with conn.cursor() as cursor:
                    # Get pending commands
                    cursor.execute("""
                        SELECT id, command_type, command_data, created_at
                        FROM command_queue 
                        WHERE status = 'pending' AND processed_by IS NULL
                        ORDER BY created_at ASC
                        LIMIT 10
                    """)
                    
                    commands = cursor.fetchall()
                    
                    for cmd in commands:
                        cmd_id, cmd_type, cmd_data, created_at = cmd
                        
                        # Mark as processing
                        cursor.execute("""
                            UPDATE command_queue 
                            SET status = 'processing', processed_by = %s, processed_at = NOW()
                            WHERE id = %s
                        """, (f"bot_{os.getpid()}", cmd_id))
                        conn.commit()
                        
                        # Execute command
                        success = await self._execute_web_command(cmd_type, cmd_data)
                        
                        # Update status
                        final_status = 'completed' if success else 'failed'
                        cursor.execute("""
                            UPDATE command_queue 
                            SET status = %s, completed_at = NOW()
                            WHERE id = %s
                        """, (final_status, cmd_id))
                        conn.commit()
                        
                        print(f"WEB_CMD: Processed {cmd_type} (ID: {cmd_id}) - {final_status}")
                        
            finally:
                self.database_storage.return_connection(conn)
                
        except Exception as e:
            print(f"WEB_CMD_ERROR: {e}")
    
    async def _execute_web_command(self, cmd_type, cmd_data):
        """Execute a command from the web panel"""
        try:
            data = json.loads(cmd_data) if isinstance(cmd_data, str) else cmd_data
            
            if cmd_type == 'system_enable':
                return await self._handle_system_enable(data)
            elif cmd_type == 'system_disable':
                return await self._handle_system_disable(data)
            elif cmd_type == 'announcement':
                return await self._handle_announcement(data)
            elif cmd_type == 'user_ban':
                return await self._handle_user_ban(data)
            elif cmd_type == 'user_unban':
                return await self._handle_user_unban(data)
            elif cmd_type == 'channel_add':
                return await self._handle_channel_management(data, 'add')
            elif cmd_type == 'channel_remove':
                return await self._handle_channel_management(data, 'remove')
            elif cmd_type == 'presence_update':
                return await self._handle_presence_update(data)
            else:
                print(f"UNKNOWN_CMD: {cmd_type}")
                return False
                
        except Exception as e:
            print(f"CMD_EXEC_ERROR: {e}")
            return False
    
    async def _handle_system_enable(self, data):
        """Handle system enable command from web panel"""
        try:
            system = data.get('system')
            if system == 'crosschat':
                self.bot.cross_chat_manager.enabled = True
                print("SYNC: CrossChat enabled via web panel")
                return True
            elif system == 'automod':
                self.bot.auto_moderation.enabled = True
                print("SYNC: AutoMod enabled via web panel")
                return True
            return False
        except Exception as e:
            print(f"SYSTEM_ENABLE_ERROR: {e}")
            return False
    
    async def _handle_system_disable(self, data):
        """Handle system disable command from web panel"""
        try:
            system = data.get('system')
            if system == 'crosschat':
                self.bot.cross_chat_manager.enabled = False
                print("SYNC: CrossChat disabled via web panel")
                return True
            elif system == 'automod':
                self.bot.auto_moderation.enabled = False
                print("SYNC: AutoMod disabled via web panel")
                return True
            return False
        except Exception as e:
            print(f"SYSTEM_DISABLE_ERROR: {e}")
            return False
    
    async def _handle_announcement(self, data):
        """Handle announcement command from web panel"""
        try:
            message = data.get('message', '')
            if not message:
                return False
            
            # Send announcement through CrossChat
            channels = self._get_crosschat_channels()
            success_count = 0
            
            for channel in channels:
                try:
                    discord_channel = self.bot.get_channel(int(channel['channel_id']))
                    if discord_channel:
                        embed = discord.Embed(
                            title="📢 System Announcement",
                            description=message,
                            color=0x00ff00,
                            timestamp=datetime.utcnow()
                        )
                        embed.set_footer(text="SynapseChat System")
                        await discord_channel.send(embed=embed)
                        success_count += 1
                except Exception as e:
                    print(f"ANNOUNCE_ERROR in {channel['channel_id']}: {e}")
            
            print(f"SYNC: Announcement sent to {success_count} channels")
            return success_count > 0
            
        except Exception as e:
            print(f"ANNOUNCEMENT_ERROR: {e}")
            return False
    
    async def _handle_user_ban(self, data):
        """Handle user ban command from web panel"""
        try:
            user_id = data.get('user_id')
            reason = data.get('reason', 'Banned via web panel')
            
            if not user_id:
                return False
            
            # Store ban in database (already handled by web panel, just acknowledge)
            print(f"SYNC: User {user_id} banned - {reason}")
            return True
            
        except Exception as e:
            print(f"USER_BAN_ERROR: {e}")
            return False
    
    async def _handle_user_unban(self, data):
        """Handle user unban command from web panel"""
        try:
            user_id = data.get('user_id')
            
            if not user_id:
                return False
            
            # Remove ban from database (already handled by web panel, just acknowledge)
            print(f"SYNC: User {user_id} unbanned")
            return True
            
        except Exception as e:
            print(f"USER_UNBAN_ERROR: {e}")
            return False
    
    async def _handle_channel_management(self, data, action):
        """Handle channel add/remove commands from web panel"""
        try:
            channel_id = data.get('channel_id')
            guild_id = data.get('guild_id')
            
            if not channel_id:
                return False
            
            if action == 'add':
                # Channel addition is handled by database storage
                print(f"SYNC: Channel {channel_id} added to CrossChat")
                return True
            elif action == 'remove':
                # Channel removal is handled by database storage
                print(f"SYNC: Channel {channel_id} removed from CrossChat")
                return True
            
            return False
            
        except Exception as e:
            print(f"CHANNEL_MGMT_ERROR: {e}")
            return False
    
    async def _handle_presence_update(self, data):
        """Handle bot presence update from web panel"""
        try:
            import discord
            
            status_str = data.get('status', 'online')
            activity_type = data.get('activity_type', 'watching')
            activity_text = data.get('activity_text', 'Cross-Server Chat')
            
            # Convert status string to Discord status
            status = getattr(discord.Status, status_str, discord.Status.online)
            
            # Create activity
            if activity_type == 'playing':
                activity = discord.Game(name=activity_text)
            elif activity_type == 'streaming':
                activity = discord.Streaming(name=activity_text, url="https://twitch.tv/synapsechat")
            elif activity_type == 'listening':
                activity = discord.Activity(type=discord.ActivityType.listening, name=activity_text)
            else:  # watching
                activity = discord.Activity(type=discord.ActivityType.watching, name=activity_text)
            
            await self.bot.change_presence(status=status, activity=activity)
            print(f"SYNC: Presence updated - {status_str} {activity_type} {activity_text}")
            return True
            
        except Exception as e:
            print(f"PRESENCE_ERROR: {e}")
            return False
    
    async def _sync_configuration(self):
        """Sync configuration changes from web panel"""
        try:
            conn = self.database_storage.get_connection()
            if not conn:
                return
            
            try:
                with conn.cursor() as cursor:
                    # Check for configuration updates
                    cursor.execute("""
                        SELECT config_key, config_value, updated_at
                        FROM system_config 
                        WHERE updated_at > %s
                    """, (datetime.fromtimestamp(self.last_sync),))
                    
                    updates = cursor.fetchall()
                    
                    for config_key, config_value, updated_at in updates:
                        await self._apply_config_update(config_key, config_value)
                        
            finally:
                self.database_storage.return_connection(conn)
                
        except Exception as e:
            print(f"CONFIG_SYNC_ERROR: {e}")
    
    async def _apply_config_update(self, key, value):
        """Apply a configuration update"""
        try:
            if key == 'crosschat_enabled':
                self.bot.cross_chat_manager.enabled = bool(value)
            elif key == 'automod_enabled':
                self.bot.auto_moderation.enabled = bool(value)
            elif key == 'max_message_length':
                # Update message length limit if needed
                pass
            
            print(f"CONFIG_UPDATE: {key} = {value}")
            
        except Exception as e:
            print(f"CONFIG_APPLY_ERROR: {e}")
    
    async def _update_statistics(self):
        """Update statistics in database"""
        try:
            # Get message counts and other stats
            conn = self.database_storage.get_connection()
            if not conn:
                return
            
            try:
                with conn.cursor() as cursor:
                    # Update bot statistics
                    stats = {
                        'guilds_connected': len(self.bot.guilds),
                        'channels_active': len(self._get_crosschat_channels()),
                        'uptime_seconds': self._calculate_uptime_seconds(),
                        'latency_ms': round(self.bot.latency * 1000),
                        'last_update': datetime.now().isoformat()
                    }
                    
                    cursor.execute("""
                        INSERT INTO bot_statistics (data, updated_at)
                        VALUES (%s, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                        data = EXCLUDED.data,
                        updated_at = EXCLUDED.updated_at
                    """, (json.dumps(stats),))
                    conn.commit()
                    
            finally:
                self.database_storage.return_connection(conn)
                
        except Exception as e:
            print(f"STATS_UPDATE_ERROR: {e}")
    
    def _get_crosschat_channels(self):
        """Get list of active CrossChat channels"""
        try:
            return self.database_storage.get_crosschat_channels()
        except:
            return []
    
    def _calculate_uptime(self):
        """Calculate bot uptime string"""
        uptime_seconds = self._calculate_uptime_seconds()
        
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _calculate_uptime_seconds(self):
        """Calculate bot uptime in seconds"""
        return int((datetime.utcnow() - self.bot.start_time).total_seconds())

# Global sync instance
web_panel_sync = None

def get_sync_instance(bot=None):
    """Get or create the web panel sync instance"""
    global web_panel_sync
    if web_panel_sync is None and bot:
        web_panel_sync = WebPanelSync(bot)
    return web_panel_sync