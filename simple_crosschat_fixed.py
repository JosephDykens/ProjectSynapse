"""
Simple CrossChat System with Database Error Handling
Gracefully handles database unavailability
"""

import discord
from typing import Dict, List, Optional
from database_handler import db_handler

class SimpleCrossChat:
    """Simplified cross-chat system with database error handling"""
    
    def __init__(self, bot):
        self.bot = bot
        self.channels = {}  # In-memory fallback
        
    def get_crosschat_channels(self) -> Dict[str, Dict]:
        """Get crosschat channels from database or fallback"""
        if not db_handler.is_available():
            return self.channels
            
        try:
            result = db_handler.execute_query("""
                SELECT channel_id, guild_id, guild_name, channel_name 
                FROM crosschat_channels 
                WHERE is_active = true
            """)
            
            if result:
                channels = {}
                for row in result:
                    channels[str(row[0])] = {
                        'guild_id': str(row[1]),
                        'guild_name': row[2],
                        'channel_name': row[3]
                    }
                return channels
            else:
                return self.channels
                
        except Exception as e:
            print(f"Error getting crosschat channels: {e}")
            return self.channels
    
    def add_channel(self, channel_id: str, guild_id: str, guild_name: str, channel_name: str) -> bool:
        """Add channel to crosschat"""
        # Add to memory first
        self.channels[channel_id] = {
            'guild_id': guild_id,
            'guild_name': guild_name,
            'channel_name': channel_name
        }
        
        # Try to add to database
        if db_handler.is_available():
            try:
                db_handler.execute_query("""
                    INSERT INTO crosschat_channels (channel_id, guild_id, guild_name, channel_name, is_active)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (channel_id) DO UPDATE SET
                    guild_name = EXCLUDED.guild_name,
                    channel_name = EXCLUDED.channel_name,
                    is_active = true
                """, (channel_id, guild_id, guild_name, channel_name))
                return True
            except Exception as e:
                print(f"Error adding channel to database: {e}")
        
        return True  # Still return True since we added to memory
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove channel from crosschat"""
        # Remove from memory
        if channel_id in self.channels:
            del self.channels[channel_id]
        
        # Try to remove from database
        if db_handler.is_available():
            try:
                db_handler.execute_query("""
                    UPDATE crosschat_channels 
                    SET is_active = false 
                    WHERE channel_id = %s
                """, (channel_id,))
            except Exception as e:
                print(f"Error removing channel from database: {e}")
        
        return True
    
    async def send_to_crosschat(self, message, exclude_channel_id=None) -> int:
        """Send message to all crosschat channels"""
        channels = self.get_crosschat_channels()
        sent_count = 0
        
        for channel_id, channel_info in channels.items():
            if channel_id == exclude_channel_id:
                continue
                
            try:
                channel = self.bot.get_channel(int(channel_id))
                if channel:
                    # Create embed for crosschat message
                    embed = discord.Embed(
                        description=message.content,
                        color=0x7289DA
                    )
                    embed.set_author(
                        name=f"{message.author.display_name} • {message.guild.name}",
                        icon_url=message.author.display_avatar.url
                    )
                    
                    await channel.send(embed=embed)
                    sent_count += 1
                    
            except Exception as e:
                print(f"Error sending to channel {channel_id}: {e}")
        
        # Log to database if available
        if db_handler.is_available():
            try:
                db_handler.execute_query("""
                    INSERT INTO crosschat_messages (message_id, user_id, username, content, guild_id, channel_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (str(message.id), str(message.author.id), message.author.display_name, 
                     message.content, str(message.guild.id), str(message.channel.id)))
            except Exception as e:
                print(f"Error logging crosschat message: {e}")
        
        return sent_count
    
    def is_crosschat_channel(self, channel_id: str) -> bool:
        """Check if channel is a crosschat channel"""
        channels = self.get_crosschat_channels()
        return channel_id in channels