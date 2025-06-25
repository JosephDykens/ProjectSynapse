#!/usr/bin/env python3
"""
SynapseChat Discord Bot - Production Version
Unified command processing with web panel integration
"""

import os
import json
import asyncio
import logging
import discord
from discord.ext import commands, tasks
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import secrets
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/synapsechat/bot.log'),
        logging.StreamHandler()
    ]
)

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

if not DISCORD_TOKEN or not DATABASE_URL:
    logging.error("Missing required environment variables")
    exit(1)

class CrossChatBot(commands.Bot):
    """Main Discord bot class with unified command processing"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.start_time = time.time()
        self.db_url = DATABASE_URL
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            return None
    
    async def setup_hook(self):
        """Setup bot components"""
        logging.info("Setting up bot components...")
        
        # Add slash commands
        self.add_slash_commands()
        
        # Start background tasks
        self.heartbeat_loop.start()
        self.process_web_commands.start()
        self.status_updater.start()
        
        logging.info("Bot setup complete")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logging.info(f"Bot logged in as {self.user}")
        logging.info(f"Connected to {len(self.guilds)} guilds")
        
        # Update bot status in database
        await self.update_bot_status("online")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logging.error(f"Failed to sync commands: {e}")
    
    async def update_bot_status(self, status):
        """Update bot status in database"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bot_status (status, last_update) 
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                status = EXCLUDED.status, 
                last_update = EXCLUDED.last_update
            """, (status, datetime.now()))
            conn.commit()
        except Exception as e:
            logging.error(f"Failed to update bot status: {e}")
        finally:
            conn.close()
    
    @tasks.loop(minutes=1)
    async def heartbeat_loop(self):
        """Heartbeat to track uptime"""
        await self.update_bot_status("online")
    
    @tasks.loop(seconds=5)
    async def process_web_commands(self):
        """Process commands from web panel with unified system"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, command_type, command_data, created_at
                FROM web_panel_commands 
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT 10
            """)
            commands = cursor.fetchall()
            
            for command in commands:
                try:
                    # Mark as processing
                    cursor.execute(
                        "UPDATE web_panel_commands SET status = 'processing' WHERE id = %s",
                        (command['id'],)
                    )
                    conn.commit()
                    
                    # Process command using unified system
                    await self.execute_unified_command(
                        command['command_type'],
                        json.loads(command['command_data']),
                        command['id']
                    )
                    
                    # Mark as completed
                    cursor.execute(
                        "UPDATE web_panel_commands SET status = 'completed', completed_at = %s WHERE id = %s",
                        (datetime.now(), command['id'])
                    )
                    conn.commit()
                    
                except Exception as e:
                    logging.error(f"Failed to process command {command['id']}: {e}")
                    cursor.execute(
                        "UPDATE web_panel_commands SET status = 'failed', error = %s WHERE id = %s",
                        (str(e), command['id'])
                    )
                    conn.commit()
        
        except Exception as e:
            logging.error(f"Error processing web commands: {e}")
        finally:
            conn.close()
    
    async def execute_unified_command(self, command_type, data, command_id=None):
        """Unified command execution for both slash commands and web panel"""
        try:
            if command_type == 'announcement':
                await self.send_crosschat_announcement(data['message'], data.get('anonymous', False))
            
            elif command_type == 'warn':
                await self.warn_user_unified(data['user_id'], data['reason'])
            
            elif command_type == 'ban':
                await self.ban_user_unified(data['user_id'], data.get('duration', 24), data['reason'])
            
            elif command_type == 'unban':
                await self.unban_user_unified(data['user_id'])
            
            else:
                logging.warning(f"Unknown command type: {command_type}")
        
        except Exception as e:
            logging.error(f"Unified command execution failed: {e}")
            raise
    
    async def send_crosschat_announcement(self, message, anonymous=False):
        """Send announcement to all crosschat channels"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id FROM crosschat_channels WHERE enabled = true")
            channels = cursor.fetchall()
            
            embed = discord.Embed(
                title="📢 Network Announcement",
                description=message,
                color=0x667eea,
                timestamp=datetime.now()
            )
            
            if not anonymous:
                embed.set_footer(text="SynapseChat Network")
            
            sent_count = 0
            for channel_data in channels:
                try:
                    channel = self.get_channel(int(channel_data['channel_id']))
                    if channel:
                        await channel.send(embed=embed)
                        sent_count += 1
                except Exception as e:
                    logging.error(f"Failed to send to channel {channel_data['channel_id']}: {e}")
            
            logging.info(f"Announcement sent to {sent_count} channels")
            
        except Exception as e:
            logging.error(f"Failed to send announcement: {e}")
        finally:
            conn.close()
    
    async def warn_user_unified(self, user_id, reason):
        """Unified user warning system"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Add warning to database
            cursor.execute("""
                INSERT INTO warnings (user_id, reason, timestamp, moderator)
                VALUES (%s, %s, %s, %s)
            """, (user_id, reason, datetime.now(), "Web Panel"))
            
            # Get warning count
            cursor.execute("SELECT COUNT(*) as count FROM warnings WHERE user_id = %s", (user_id,))
            warning_count = cursor.fetchone()['count']
            
            conn.commit()
            
            # Send DM to user
            try:
                user = await self.fetch_user(int(user_id))
                embed = discord.Embed(
                    title="⚠️ Warning Received",
                    description=f"**Reason:** {reason}\n**Warning #{warning_count}**",
                    color=0xffc107,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="SynapseChat Network")
                await user.send(embed=embed)
                
                # Log success
                cursor.execute("""
                    INSERT INTO chat_logs (user_id, username, content, timestamp, server_name, message_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, user.name, f"Warning sent: {reason}", datetime.now(), "DM", "warning"))
                conn.commit()
                
            except Exception as e:
                logging.error(f"Failed to send warning DM to {user_id}: {e}")
            
            logging.info(f"Warning issued to user {user_id}: {reason}")
            
        except Exception as e:
            logging.error(f"Failed to warn user {user_id}: {e}")
        finally:
            conn.close()
    
    async def ban_user_unified(self, user_id, duration_hours, reason):
        """Unified user ban system"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            
            # Add ban to database
            ban_until = datetime.now() + timedelta(hours=duration_hours)
            cursor.execute("""
                INSERT INTO user_bans (user_id, reason, banned_until, moderator, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                reason = EXCLUDED.reason,
                banned_until = EXCLUDED.banned_until,
                moderator = EXCLUDED.moderator,
                timestamp = EXCLUDED.timestamp
            """, (user_id, reason, ban_until, "Web Panel", datetime.now()))
            
            conn.commit()
            
            # Send DM to user
            try:
                user = await self.fetch_user(int(user_id))
                embed = discord.Embed(
                    title="🔨 Service Ban",
                    description=f"**Reason:** {reason}\n**Duration:** {duration_hours} hours\n**Until:** <t:{int(ban_until.timestamp())}:F>",
                    color=0xdc3545,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="SynapseChat Network")
                await user.send(embed=embed)
                
            except Exception as e:
                logging.error(f"Failed to send ban DM to {user_id}: {e}")
            
            logging.info(f"User {user_id} banned for {duration_hours} hours: {reason}")
            
        except Exception as e:
            logging.error(f"Failed to ban user {user_id}: {e}")
        finally:
            conn.close()
    
    async def unban_user_unified(self, user_id):
        """Unified user unban system"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_bans WHERE user_id = %s", (user_id,))
            conn.commit()
            
            # Send DM to user
            try:
                user = await self.fetch_user(int(user_id))
                embed = discord.Embed(
                    title="✅ Service Unban",
                    description="Your access to SynapseChat has been restored.",
                    color=0x28a745,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="SynapseChat Network")
                await user.send(embed=embed)
                
            except Exception as e:
                logging.error(f"Failed to send unban DM to {user_id}: {e}")
            
            logging.info(f"User {user_id} unbanned")
            
        except Exception as e:
            logging.error(f"Failed to unban user {user_id}: {e}")
        finally:
            conn.close()
    
    @tasks.loop(minutes=5)
    async def status_updater(self):
        """Update bot status and activity"""
        status_messages = [
            "Managing cross-chat network",
            f"Connected to {len(self.guilds)} servers",
            "Powered by SynapseChat",
            "Type /help for commands"
        ]
        
        try:
            message = secrets.choice(status_messages)
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=message
                ),
                status=discord.Status.online
            )
        except Exception as e:
            logging.error(f"Failed to update status: {e}")
    
    def add_slash_commands(self):
        """Add all slash commands using unified system"""
        
        @self.tree.command(name="announce", description="Send announcement to all crosschat channels")
        async def announce(interaction: discord.Interaction, message: str, anonymous: bool = False):
            if not await self.is_owner_or_admin(interaction):
                await interaction.response.send_message("❌ Insufficient permissions", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                # Use unified command system
                await self.execute_unified_command('announcement', {
                    'message': message,
                    'anonymous': anonymous
                })
                
                await interaction.followup.send("✅ Announcement sent successfully!", ephemeral=True)
                
            except Exception as e:
                logging.error(f"Announce command failed: {e}")
                await interaction.followup.send("❌ Failed to send announcement", ephemeral=True)
        
        @self.tree.command(name="warn", description="Warn a user")
        async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
            if not await self.is_owner_or_admin(interaction):
                await interaction.response.send_message("❌ Insufficient permissions", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                # Use unified command system
                await self.execute_unified_command('warn', {
                    'user_id': str(user.id),
                    'reason': reason
                })
                
                await interaction.followup.send(f"✅ Warning sent to {user.mention}", ephemeral=True)
                
            except Exception as e:
                logging.error(f"Warn command failed: {e}")
                await interaction.followup.send("❌ Failed to send warning", ephemeral=True)
        
        @self.tree.command(name="ban", description="Ban a user from crosschat service")
        async def ban(interaction: discord.Interaction, user: discord.Member, duration: int = 24, reason: str = "No reason provided"):
            # Only bot owner can use ban command
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ Only authorized staff can use ban commands", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                # Use unified command system
                await self.execute_unified_command('ban', {
                    'user_id': str(user.id),
                    'duration': duration,
                    'reason': reason
                })
                
                await interaction.followup.send(f"✅ User {user.mention} banned for {duration} hours", ephemeral=True)
                
            except Exception as e:
                logging.error(f"Ban command failed: {e}")
                await interaction.followup.send("❌ Failed to ban user", ephemeral=True)
        
        @self.tree.command(name="unban", description="Unban a user from crosschat service")
        async def unban(interaction: discord.Interaction, user_id: str):
            # Only bot owner can use unban command
            if interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ Only authorized staff can use ban commands", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            try:
                # Use unified command system
                await self.execute_unified_command('unban', {
                    'user_id': user_id
                })
                
                await interaction.followup.send(f"✅ User <@{user_id}> unbanned", ephemeral=True)
                
            except Exception as e:
                logging.error(f"Unban command failed: {e}")
                await interaction.followup.send("❌ Failed to unban user", ephemeral=True)
        
        @self.tree.command(name="status", description="Show bot status")
        async def status(interaction: discord.Interaction):
            uptime = int(time.time() - self.start_time)
            
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=0x28a745,
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="Online ✅", inline=True)
            embed.add_field(name="Uptime", value=f"{uptime // 3600}h {(uptime % 3600) // 60}m", inline=True)
            embed.add_field(name="Servers", value=len(self.guilds), inline=True)
            embed.add_field(name="Latency", value=f"{round(self.latency * 1000)}ms", inline=True)
            
            await interaction.response.send_message(embed=embed)
        
        @self.tree.command(name="setup", description="Setup crosschat channel")
        async def setup(interaction: discord.Interaction, action: str, channel: discord.TextChannel = None):
            if not await self.is_server_admin(interaction):
                await interaction.response.send_message("❌ Administrator permission required", ephemeral=True)
                return
            
            if action.lower() == "enable":
                if not channel:
                    await interaction.response.send_message("❌ Channel parameter required for enable", ephemeral=True)
                    return
                
                conn = self.get_db_connection()
                if not conn:
                    await interaction.response.send_message("❌ Database connection failed", ephemeral=True)
                    return
                
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO crosschat_channels (channel_id, guild_id, enabled)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (channel_id) DO UPDATE SET enabled = true
                    """, (str(channel.id), str(interaction.guild.id), True))
                    conn.commit()
                    
                    await interaction.response.send_message(f"✅ Crosschat enabled for {channel.mention}")
                    
                except Exception as e:
                    logging.error(f"Setup enable failed: {e}")
                    await interaction.response.send_message("❌ Failed to enable crosschat", ephemeral=True)
                finally:
                    conn.close()
            
            elif action.lower() == "disable":
                conn = self.get_db_connection()
                if not conn:
                    await interaction.response.send_message("❌ Database connection failed", ephemeral=True)
                    return
                
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE crosschat_channels SET enabled = false WHERE guild_id = %s",
                        (str(interaction.guild.id),)
                    )
                    conn.commit()
                    
                    await interaction.response.send_message("✅ Crosschat disabled for this server")
                    
                except Exception as e:
                    logging.error(f"Setup disable failed: {e}")
                    await interaction.response.send_message("❌ Failed to disable crosschat", ephemeral=True)
                finally:
                    conn.close()
    
    async def is_owner_or_admin(self, interaction):
        """Check if user is bot owner or server admin"""
        return (
            interaction.user.id == OWNER_ID or
            interaction.user.guild_permissions.administrator
        )
    
    async def is_server_admin(self, interaction):
        """Check if user is server administrator"""
        return interaction.user.guild_permissions.administrator
    
    async def on_message(self, message):
        """Handle crosschat messages with full feature support"""
        if message.author.bot or not message.guild:
            return
        
        # Skip commands
        if message.content.startswith('/'):
            return
        
        # Check if message is in crosschat channel
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT enabled FROM crosschat_channels WHERE channel_id = %s",
                (str(message.channel.id),)
            )
            channel_data = cursor.fetchone()
            
            if not channel_data or not channel_data['enabled']:
                return
            
            # Check if user is banned
            cursor.execute(
                "SELECT banned_until FROM user_bans WHERE user_id = %s",
                (str(message.author.id),)
            )
            ban_data = cursor.fetchone()
            
            if ban_data and ban_data['banned_until'] > datetime.now():
                await message.delete()
                try:
                    await message.author.send("You are currently banned from CrossChat.")
                except:
                    pass
                return
            
            # Don't forward empty messages
            if not message.content.strip() and not message.attachments:
                return
            
            # Log message
            cursor.execute("""
                INSERT INTO chat_logs (user_id, username, content, timestamp, server_name, message_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                str(message.author.id),
                message.author.name,
                message.content or "[Attachment]",
                datetime.now(),
                message.guild.name,
                "crosschat"
            ))
            
            # Get all other crosschat channels
            cursor.execute(
                "SELECT channel_id FROM crosschat_channels WHERE enabled = true AND channel_id != %s",
                (str(message.channel.id),)
            )
            other_channels = cursor.fetchall()
            
            if not other_channels:
                return
            
            # Create embed for crosschat message
            embed = discord.Embed(
                description=message.content or "*[Attachment only]*",
                color=0x667eea,
                timestamp=message.created_at
            )
            
            # Set author with server name
            embed.set_author(
                name=f"{message.author.display_name} • {message.guild.name}",
                icon_url=message.author.display_avatar.url
            )
            
            # Add attachment info if present
            if message.attachments:
                attachment_text = "\n".join([f"📎 [{att.filename}]({att.url})" for att in message.attachments[:3]])
                if len(message.attachments) > 3:
                    attachment_text += f"\n*... and {len(message.attachments) - 3} more attachments*"
                embed.add_field(name="Attachments", value=attachment_text, inline=False)
            
            # Add reply info if message is a reply
            if message.reference and message.reference.message_id:
                try:
                    replied_msg = await message.channel.fetch_message(message.reference.message_id)
                    reply_content = replied_msg.content[:100] + "..." if len(replied_msg.content) > 100 else replied_msg.content
                    embed.add_field(
                        name=f"↳ Replying to {replied_msg.author.display_name}",
                        value=reply_content or "*[Attachment or embed]*",
                        inline=False
                    )
                except:
                    pass
            
            # Forward to all other crosschat channels
            successful_forwards = 0
            for channel_data in other_channels:
                try:
                    target_channel = self.get_channel(int(channel_data['channel_id']))
                    if target_channel and hasattr(target_channel, 'send'):
                        await target_channel.send(embed=embed)
                        successful_forwards += 1
                except Exception as e:
                    logging.error(f"Failed to forward to channel {channel_data['channel_id']}: {e}")
            
            # Update statistics
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value) 
                VALUES ('total_crosschat_messages', '1')
                ON CONFLICT (config_key) 
                DO UPDATE SET config_value = (CAST(system_config.config_value AS INTEGER) + 1)::TEXT
            """)
            
            conn.commit()
            logging.info(f"Crosschat: Forwarded message from {message.author.name} to {successful_forwards} channels")
            
        except Exception as e:
            logging.error(f"Error processing crosschat message: {e}")
        finally:
            conn.close()
    
    async def get_crosschat_stats(self):
        """Get crosschat statistics"""
        conn = self.get_db_connection()
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            # Get total channels
            cursor.execute("SELECT COUNT(*) FROM crosschat_channels WHERE enabled = true")
            total_channels = cursor.fetchone()[0]
            
            # Get total messages today
            cursor.execute("""
                SELECT COUNT(*) FROM chat_logs 
                WHERE message_type = 'crosschat' AND DATE(timestamp) = CURRENT_DATE
            """)
            messages_today = cursor.fetchone()[0]
            
            # Get total servers
            cursor.execute("SELECT COUNT(DISTINCT guild_id) FROM crosschat_channels WHERE enabled = true")
            total_servers = cursor.fetchone()[0]
            
            return {
                'channels': total_channels,
                'messages_today': messages_today,
                'servers': total_servers
            }
            
        except Exception as e:
            logging.error(f"Error getting crosschat stats: {e}")
            return {}
        finally:
            conn.close()

async def main():
    """Main bot startup"""
    bot = CrossChatBot()
    
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())