"""
Simple Cross-Chat Implementation
Direct approach - one message in, one embed per channel out
"""

import asyncio
import discord
from datetime import datetime
import time
import random
import string
import json
import os
import io
# Database import removed - using MongoDB handler from bot instance

class SimpleCrossChat:
    """Simple cross-chat with no complexity - ABSOLUTE SINGLETON"""
    
    # Class-level singleton instance and global locks
    _instance = None
    _global_processing_lock = set()
    _handler_registered = False
    _global_processed_messages = set()
    _duplicate_prevention_cache = set()
    _global_message_ids = set()  # Global tracking of ALL processed message IDs
    _global_send_locks = {}  # Class-level send locks to prevent Discord API duplication
    _global_cc_id_mapping = {}  # Global CC-ID mapping to prevent duplicate ID generation
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        return cls._instance
    
    def __new__(cls, bot):
        # ABSOLUTE singleton enforcement - only one instance ever
        if cls._instance is not None:
            print(f"SINGLETON_REJECT: SimpleCrossChat instance already exists, returning existing")
            return cls._instance
            
        print(f"SINGLETON_CREATE: Creating the ONLY SimpleCrossChat instance")
        cls._instance = super(SimpleCrossChat, cls).__new__(cls)
        cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, bot):
        # Only initialize once
        if self._initialized:
            print(f"SIMPLE_SINGLETON: Instance already initialized, skipping")
            return
            
        print(f"SIMPLE_SINGLETON: Initializing the singleton instance")
        self.bot = bot
        self.processed = self._load_processed_messages()
        self.cc_id_mapping = {}  # message_id -> cc_id
        self.cc_id_reverse = {}  # cc_id -> message_id
        self.message_mappings = {}  # message_id -> list of sent message objects
        self.currently_processing = set()
        # VIP processing queues
        self.vip_queue = asyncio.Queue()
        self.standard_queue = asyncio.Queue()
        self._initialized = True
        print(f"SIMPLE_SINGLETON: Initialization complete")

    async def is_support_vip(self, user_id):
        """Check if user has VIP role (VIP_ROLE_ID or VIP_ROLE_ID2) in the SynapseChat Support server"""
        try:
            import os
            
            # Use SYNAPSECHAT_GUILD_ID for the Support server and check both VIP role IDs
            support_server_id = os.getenv('SYNAPSECHAT_GUILD_ID')
            vip_role_id = os.getenv('VIP_ROLE_ID')
            vip_role_id2 = os.getenv('VIP_ROLE_ID2')
            
            if not support_server_id:
                print(f"VIP_CHECK: SYNAPSECHAT_GUILD_ID not set")
                return False
                
            if not vip_role_id and not vip_role_id2:
                print(f"VIP_CHECK: Neither VIP_ROLE_ID nor VIP_ROLE_ID2 are set")
                return False
            
            # Get the support server
            support_guild = self.bot.get_guild(int(support_server_id))
            if not support_guild:
                print(f"VIP_CHECK: SynapseChat guild {support_server_id} not found")
                return False
                
            # Get the member in support server
            member = support_guild.get_member(user_id)
            if not member:
                return False
                
            # Check for VIP_ROLE_ID (SynapseChat Architect)
            if vip_role_id:
                vip_role = support_guild.get_role(int(vip_role_id))
                if vip_role and vip_role in member.roles:
                    print(f"VIP_CHECK: {member.display_name} has VIP role ({vip_role.name}) in {support_guild.name}")
                    return True
            
            # Check for VIP_ROLE_ID2 (SynapseChat Elite)
            if vip_role_id2:
                vip_role2 = support_guild.get_role(int(vip_role_id2))
                if vip_role2 and vip_role2 in member.roles:
                    print(f"VIP_CHECK: {member.display_name} has Elite VIP role ({vip_role2.name}) in {support_guild.name}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"VIP_CHECK: Error checking VIP status for {user_id}: {e}")
            return False

    # REMOVED: on_message event handler to prevent duplicate processing
    # All message processing now handled through bot.py event system only

    async def get_system_config(self):
        """Get system configuration for CrossChat and AutoMod status"""
        try:
            # Default to enabled - no database dependency for config
            return {
                'cross_chat_enabled': True,
                'auto_moderation_enabled': True
            }
        except Exception as e:
            print(f"SIMPLE_CONFIG: Error reading system config: {e}")
            # Default to enabled if config can't be read
            return {
                'cross_chat_enabled': True,
                'auto_moderation_enabled': True
            }

    def _load_processed_messages(self):
        """Load processed message IDs from memory"""
        try:
            # Use in-memory tracking only - no database dependency
            return set()
        except Exception as e:
            print(f"SIMPLE: Error loading processed messages: {e}")
        return set()
    
    def _save_processed_messages(self):
        """Save processed message IDs to memory"""
        try:
            # Keep only recent messages (last 1000) to prevent memory from growing too large
            if len(self.processed) > 1000:
                self.processed = set(list(self.processed)[-1000:])
        except Exception as e:
            print(f"SIMPLE: Error saving processed messages: {e}")
    
    def generate_cc_id(self, message_id, is_vip=False, message=None):
        """Generate unique CC-ID with VIP FAST-TRACK processing"""
        import time, random, string
        
        # VIP FAST-TRACK: Skip heavy database operations for instant processing
        if is_vip:
            # Ultra-fast CC-ID generation for VIP users
            timestamp_part = str(int(time.time() * 1000))[-6:]
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
            cc_id = f"V{timestamp_part[:3]}{random_part}"  # V prefix for VIP
            
            # Store in memory mapping only - skip database checks for speed
            SimpleCrossChat._global_cc_id_mapping[message_id] = cc_id
            self.cc_id_mapping[message_id] = cc_id
            print(f"VIP_FAST: Generated instant CC-ID {cc_id} for VIP message {message_id}")
            return cc_id
        
        # STANDARD PROCESSING: Full duplicate prevention for regular users
        # STEP 1: Check local singleton mappings first
        if message_id in SimpleCrossChat._global_cc_id_mapping:
            existing_cc_id = SimpleCrossChat._global_cc_id_mapping[message_id]
            print(f"SINGLETON_FOUND: Message {message_id} already has CC-ID {existing_cc_id}")
            return existing_cc_id
        
        if message_id in self.cc_id_mapping:
            existing_cc_id = self.cc_id_mapping[message_id]
            print(f"LOCAL_FOUND: Message {message_id} already has CC-ID {existing_cc_id}")
            SimpleCrossChat._global_cc_id_mapping[message_id] = existing_cc_id
            return existing_cc_id
        
        # STEP 2: Check database for existing CC-ID
        try:
            # MongoDB check - use bot's database handler
            existing_record = None
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                existing_record = self.bot.db_handler.get_crosschat_message(str(message_id))
            if existing_record and existing_record.get('cc_id'):
                existing_cc_id = existing_record['cc_id']
                print(f"DB_FOUND: Message {message_id} already has database CC-ID {existing_cc_id}")
                
                # Update local mappings
                SimpleCrossChat._global_cc_id_mapping[message_id] = existing_cc_id
                self.cc_id_mapping[message_id] = existing_cc_id
                return existing_cc_id
        except Exception as e:
            print(f"DB_CHECK_ERROR: {e}")
        
        # STEP 3: Generate new CC-ID with atomic database protection
        timestamp_part = str(int(time.time() * 1000))[-6:]
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
        cc_id = f"{timestamp_part[:4]}{random_part}"
        
        # STEP 4: Try atomic database insert with UNIQUE constraint
        try:
            # Use direct SQL insert with ON CONFLICT for atomic protection
            # MongoDB insert - use bot's database handler
            success = True
            print(f"🔍 DEBUG: CC-ID Generation - checking db_handler: {hasattr(self.bot, 'db_handler')}")
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler and message:
                message_data = {
                    "message_id": str(message_id),
                    "cc_id": cc_id,
                    "user_id": str(message.author.id),
                    "username": message.author.display_name,
                    "content": message.content or "",
                    "guild_id": str(message.guild.id),
                    "channel_id": str(message.channel.id)
                }
                print(f"🔍 DEBUG: CC-ID calling log_crosschat_message...")
                success = self.bot.db_handler.log_crosschat_message(message_data)
                print(f"🔍 DEBUG: CC-ID logging result: {success}")
                
                # FORCE IMMEDIATE VERIFICATION
                if success:
                    verify_record = self.bot.db_handler.get_crosschat_message(str(message_id))
                    if verify_record:
                        print(f"✅ CC-ID VERIFICATION: Message {message_id} confirmed in database")
                    else:
                        print(f"❌ CC-ID VERIFICATION FAILED: Message {message_id} not found in database")
            else:
                print(f"❌ DEBUG: CC-ID Generation - No db_handler available")
            
            # MongoDB atomic insert completed above
            
            if success:
                print(f"DB_ATOMIC: Generated ATOMIC CC-ID {cc_id} for message {message_id}")
                
                # Update local mappings
                SimpleCrossChat._global_cc_id_mapping[message_id] = cc_id
                self.cc_id_mapping[message_id] = cc_id
                return cc_id
            else:
                # Another instance already inserted - get their CC-ID
                # MongoDB check - use bot's database handler
                existing_record = None
                if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                    existing_record = self.bot.db_handler.get_crosschat_message(str(message_id))
                if existing_record and existing_record.get('cc_id'):
                    existing_cc_id = existing_record['cc_id']
                    print(f"DB_CONFLICT: Message {message_id} already has CC-ID {existing_cc_id} from another instance")
                    
                    # Update local mappings
                    SimpleCrossChat._global_cc_id_mapping[message_id] = existing_cc_id
                    self.cc_id_mapping[message_id] = existing_cc_id
                    return existing_cc_id
                    
        except Exception as e:
            print(f"DB_ATOMIC_ERROR: {e}")
        
        # STEP 5: Store in local mappings as fallback
        SimpleCrossChat._global_cc_id_mapping[message_id] = cc_id
        self.cc_id_mapping[message_id] = cc_id
        
        print(f"CC_GENERATED: Generated CC-ID {cc_id} for message {message_id}")
        return cc_id
        
    def get_channels(self):
        """Get cross-chat channels from MongoDB"""
        try:
            channels = []
            
            # Get channels from MongoDB handler
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                db_channels = self.bot.db_handler.get_crosschat_channels()
                print(f"SIMPLE: Loaded {len(db_channels)} channels from MongoDB")
                
                # Verify each channel is accessible
                for channel_id in db_channels:
                    # db_channels is now a dict with channel_id as keys
                    try:
                        discord_channel = self.bot.get_channel(int(channel_id))
                        if discord_channel:
                            channels.append(int(channel_id))
                            print(f"SIMPLE: Verified channel {channel_id} in {discord_channel.guild.name}")
                        else:
                            print(f"SIMPLE: Channel {channel_id} not accessible")
                    except Exception as e:
                        print(f"SIMPLE: Error verifying channel {channel_id}: {e}")
            else:
                print("SIMPLE: No MongoDB handler available - using empty channels list")
                
            print(f"SIMPLE: Returning {len(channels)} verified channels")
            return channels
            
        except Exception as e:
            print(f"SIMPLE: Error getting channels: {e}")
            return []
    
    async def _is_crosschat_channel(self, channel_id) -> bool:
        """Check if channel is registered for crosschat"""
        try:
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                channels = self.bot.db_handler.get_crosschat_channels()
                return int(channel_id) in channels
            return False
        except Exception as e:
            print(f"ERROR: Failed to check crosschat channel: {e}")
            return False
    
    async def is_user_banned(self, user_id):
        """Check if user is service banned (OPTIMIZED with cache)"""
        try:
            from performance_cache import performance_cache
            
            # Use cached ban list (much faster than database)
            banned_users = performance_cache.get_banned_users()
            return str(user_id) in banned_users
            
        except Exception as e:
            print(f"SIMPLE: Error checking user ban: {e}")
            return False
            
    async def is_server_banned(self, guild_id):
        """Check if server is banned (OPTIMIZED with cache)"""
        try:
            from performance_cache import performance_cache
            
            # Use cached ban list (much faster than database)
            banned_servers = performance_cache.get_banned_servers()
            return str(guild_id) in banned_servers
            
        except Exception as e:
            print(f"SIMPLE: Error checking server ban: {e}")
            return False
    
    async def check_automod(self, message):
        """Check message against automod rules, return reason if blocked"""
        try:
            # Check if automod is enabled using database storage
            # MongoDB check - automod enabled by default
            automod_enabled = True
            if not automod_enabled:
                return None
                
            # Basic content filtering - can be expanded later
            content = message.content.lower()
            blocked_words = ['spam', 'scam', 'hack']  # Basic example
            for word in blocked_words:
                if word in content:
                    return f"Message contains blocked word: {word}"
            return None
        except Exception as e:
            print(f"SIMPLE: Automod check error: {e}")
            return None
    
    async def send_block_dm(self, user, block_type, reason):
        """Send DM to user explaining why their message was blocked"""
        try:
            embed = discord.Embed(
                title="❌ Message Blocked",
                description=f"Your message was blocked: {reason}",
                color=0xff0000,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Block Type", value=block_type, inline=True)
            embed.set_footer(text="SynapseChat Cross-Chat System")
            
            await user.send(embed=embed)
            print(f"SIMPLE_DM: Sent block notification to {user.name} ({user.id}) for {block_type}")
        except Exception as e:
            print(f"SIMPLE: Failed to send block DM to {user.name}: {e}")
    
    async def send_automod_warning(self, user, automod_reason, message_content):
        """Send automod warning DM with specific violation details"""
        try:
            # Truncate message content for display
            display_content = message_content[:100] + "..." if len(message_content) > 100 else message_content
            
            embed = discord.Embed(
                title="⚠️ AutoMod Warning",
                description="Your message was blocked by our automated moderation system.",
                color=0xff9900,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Violation Type", value=automod_reason, inline=False)
            embed.add_field(name="Message Content", value=f"```{display_content}```", inline=False)
            embed.add_field(
                name="What to do?", 
                value="Please review our community guidelines and rephrase your message. Repeated violations may result in temporary restrictions.", 
                inline=False
            )
            embed.set_footer(text="SynapseChat AutoMod System")
            
            await user.send(embed=embed)
            print(f"AUTOMOD_DM: Sent automod warning to {user.name} ({user.id}) for: {automod_reason}")
            
            # Log the automod warning to database for tracking
            try:
                warning_data = {
                    'user_id': str(user.id),
                    'username': user.display_name,
                    'warning_type': 'automod',
                    'reason': automod_reason,
                    'message_content': message_content,
                    'timestamp': datetime.now().isoformat()
                }
                # MongoDB logging - use bot's database handler
                if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                    self.bot.db_handler.log_moderation_action(warning_data)
                print(f"AUTOMOD_LOG: Logged warning for {user.name}")
            except Exception as log_e:
                print(f"AUTOMOD_LOG: Failed to log warning: {log_e}")
                
        except Exception as e:
            print(f"SIMPLE: Failed to send automod warning to {user.name}: {e}")
    
    def get_tag_hierarchy_level(self, user_roles, guild, user_id=None, is_vip=False):
        """Determine user's tag hierarchy level based on roles
        
        Returns:
            dict: {
                'level': int (1-7, higher = more important),
                'tag': str (display tag),
                'color': int (embed color),
                'priority': int (processing priority)
            }
        """
        
        # Default level for regular users (no tag)
        tag_info = {
            'level': 1,
            'tag': '',
            'color': 0x7289da,  # Blue
            'priority': 100
        }
        
        # Global VIP detection helper function
        import os
        def check_role_globally(role_id):
            """Check if user has role across ALL guilds"""
            if not (role_id and user_id and hasattr(self, 'bot') and self.bot):
                return False
            for check_guild in self.bot.guilds:
                member = check_guild.get_member(user_id)
                if member and member.roles:
                    for role in member.roles:
                        if str(role.id) == str(role_id):
                            return True
            return False
        
        # Check global VIP status BEFORE using in Founder/Staff checks
        vip_role_id2 = os.environ.get('VIP_ROLE_ID2')  # Elite
        vip_role_id = os.environ.get('VIP_ROLE_ID')    # Architect
        
        has_elite_vip = check_role_globally(vip_role_id2)
        has_architect_vip = check_role_globally(vip_role_id) if not has_elite_vip else False
        has_staff_role = check_role_globally(os.environ.get('STAFF_ROLE_ID'))
        
        # PRIORITY 1: Check if this is the bot owner/founder FIRST
        bot_owner_id = os.environ.get('BOT_OWNER_ID')
        if user_id and bot_owner_id and str(user_id) == str(bot_owner_id):
            founder_tag = 'SynapseChat Founder'  # Default founder tag
            
            # Apply global VIP icons to founder tag
            if has_elite_vip:
                founder_tag = '💎 SynapseChat Founder'  # Elite founder with diamond
                print(f"FOUNDER_ELITE_GLOBAL: Founder has Elite VIP globally")
            elif has_architect_vip:
                founder_tag = '⭐ SynapseChat Founder'  # Architect founder with star
                print(f"FOUNDER_ARCHITECT_GLOBAL: Founder has Architect VIP globally")
            
            return {
                'level': 7,
                'tag': founder_tag,
                'color': 0xDC143C,  # Crimson red
                'priority': 10
            }
        
        # PRIORITY 2: Check for Staff role SECOND
        if has_staff_role:
            staff_tag = 'SynapseChat Staff'  # Default staff tag
            staff_priority = 100  # Same as regular users (1.0s processing)
            
            # Apply global VIP icons and processing speeds to staff tag
            if has_elite_vip:
                staff_tag = '💎 SynapseChat Staff'  # Elite staff with diamond
                staff_priority = 10  # Elite VIP priority - 0.25s processing
                print(f"STAFF_ELITE_GLOBAL: Staff has Elite VIP globally")
            elif has_architect_vip:
                staff_tag = '⭐ SynapseChat Staff'  # Architect staff with star
                staff_priority = 25  # Architect VIP priority - 0.5s processing
                print(f"STAFF_ARCHITECT_GLOBAL: Staff has Architect VIP globally")
            
            return {
                'level': 6,
                'tag': staff_tag,
                'color': 0x9932cc,  # Purple
                'priority': staff_priority
            }
        
        # PRIORITY 3: VIP-only users (no Staff or Founder roles)
        if has_elite_vip:
            return {
                'level': 5,
                'tag': '💎 SynapseChat Elite',
                'color': 0xff8c00,  # Orange
                'priority': 10  # Elite processing speed
            }
        elif has_architect_vip:
            return {
                'level': 3,
                'tag': '⭐ SynapseChat Architect',
                'color': 0xffd700,  # Gold
                'priority': 25  # Architect processing speed
            }
        elif is_vip:  # Fallback for subscription-based VIP
            return {
                'level': 3,
                'tag': 'SynapseChat Architect',
                'color': 0xffd700,  # Gold
                'priority': 25
            }
        
        return tag_info

    async def process(self, message):
        """Process crosschat message with VIP FAST-TRACK optimization and tag hierarchy"""
        
        # Basic filtering
        if not message.guild or message.author.bot or not message.content.strip():
            return None
        
        # Database duplicate prevention - the ONLY check we need
        message_id = str(message.id)
        print(f"🔍 PROCESS: Starting crosschat processing for message {message_id}")
        
        # PRIVACY PROTECTION: Verify channel is registered for crosschat
        is_crosschat = await self._is_crosschat_channel(message.channel.id)
        if not is_crosschat:
            print(f"🛡️ PRIVACY: Channel {message.channel.id} not registered - skipping ALL processing")
            return None
        
        print(f"✅ CROSSCHAT VERIFIED: Channel {message.channel.id} is registered for crosschat")
        
        # Get available channels early for debugging
        channels = self.get_channels()
        print(f"🔍 CROSSCHAT DEBUG: Total channels available: {len(channels)}")
        print(f"🔍 CROSSCHAT DEBUG: Channel list: {channels}")
        print(f"🔍 CROSSCHAT DEBUG: Current channel: {message.channel.id}")
        
        if not channels:
            print(f"❌ CRITICAL: No crosschat channels available for message forwarding")
            return None
            
        if int(message.channel.id) not in channels:
            print(f"❌ CRITICAL: Current channel {message.channel.id} not in channels list {channels}")
            return None
        
        # IMMEDIATE DUPLICATE PREVENTION - Log processing start to prevent race conditions
        print(f"🔍 DUPLICATE_CHECK: Checking if message {message_id} already processed")
        existing = None
        if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
            existing = self.bot.db_handler.get_crosschat_message(message_id)
        else:
            print(f"❌ CRITICAL: No database handler available for duplicate checking")
            
        if existing:
            print(f"🛡️ DUPLICATE_SKIP: Message {message_id} already processed in database, skipping")
            return 'processed'
        else:
            # IMMEDIATELY mark as processing to prevent duplicates
            print(f"✅ DUPLICATE_CHECK: Message {message_id} is new, marking as processing")
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                try:
                    # Create immediate processing marker
                    processing_marker = {
                        'message_id': message_id,
                        'status': 'processing',
                        'user_id': str(message.author.id),
                        'channel_id': str(message.channel.id),
                        'guild_id': str(message.guild.id),
                        'timestamp': message.created_at.isoformat(),
                        'processing_started': True
                    }
                    self.bot.db_handler.log_crosschat_message(processing_marker)
                    print(f"🔒 PROCESSING_LOCK: Marked message {message_id} as processing")
                except Exception as e:
                    print(f"⚠️ PROCESSING_LOCK_FAILED: Could not mark processing: {e}")
            print(f"✅ DUPLICATE_CHECK: Message {message_id} ready for processing")
        
        # VIP STATUS CHECK - Early detection for fast-track processing
        is_vip = await self.is_support_vip(message.author.id)
        
        # ELITE VIP CHECK - GLOBAL check across all guilds for VIP_ROLE_ID2
        import os
        vip_role_id2 = os.environ.get('VIP_ROLE_ID2')
        is_elite_vip = False
        
        if vip_role_id2 and hasattr(self, 'bot') and self.bot:
            # Check across ALL guilds where bot can see the user
            for check_guild in self.bot.guilds:
                member = check_guild.get_member(message.author.id)
                if member and member.roles:
                    for role in member.roles:
                        if str(role.id) == str(vip_role_id2):
                            is_elite_vip = True
                            print(f"ELITE_VIP_GLOBAL: User {message.author.display_name} has Elite VIP status in {check_guild.name} - ULTRA FAST processing")
                            break
                if is_elite_vip:
                    break
        
        # TAG HIERARCHY - Get user's tag level (separate from VIP processing speed)
        # Pass None for roles to force global checking across all guilds
        tag_info = self.get_tag_hierarchy_level(None, message.guild, message.author.id, is_vip)
        
        # Use tag hierarchy color (VIP users get their VIP tag color)
        final_color = tag_info['color']
        
        if is_elite_vip:
            # ELITE VIP: Full security checks with ultra-fast processing
            print(f"ELITE_VIP_EXPRESS: Processing Elite VIP {tag_info['tag']} message {message.id} from {message.author.display_name}")
            
            # REQUIRED: Ban checks for Elite VIP users
            if await self.is_user_banned(message.author.id):
                print(f"ELITE_VIP_BLOCKED: Elite VIP user {message.author.id} is banned")
                return 'banned'
            
            if await self.is_server_banned(message.guild.id):
                print(f"ELITE_VIP_BLOCKED: Elite VIP user's server {message.guild.id} is banned")
                return 'server_banned'
            
            # REQUIRED: AutoMod check for Elite VIP users
            automod_reason = await self.check_automod(message)
            if automod_reason:
                print(f"ELITE_VIP_AUTOMOD: Elite VIP message blocked by AutoMod: {automod_reason}")
                await self.send_automod_warning(message.author, automod_reason, message.content)
                return 'blocked'
            
            print(f"ELITE_VIP_EXPRESS: Elite VIP security checks passed for message {message.id}")
            
        elif is_vip:
            # VIP FAST-TRACK: Optimized processing with REQUIRED security checks
            print(f"VIP_FAST: Processing VIP {tag_info['tag']} message {message.id} from {message.author.display_name}")
            
            # REQUIRED: Ban checks for VIP users
            if await self.is_user_banned(message.author.id):
                print(f"VIP_BLOCKED: VIP user {message.author.id} is banned")
                await self.send_block_dm(message.author, "user_ban", "You are currently banned from using CrossChat")
                return 'banned'
            
            if await self.is_server_banned(message.guild.id):
                print(f"VIP_BLOCKED: VIP user's server {message.guild.id} is banned")
                return 'server_banned'
            
            # REQUIRED: AutoMod check for VIP users
            automod_reason = await self.check_automod(message)
            if automod_reason:
                print(f"VIP_AUTOMOD: VIP message blocked by AutoMod: {automod_reason}")
                await self.send_automod_warning(message.author, automod_reason, message.content)
                return 'blocked'
            
            # REQUIRED: System configuration check for VIP (needed for reactions)
            try:
                system_config = await self.get_system_config()
                crosschat_enabled = system_config.get('cross_chat_enabled', True)
                
                if not crosschat_enabled:
                    print(f"VIP_BLOCKED: CrossChat system disabled - not processing VIP message {message.id}")
                    return 'system_disabled'
            except Exception as e:
                print(f"VIP_CONFIG_ERROR: Failed to check system status: {e}")
                # Continue processing for VIP users even if config check fails
            
            # Fast channel verification for VIP (use already retrieved channels)
            if not channels or int(message.channel.id) not in channels:
                print(f"VIP_BLOCKED: Channel {message.channel.id} not in verified channels list")
                return None
            
            print(f"VIP_FAST: VIP security checks passed for message {message.id}")
            print(f"VIP_DEBUG: Available channels for distribution: {channels}")
            
        else:
            # STANDARD PROCESSING: Full checks for regular users
            # Check system status
            try:
                system_config = await self.get_system_config()
                crosschat_enabled = system_config.get('cross_chat_enabled', True)
                automod_enabled = system_config.get('auto_moderation_enabled', True)
                
                if not crosschat_enabled:
                    print(f"SIMPLE: CrossChat system disabled - not processing message {message.id}")
                    return 'system_disabled'
            except Exception as e:
                print(f"SIMPLE_CONFIG_ERROR: Failed to check system status: {e}")
                crosschat_enabled = True
                automod_enabled = True
            
            # Verify this is a crosschat channel (use already retrieved channels)
            if not channels or int(message.channel.id) not in channels:
                print(f"STANDARD_BLOCKED: Channel {message.channel.id} not in verified channels list")
                print(f"DEBUG: Available channels: {channels}")
                return None
                
            print(f"STANDARD: Channel verification passed for {message.channel.id}")
            print(f"STANDARD_DEBUG: Available channels for distribution: {channels}")
            
            # Check if user is banned
            if await self.is_user_banned(message.author.id):
                print(f"SIMPLE_BLOCKED: User {message.author.id} is banned")
                await message.add_reaction('🚫')
                return 'banned'
            
            if await self.is_server_banned(message.guild.id):
                print(f"SIMPLE_BLOCKED: Server {message.guild.id} is banned")
                await message.add_reaction('🚫')
                return 'server_banned'
            
            # AutoMod check for regular users
            automod_reason = await self.check_automod(message)
            if automod_reason:
                print(f"SIMPLE_AUTOMOD: Message blocked by AutoMod: {automod_reason}")
                await message.add_reaction('⚠️')
                await self.send_automod_warning(message.author, automod_reason, message.content)
                return 'blocked'
            
            print(f"SIMPLE: Processing {message.id} from {message.author.display_name}")
            
            # Get channels for distribution
            print(f"SIMPLE: Found {len(channels)} channels for distribution")
            
            print(f"SIMPLE: Processing {message.id} from {message.author.display_name}")
            
            # Get channels for distribution
            print(f"SIMPLE: Found {len(channels)} channels for distribution")
        
        # Add processing reaction immediately
        try:
            await message.add_reaction('⏳')
            print(f"PROCESSING_REACTION: Added ⏳ to message {message.id}")
        except Exception as e:
            print(f"PROCESSING_REACTION_ERROR: Failed to add processing reaction: {e}")
        
        # Generate CC-ID ONCE for both VIP and standard users (after all checks)
        cc_id = self.generate_cc_id(message.id, is_vip=is_vip, message=message)
        print(f"SIMPLE: Generated CC-ID {cc_id} for message {message.id} (VIP: {is_vip})")
        
        # Create embed for crosschat display with hierarchy and VIP support
        embed = discord.Embed(
            description=message.content or "*[Image/File attached]*",
            color=final_color,  # VIP gold or hierarchy-based color
            timestamp=message.created_at
        )
        
        # Set author with tag hierarchy and VIP indication
        hierarchy_tag = f"[{tag_info['tag']}]"
        vip_indicator = " ⭐" if is_vip else ""
        author_name = f"{hierarchy_tag} {message.author.display_name}{vip_indicator} • {message.guild.name}"
        embed.set_author(
            name=author_name,
            icon_url=message.author.display_avatar.url
        )
        
        # Add origin info
        embed.add_field(
            name="📍 From",
            value=f"#{message.channel.name} • {message.guild.name}",
            inline=False
        )
        
        # Handle image attachments - set the first image as embed image
        image_attachment = None
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    embed.set_image(url=attachment.url)
                    image_attachment = attachment
                    break
        
        embed.set_footer(text=f"CC-{cc_id} • ID: {message.author.id}")
        
        # Database logging: Standard users logged immediately, VIP users logged after distribution
        log_data = {
            'user_id': str(message.author.id),
            'username': message.author.display_name,
            'message': message.content,
            'original_message': message.content,
            'channel_id': str(message.channel.id),
            'channel_name': message.channel.name,
            'guild_id': str(message.guild.id),
            'guild_name': message.guild.name,
            'message_id': str(message.id),
            'cc_id': cc_id,
            'action_type': 'crosschat',
            'timestamp': message.created_at.isoformat(),
            'edit_history': [],
            'is_deleted': False,
            'deleted_at': None,
            'tag_level': tag_info['level'],
            'tag_name': tag_info['tag'],
            'is_vip': is_vip
        }
        
        # Both VIP and standard users will log after distribution for consistency
        print(f"PROCESSING: {tag_info['tag']} message {message.id} - logging after distribution")
        
        # Prepare files to send with the message
        files_to_send = []
        if message.attachments:
            for attachment in message.attachments:
                try:
                    # Download the file to send it to other channels
                    file_data = await attachment.read()
                    discord_file = discord.File(
                        io.BytesIO(file_data), 
                        filename=attachment.filename
                    )
                    files_to_send.append(discord_file)
                    print(f"ATTACHMENT: Prepared {attachment.filename} for forwarding")
                except Exception as e:
                    print(f"ATTACHMENT_ERROR: Failed to prepare {attachment.filename}: {e}")

        # Initialize sent counter for all processing paths
        sent_count = 0
        
        # SPEED DIFFERENTIATION: Elite VIP > Regular VIP > Standard users
        if is_elite_vip:
            # ELITE VIP: Instant parallel distribution with minimal delays
            print(f"ELITE_VIP_DISTRIBUTION: Starting ultra-fast parallel distribution to {len(channels)-1} channels")
            tasks = []
            
            for channel_id in channels:
                if channel_id == message.channel.id:
                    continue
                    
                channel = self.bot.get_channel(channel_id)
                if channel:
                    # Elite VIP: No file preparation delays - direct send
                    task = asyncio.create_task(self._elite_vip_ultra_send(channel, embed, cc_id, str(message.id)))
                    tasks.append(task)
            
            # Elite VIP: Wait for all sends with minimal timeout
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                sent_count = sum(1 for result in results if result is True)
                print(f"ELITE_VIP_COMPLETE: Ultra-fast distribution completed - {sent_count}/{len(tasks)} channels")
            
        elif is_vip:
            # VIP: Parallel sends for maximum speed
            print(f"VIP_FAST: Starting parallel distribution to {len(channels)-1} channels")
            print(f"VIP_DEBUG: Source channel: {message.channel.id}, Target channels: {channels}")
            tasks = []
            
            for channel_id in channels:
                if channel_id == message.channel.id:
                    continue
                    
                channel = self.bot.get_channel(channel_id)
                if channel:
                    # For VIP, create fresh file objects for each channel (required for parallel sending)
                    channel_files = []
                    if message.attachments:
                        for attachment in message.attachments:
                            try:
                                file_data = await attachment.read()
                                discord_file = discord.File(
                                    io.BytesIO(file_data), 
                                    filename=attachment.filename
                                )
                                channel_files.append(discord_file)
                            except Exception as e:
                                print(f"VIP_ATTACHMENT_ERROR: Failed to prepare {attachment.filename}: {e}")
                    
                    tasks.append(self._vip_fast_send_with_files(channel, embed, channel_files, cc_id, str(message.id)))
                    print(f"VIP_SEND: Added task for channel {channel_id} ({channel.name})")
            
            # Execute all sends simultaneously for VIP speed
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                sent_count = sum(1 for r in results if isinstance(r, bool) and r)
                print(f"VIP_FAST: Instant delivery complete - {sent_count} channels")
            else:
                sent_count = 0
            
            # VIP: Log to MongoDB AFTER instant distribution (FORCE IMMEDIATE)
            print(f"🔍 DEBUG: VIP - FORCING IMMEDIATE LOGGING for message {log_data['message_id']}")
            try:
                await self._log_message_async(log_data, "VIP")
            except Exception as e:
                print(f"❌ CRITICAL VIP LOGGING ERROR: {e}")
                import traceback
                traceback.print_exc()
            
            # VIP: Replace processing reaction with final status
            if sent_count > 0:
                await self.replace_processing_reaction(message, '✅')
                return 'processed'
            else:
                await self.replace_processing_reaction(message, '❌')
                return 'failed'
                
        else:
            # STANDARD PROCESSING: Sequential sends for regular users
            print(f"STANDARD: Starting sequential distribution to {len(channels)-1} channels")
            print(f"STANDARD_DEBUG: Source channel: {message.channel.id}, Target channels: {channels}")
            for channel_id in channels:
                if channel_id == message.channel.id:
                    continue
                    
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        # Create fresh file objects for each channel
                        channel_files = []
                        if message.attachments:
                            for attachment in message.attachments:
                                try:
                                    file_data = await attachment.read()
                                    discord_file = discord.File(
                                        io.BytesIO(file_data), 
                                        filename=attachment.filename
                                    )
                                    channel_files.append(discord_file)
                                except Exception as e:
                                    print(f"ATTACHMENT_ERROR: Failed to prepare {attachment.filename}: {e}")
                        
                        # Send embed with files
                        sent_message = await channel.send(embed=embed, files=channel_files)
                        # Track sent message for global editing
                        await self._track_sent_message(cc_id, str(message.id), str(channel_id), str(sent_message.id))
                        sent_count += 1
                        print(f"STANDARD_SEND: Successfully sent to {channel.name} ({channel.guild.name}) with {len(channel_files)} files")
                except Exception as e:
                    print(f"SIMPLE: Failed to send to channel {channel_id}: {e}")
            
            print(f"SIMPLE: Message {message.id} distributed to {sent_count} channels")
            
            # Standard users: Log to database AFTER distribution (FORCE IMMEDIATE)
            print(f"🔍 DEBUG: STANDARD - FORCING IMMEDIATE LOGGING for message {log_data['message_id']}")
            try:
                await self._log_message_async(log_data, "STANDARD")
            except Exception as e:
                print(f"❌ CRITICAL STANDARD LOGGING ERROR: {e}")
                import traceback
                traceback.print_exc()
        
        # Only add success reaction if message was actually sent to channels
        if sent_count > 0:
            await self.replace_processing_reaction(message, '✅')
            result = 'processed'
        else:
            await self.replace_processing_reaction(message, '❌')
            result = 'failed'
        
        return result
    
    async def add_reaction(self, message, emoji):
        """Add reaction to message"""
        try:
            await message.add_reaction(emoji)
        except Exception as e:
            print(f"Failed to add reaction {emoji} to message {message.id}: {e}")
    
    async def replace_processing_reaction(self, message, final_emoji):
        """Replace processing reaction with final status reaction"""
        try:
            # Remove processing reaction first
            await message.remove_reaction('⏳', self.bot.user)
            print(f"REACTION_REPLACED: Removed ⏳ from message {message.id}")
            
            # Add final status reaction
            await message.add_reaction(final_emoji)
            print(f"REACTION_REPLACED: Added {final_emoji} to message {message.id}")
        except discord.NotFound:
            # Reaction not found, just add the final one
            try:
                await message.add_reaction(final_emoji)
                print(f"REACTION_ADDED: Added {final_emoji} to message {message.id} (⏳ not found)")
            except Exception as e:
                print(f"REACTION_ADD_ERROR: Failed to add {final_emoji}: {e}")
        except discord.Forbidden:
            # No permission to remove reactions, just add the final one
            try:
                await message.add_reaction(final_emoji)
                print(f"REACTION_ADDED: Added {final_emoji} to message {message.id} (no remove permission)")
            except Exception as e:
                print(f"REACTION_ADD_ERROR: Failed to add {final_emoji}: {e}")
        except Exception as e:
            print(f"REACTION_REPLACE_ERROR: Failed to replace reaction on message {message.id}: {e}")
            # Fallback: just add the final reaction
            try:
                await message.add_reaction(final_emoji)
                print(f"REACTION_FALLBACK: Added {final_emoji} to message {message.id}")
            except:
                pass

    async def _vip_fast_send(self, channel, embed):
        """Ultra-fast send function for VIP messages - no error handling delays"""
        try:
            await channel.send(embed=embed)
            return True
        except:
            return False  # Silent fail for maximum speed
    
    async def _vip_fast_send_with_tracking(self, channel, embed, cc_id, original_message_id):
        """Ultra-fast send function for VIP messages with message tracking for global editing"""
        try:
            sent_message = await channel.send(embed=embed)
            # Track sent message for global editing (async, non-blocking)
            asyncio.create_task(self._track_sent_message(cc_id, original_message_id, str(channel.id), str(sent_message.id)))
            return True
        except:
            return False  # Silent fail for maximum speed
    
    async def _elite_vip_ultra_send(self, channel, embed, cc_id, original_message_id):
        """Ultra-fast send function for Elite VIP messages - maximum speed priority"""
        try:
            sent_message = await channel.send(embed=embed)
            # Background tracking for Elite VIP - non-blocking
            asyncio.create_task(self._track_sent_message(cc_id, original_message_id, str(channel.id), str(sent_message.id)))
            return True
        except:
            return False  # Silent fail for Elite VIP maximum speed
    
    async def _track_sent_message(self, cc_id, original_message_id, channel_id, sent_message_id):
        """Track sent message in MongoDB for global editing functionality"""
        try:
            # Use MongoDB handler for tracking sent messages
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                success = self.bot.db_handler.track_sent_message(
                    cc_id=cc_id,
                    original_message_id=original_message_id,
                    channel_id=channel_id,
                    sent_message_id=sent_message_id
                )
                if success:
                    print(f"✅ MONGODB: Tracked sent message {sent_message_id} for CC-{cc_id}")
                else:
                    print(f"❌ MONGODB: Failed to track sent message {sent_message_id}")
            else:
                print(f"❌ MONGODB: No database handler - message tracking disabled")
        except Exception as e:
            print(f"TRACK_ERROR: Failed to track sent message {sent_message_id}: {e}")
    
    async def _log_message_async(self, log_data, user_type):
        """Asynchronously log message to MongoDB after distribution with duplicate prevention"""
        try:
            # Use MongoDB handler for logging crosschat messages
            print(f"🔍 DEBUG: Checking if bot has db_handler: {hasattr(self.bot, 'db_handler')}")
            if hasattr(self.bot, 'db_handler'):
                print(f"🔍 DEBUG: db_handler exists: {self.bot.db_handler is not None}")
            
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                message_data = {
                    'message_id': log_data['message_id'],
                    'user_id': log_data['user_id'],
                    'username': log_data['username'],
                    'content': log_data['message'],
                    'guild_id': log_data['guild_id'],
                    'channel_id': log_data['channel_id'],
                    'tag_name': log_data.get('tag_name', 'Unknown'),
                    'timestamp': log_data.get('timestamp')
                }
                print(f"🔍 DEBUG: Calling log_crosschat_message with data: {message_data}")
                success = self.bot.db_handler.log_crosschat_message(message_data)
                if success:
                    print(f"✅ MONGODB {user_type}_LOG: Logged {log_data['tag_name']} message {log_data['message_id']}")
                else:
                    print(f"❌ MONGODB {user_type}_LOG: Failed to log message {log_data['message_id']}")
            else:
                print(f"❌ MONGODB {user_type}_LOG: No database handler available - bot.db_handler is None or missing")
        except Exception as e:
            print(f"❌ MONGODB {user_type}_LOG_ERROR: Failed to log message {log_data.get('message_id', 'unknown')}: {e}")

    async def _remove_discord_duplicates(self, original_message, cc_id, channel_ids):
        """Remove Discord-level duplicates by scanning channels after sends complete"""
        try:
            await asyncio.sleep(3)  # Wait for Discord API to settle
            
            duplicate_count = 0
            cc_id_pattern = cc_id  # Look for this specific CC-ID
            
            # Scan each channel for duplicate messages with same CC-ID
            for channel_id in channel_ids:
                if channel_id == original_message.channel.id:
                    continue  # Skip origin channel
                    
                try:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        continue
                    
                    # Get last 10 messages to find duplicates
                    messages = []
                    async for msg in channel.history(limit=10):
                        if msg.bot and hasattr(msg, 'embeds') and msg.embeds:
                            embed = msg.embeds[0]
                            if hasattr(embed, 'footer') and embed.footer and embed.footer.text:
                                if cc_id_pattern in embed.footer.text:
                                    messages.append(msg)
                    
                    # If more than 1 message with same CC-ID, delete extras
                    if len(messages) > 1:
                        # Keep the first one, delete the rest
                        for duplicate_msg in messages[1:]:
                            try:
                                await duplicate_msg.delete()
                                duplicate_count += 1
                                print(f"DUPLICATE_DELETED: Removed duplicate CC-{cc_id} from {channel.name}")
                            except Exception as e:
                                print(f"DUPLICATE_DELETE_FAILED: {e}")
                                
                except Exception as e:
                    print(f"DUPLICATE_SCAN_ERROR: {e}")
            
            if duplicate_count > 0:
                print(f"DUPLICATE_CLEANUP: Removed {duplicate_count} Discord-level duplicates for CC-{cc_id}")
            else:
                print(f"DUPLICATE_CLEANUP: No duplicates found for CC-{cc_id}")
                
        except Exception as e:
            print(f"DUPLICATE_CLEANUP_ERROR: {e}")

    async def send_announcement(self, content: str):
        """Send announcement to all cross-chat channels"""
        try:
            channels = self.get_channels()
            sent_count = 0
            
            # Process multiline formatting - convert \n to actual newlines
            # Also handle markdown formatting edge cases
            formatted_content = content.replace('\\n', '\n')
            
            # Fix markdown formatting issues with newlines
            # Ensure bold/italic markers are properly closed before newlines
            import re
            # Find unclosed bold markers followed by newlines
            formatted_content = re.sub(r'\*\*([^*\n]+)\*\*\n', r'**\1**\n', formatted_content)
            # Find unclosed italic markers followed by newlines  
            formatted_content = re.sub(r'\*([^*\n]+)\*\n', r'*\1*\n', formatted_content)
            
            embed = discord.Embed(
                title="📢 Announcement",
                description=formatted_content,
                color=0xff9900,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="SynapseChat Announcement System")
            
            for channel_id in channels:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(embed=embed)
                        sent_count += 1
                except Exception as e:
                    print(f"SIMPLE: Failed to send announcement to {channel_id}: {e}")
            
            print(f"SIMPLE: Announcement sent to {sent_count} channels")
            return sent_count
        except Exception as e:
            print(f"SIMPLE: Error sending announcement: {e}")
            return 0

    async def announce(self, content: str):
        """Alias for send_announcement"""
        return await self.send_announcement(content)
    
    async def send_system_alert(self, alert_message: str, alert_type: str = "system", admin_user: str = "Administrator"):
        """Send system alert to all CrossChat channels"""
        try:
            channels = self.get_channels()
            sent_count = 0
            
            # Create alert embed with distinctive styling
            if alert_type == "crosschat":
                color = 0x00ff00 if "ENABLED" in alert_message else 0xff0000  # Green for enabled, red for disabled
                title = "🌐 CrossChat System Alert"
            elif alert_type == "automod":
                color = 0x0099ff if "ENABLED" in alert_message else 0xff6600  # Blue for enabled, orange for disabled
                title = "🛡️ AutoMod System Alert"
            else:
                color = 0xffff00  # Yellow for general system alerts
                title = "⚙️ System Alert"
            
            embed = discord.Embed(
                title=title,
                description=alert_message,
                color=color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Administrator", value=admin_user, inline=True)
            embed.set_footer(text="SynapseChat Administrative System")
            
            for channel_id in channels:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(embed=embed)
                        sent_count += 1
                        print(f"ALERT_SENT: System alert sent to {channel.name} in {channel.guild.name}")
                except Exception as e:
                    print(f"ALERT_ERROR: Failed to send system alert to {channel_id}: {e}")
            
            print(f"SYSTEM_ALERT: Alert sent to {sent_count} channels - Type: {alert_type}")
            return sent_count
            
        except Exception as e:
            print(f"SYSTEM_ALERT_ERROR: Failed to send system alert: {e}")
            return 0
    
    async def process_pending_system_alerts(self):
        """Process any pending system alerts from web panel"""
        try:
            # MongoDB operations - simplified alert processing
            print("ALERT_SYSTEM: MongoDB alert system ready")
            # Alert processing would use MongoDB handler if implemented
                
        except Exception as e:
            print(f"PROCESS_ALERTS_ERROR: Failed to process pending alerts: {e}")

    async def process_edit(self, before, after):
        """Process message edits and update globally across CrossChat channels"""
        try:
            # Check if this message is from a CrossChat channel
            channels = self.get_channels()
            if not channels or int(after.channel.id) not in channels:
                print(f"EDIT_SKIP: Message {after.id} not in CrossChat channel")
                return None
            
            # Check if the message was originally processed by CrossChat using MongoDB
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                original_record = self.bot.db_handler.get_crosschat_message(str(before.id))
                
                if not original_record:
                    print(f"EDIT_SKIP: Original message {before.id} not found in CrossChat database")
                    return None
                
                # Process edit with MongoDB data
                cc_id = original_record.get('cc_id')
                if cc_id:
                    print(f"EDIT_PROCESS: Processing edit for CrossChat message CC-{cc_id}")
                    
                    # Update message in MongoDB
                    self.bot.db_handler.update_crosschat_message(str(after.id), after.content)
                    
                    # Find and edit all related messages globally
                    await self._edit_crosschat_globally(cc_id, after.content, str(after.id))
                    
                    print(f"EDIT_COMPLETE: Updated CrossChat message CC-{cc_id} globally")
                    return 'processed'
                else:
                    print("EDIT_SKIP: No CC-ID found for message")
                    return None
            else:
                print("EDIT_SKIP: No MongoDB handler available")
                return None
            
        except Exception as e:
            print(f"EDIT_ERROR: Failed to process edit: {e}")
            import traceback
            traceback.print_exc()
            return 'failed'

    async def _edit_crosschat_globally(self, cc_id: str, new_content: str, original_message_id: str):
        """Edit all crosschat messages globally with the same CC-ID"""
        try:
            # Get all crosschat channels
            channels = self.get_channels()
            if not channels:
                print(f"EDIT_GLOBAL_SKIP: No crosschat channels available")
                return

            print(f"EDIT_GLOBAL: Searching for messages with CC-ID {cc_id} across {len(channels)} channels")
            
            # Search for all messages with this CC-ID
            if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                sent_messages = self.bot.db_handler.get_sent_messages_by_cc_id(cc_id)
                
                if not sent_messages:
                    print(f"EDIT_GLOBAL_SKIP: No sent messages found for CC-ID {cc_id}")
                    return
                
                edit_count = 0
                for sent_msg in sent_messages:
                    # Skip the original message that was edited
                    if sent_msg.get('message_id') == original_message_id:
                        continue
                    
                    try:
                        channel_id = int(sent_msg.get('channel_id'))
                        message_id = int(sent_msg.get('message_id'))
                        
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            # Fetch and edit the message
                            message = await channel.fetch_message(message_id)
                            if message and message.author == self.bot.user:
                                # Parse the current embed to preserve formatting
                                if message.embeds:
                                    embed = message.embeds[0]
                                    # Update the description with new content
                                    embed.description = new_content
                                    await message.edit(embed=embed)
                                    edit_count += 1
                                    print(f"EDIT_GLOBAL_SUCCESS: Updated message {message_id} in {channel.name}")
                                else:
                                    # Fallback for non-embed messages
                                    await message.edit(content=new_content)
                                    edit_count += 1
                                    print(f"EDIT_GLOBAL_SUCCESS: Updated text message {message_id} in {channel.name}")
                    except Exception as e:
                        print(f"EDIT_GLOBAL_ERROR: Failed to edit message {sent_msg.get('message_id')}: {e}")
                
                print(f"EDIT_GLOBAL_COMPLETE: Updated {edit_count} messages globally for CC-ID {cc_id}")
            else:
                print(f"EDIT_GLOBAL_SKIP: No database handler available")
                
        except Exception as e:
            print(f"EDIT_GLOBAL_CRITICAL_ERROR: {e}")
            import traceback
            traceback.print_exc()

    async def edit_message(self, cc_id: str, new_content: str):
        """Edit a cross-chat message by CC-ID"""
        try:
            # Find the original message ID from CC-ID
            original_message_id = self.cc_id_reverse.get(cc_id)
            if not original_message_id:
                print(f"SIMPLE_EDIT: CC-ID {cc_id} not found")
                return False
                
            # Get the sent messages for this original message
            sent_messages = self.message_mappings.get(original_message_id, [])
            if not sent_messages:
                print(f"SIMPLE_EDIT: No sent messages found for CC-ID {cc_id}")
                return False
            
            # Get user ID from database for footer
            user_id = "Unknown"
            try:
                if hasattr(self.bot, 'db_handler') and self.bot.db_handler:
                    message_record = self.bot.db_handler.get_crosschat_message(str(original_message_id))
                    if message_record and message_record.get('user_id'):
                        user_id = message_record['user_id']
            except Exception as e:
                print(f"SIMPLE_EDIT: Failed to get user ID from database: {e}")
            
            # Create updated embed
            embed = discord.Embed(
                description=new_content,
                color=0x7289da,
                timestamp=datetime.utcnow()
            )
            
            # Add edit indicator
            embed.add_field(
                name="✏️ Edited",
                value="This message was edited by an administrator",
                inline=False
            )
            
            # Add footer with CC-ID and user ID
            embed.set_footer(text=f"CC-{cc_id} • ID: {user_id}")
            
            # Edit all sent messages
            edit_count = 0
            for sent_msg in sent_messages:
                try:
                    await sent_msg.edit(embed=embed)
                    edit_count += 1
                except Exception as e:
                    print(f"SIMPLE_EDIT: Failed to edit message: {e}")
            
            print(f"SIMPLE_EDIT: Edited {edit_count} messages for CC-ID {cc_id}")
            return edit_count > 0
            
        except Exception as e:
            print(f"SIMPLE_EDIT: Error editing message with CC-ID {cc_id}: {e}")
            return False

    async def _vip_fast_send_with_files(self, channel, embed, files, cc_id, original_message_id):
        """VIP optimized sending with file support"""
        try:
            sent_message = await channel.send(embed=embed, files=files)
            # Track sent message for global editing
            await self._track_sent_message(cc_id, original_message_id, str(channel.id), str(sent_message.id))
            print(f"VIP_SEND: Sent to {channel.name} ({channel.guild.name}) with {len(files)} files")
            return True
        except Exception as e:
            print(f"VIP_SEND_ERROR: Failed to send to {channel.name}: {e}")
            return False
