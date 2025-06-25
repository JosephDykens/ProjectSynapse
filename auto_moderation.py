"""
Auto Moderation Manager - Self-Hosted Version
Simplified moderation system for self-hosted deployments
"""

import asyncio
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

class AutoModerationManager:
    """Simplified auto-moderation for self-hosted bot"""
    
    def __init__(self, bot=None, database_storage=None):
        self.bot = bot
        self.database = database_storage
        self.enabled = True
        
        # Get MongoDB handler from bot if available
        if bot and hasattr(bot, 'db_handler'):
            self.db_handler = bot.db_handler
        else:
            self.db_handler = None
        
        # Basic moderation settings
        self.settings = {
            'spam_threshold': 5,  # messages per 10 seconds
            'duplicate_threshold': 3,  # same message count
            'caps_threshold': 70,  # percentage of caps
            'link_filter': True,
            'invite_filter': True,
            'profanity_filter': True
        }
        
        # Spam tracking
        self.user_message_history = {}
        self.duplicate_messages = {}
        
        # 15-minute TTL regex cache for performance optimization
        self.regex_cache = {}
        self.cache_ttl = 900  # 15 minutes in seconds
        self.last_cache_update = {}  # Track per-pattern update times
        
        # Automod violation tracking for automatic warnings/bans
        self.automod_violations = {}  # Track violations per user
        self.violation_threshold = 3  # Violations before formal warning
        self.warning_threshold = 3   # Warnings before ban
        self.ban_duration_minutes = 20  # Ban duration in minutes
        
        # Whitelist system for users who bypass automod
        self.whitelisted_users = set()  # User IDs that bypass all automod checks
        self.whitelisted_roles = set()  # Role IDs that bypass all automod checks
        
        # Comprehensive profanity patterns using regex
        self.profanity_patterns = [
            r'^[a@][s\$][s\$]$',
            r'[a@][s\$][s\$]h[o0][l1][e3][s\$]?',
            r'b[a@][s\$][t\+][a@]rd',
            r'b[e3][a@][s\$][t\+][i1][a@]?[l1]([i1][t\+]y)?',
            r'b[e3][a@][s\$][t\+][i1][l1][i1][t\+]y',
            r'b[e3][s\$][t\+][i1][a@][l1]([i1][t\+]y)?',
            r'b[i1][t\+]ch[s\$]?',
            r'b[i1][t\+]ch[e3]r[s\$]?',
            r'b[i1][t\+]ch[e3][s\$]',
            r'b[i1][t\+]ch[i1]ng?',
            r'b[l1][o0]wj[o0]b[s\$]?',
            r'c[l1][i1][t\+]',
            r'^(c|k|ck|q)[o0](c|k|ck|q)[s\$]?$',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s\$]u',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s\$]u(c|k|ck|q)[e3]d',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s\$]u(c|k|ck|q)[e3]r',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s\$]u(c|k|ck|q)[i1]ng',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s\$]u(c|k|ck|q)[s\$]',
            r'^cum[s\$]?$',
            r'cumm??[e3]r',
            r'cumm?[i1]ngcock',
            r'(c|k|ck|q)um[s\$]h[o0][t\+]',
            r'(c|k|ck|q)un[i1][l1][i1]ngu[s\$]',
            r'(c|k|ck|q)un[i1][l1][l1][i1]ngu[s\$]',
            r'(c|k|ck|q)unn[i1][l1][i1]ngu[s\$]',
            r'(c|k|ck|q)un[t\+][s\$]?',
            r'(c|k|ck|q)un[t\+][l1][i1](c|k|ck|q)',
            r'(c|k|ck|q)un[t\+][l1][i1](c|k|ck|q)[e3]r',
            r'(c|k|ck|q)un[t\+][l1][i1](c|k|ck|q)[i1]ng',
            r'cyb[e3]r(ph|f)u(c|k|ck|q)',
            r'd[a@]mn',
            r'd[i1]ck',
            r'd[i1][l1]d[o0]',
            r'd[i1][l1]d[o0][s\$]',
            r'd[i1]n(c|k|ck|q)',
            r'd[i1]n(c|k|ck|q)[s\$]',
            r'[e3]j[a@]cu[l1]',
            r'(ph|f)[a@]g[s\$]?',
            r'(ph|f)[a@]gg[i1]ng',
            r'(ph|f)[a@]gg?[o0][t\+][s\$]?',
            r'(ph|f)[a@]gg[s\$]',
            r'(ph|f)[e3][l1][l1]?[a@][t\+][i1][o0]',
            r'(ph|f)u(c|k|ck|q)',
            r'(ph|f)u(c|k|ck|q)[s\$]?',
            r'g[a@]ngb[a@]ng[s\$]?',
            r'g[a@]ngb[a@]ng[e3]d',
            r'g[a@]y',
            r'h[o0]m?m[o0]',
            r'h[o0]rny',
            r'j[a@](c|k|ck|q)\-?[o0](ph|f)(ph|f)?',
            r'j[e3]rk\-?[o0](ph|f)(ph|f)?',
            r'j[i1][s\$z][s\$z]?m?',
            r'[ck][o0]ndum[s\$]?',
            r'mast(e|ur)b(8|ait|ate)',
            r'n+[i1]+[gq]+[e3]*r+[s\$]*',
            r'[o0]rg[a@][s\$][i1]m[s\$]?',
            r'[o0]rg[a@][s\$]m[s\$]?',
            r'p[e3]nn?[i1][s\$]',
            r'p[i1][s\$][s\$]',
            r'p[i1][s\$][s\$][o0](ph|f)(ph|f)',
            r'p[o0]rn',
            r'p[o0]rn[o0][s\$]?',
            r'p[o0]rn[o0]gr[a@]phy',
            r'pr[i1]ck[s\$]?',
            r'pu[s\$][s\$][i1][e3][s\$]',
            r'pu[s\$][s\$]y[s\$]?',
            r'[s\$][e3]x',
            r'[s\$]h[i1][t\+][s\$]?',
            r'[s\$][l1]u[t\+][s\$]?',
            r'[s\$]mu[t\+][s\$]?',
            r'[s\$]punk[s\$]?',
            r'[t\+]w[a@][t\+][s\$]?'
        ]
        
        # Phone number patterns (various formats)
        self.phone_patterns = [
            # US/International formats
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890, 123.456.7890, 123 456 7890
            r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',      # (123) 456-7890, (123)456-7890
            r'\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # International +1-123-456-7890
            r'\b\d{10,15}\b',                       # Long digit strings (10-15 digits)
            r'\d{3}\s?\d{3}\s?\d{4}',              # 123 456 7890
            r'\b1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 1-123-456-7890
        ]
        
        # Address patterns (common residential indicators)
        self.address_patterns = [
            # Street addresses
            r'\b\d+\s+[A-Za-z\s]+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|place|pl|way|circle|cir)\b',
            r'\b\d+\s+[A-Za-z\s]+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|place|pl|way|circle|cir)\s*#?\d*\b',
            # Apartment/Unit indicators
            r'\b(apt|apartment|unit|suite|ste)\s*#?\d+\b',
            r'\b#\d+\b',  # Unit numbers
            # ZIP codes
            r'\b\d{5}(-\d{4})?\b',  # 12345 or 12345-6789
            # City, State combinations
            r'\b[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}\b',  # City, ST 12345
            # PO Box
            r'\b(po|p\.o\.)\s*box\s*\d+\b',
            # Common residential terms
            r'\b(live\s+at|address\s+is|my\s+house|home\s+address)\s+\d+\b',
            r'\b\d+\s+(main|north|south|east|west|n|s|e|w)\s+[A-Za-z\s]+(street|st|avenue|ave|road|rd)\b',
        ]
        
        # Link patterns
        self.link_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        ]
        
        # Discord invite patterns
        self.invite_patterns = [
            r'discord\.gg/[a-zA-Z0-9]+',
            r'discordapp\.com/invite/[a-zA-Z0-9]+',
            r'discord\.com/invite/[a-zA-Z0-9]+'
        ]
    
    def _get_cached_regex(self, pattern_key: str, pattern: str) -> Optional[re.Pattern]:
        """
        Get compiled regex pattern from cache with 15-minute TTL
        Returns fresh pattern if cache expired or doesn't exist
        """
        current_time = time.time()
        
        # Check if pattern exists in cache and is still valid
        if (pattern_key in self.regex_cache and 
            pattern_key in self.last_cache_update and
            current_time - self.last_cache_update[pattern_key] < self.cache_ttl):
            return self.regex_cache[pattern_key]
        
        # Compile new pattern and cache it
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            self.regex_cache[pattern_key] = compiled_pattern
            self.last_cache_update[pattern_key] = current_time
            return compiled_pattern
        except re.error:
            # Fallback to simple string matching if regex is invalid
            return None
    
    def _invalidate_cache(self, pattern_key: str = None):
        """
        Invalidate specific pattern or all cached patterns
        Used when automod rules are updated
        """
        if pattern_key:
            self.regex_cache.pop(pattern_key, None)
            self.last_cache_update.pop(pattern_key, None)
        else:
            self.regex_cache.clear()
            self.last_cache_update.clear()
    
    async def check_message(self, message) -> Dict[str, Any]:
        """
        Check message for auto-moderation violations
        Returns dict with violation info
        """
        if not self.enabled:
            return {'action': 'allow', 'reason': 'moderation_disabled'}
        
        # Skip bot messages
        if message.author.bot:
            return {'action': 'allow', 'reason': 'bot_message'}
        
        user_id = str(message.author.id)
        content = message.content.lower() if message.content else ""
        
        # Check if user is whitelisted (bypasses all automod)
        if await self._is_user_whitelisted(message.author, message):
            return {'action': 'allow', 'reason': 'user_whitelisted'}
        
        # Check spam
        spam_result = await self._check_spam(user_id, message)
        if spam_result['action'] != 'allow':
            return spam_result
        
        # Check duplicates
        duplicate_result = await self._check_duplicates(user_id, content)
        if duplicate_result['action'] != 'allow':
            return duplicate_result
        
        # Check caps
        caps_result = await self._check_caps(content)
        if caps_result['action'] != 'allow':
            return caps_result
        
        # Check links
        if self.settings['link_filter']:
            link_result = await self._check_links(content)
            if link_result['action'] != 'allow':
                return link_result
        
        # Check invites
        if self.settings['invite_filter']:
            invite_result = await self._check_invites(content)
            if invite_result['action'] != 'allow':
                return invite_result
        
        # Check profanity
        if self.settings['profanity_filter']:
            profanity_result = await self._check_profanity(content)
            if profanity_result['action'] != 'allow':
                return profanity_result
        
        # Check phone numbers
        phone_result = await self._check_phone_numbers(content)
        if phone_result['action'] != 'allow':
            return phone_result
        
        # Check addresses
        address_result = await self._check_addresses(content)
        if address_result['action'] != 'allow':
            return address_result
        
        return {'action': 'allow', 'reason': 'clean_message'}
    
    async def _check_spam(self, user_id: str, message) -> Dict[str, Any]:
        """Check for spam (too many messages in short time)"""
        now = datetime.now()
        
        if user_id not in self.user_message_history:
            self.user_message_history[user_id] = []
        
        # Add current message
        self.user_message_history[user_id].append(now)
        
        # Remove old messages (older than 10 seconds)
        cutoff_time = now - timedelta(seconds=10)
        self.user_message_history[user_id] = [
            msg_time for msg_time in self.user_message_history[user_id]
            if msg_time > cutoff_time
        ]
        
        # Check if spam threshold exceeded
        if len(self.user_message_history[user_id]) > self.settings['spam_threshold']:
            return {
                'action': 'delete',
                'reason': 'spam_detected',
                'details': f'Too many messages ({len(self.user_message_history[user_id])}) in 10 seconds'
            }
        
        return {'action': 'allow', 'reason': 'spam_check_passed'}
    
    async def _check_duplicates(self, user_id: str, content: str) -> Dict[str, Any]:
        """Check for duplicate messages"""
        if not content:
            return {'action': 'allow', 'reason': 'empty_content'}
        
        # Create unique key for user+content
        key = f"{user_id}:{content}"
        now = datetime.now()
        
        if key not in self.duplicate_messages:
            self.duplicate_messages[key] = []
        
        # Add current message
        self.duplicate_messages[key].append(now)
        
        # Remove old duplicates (older than 1 minute)
        cutoff_time = now - timedelta(minutes=1)
        self.duplicate_messages[key] = [
            msg_time for msg_time in self.duplicate_messages[key]
            if msg_time > cutoff_time
        ]
        
        # Check if duplicate threshold exceeded
        if len(self.duplicate_messages[key]) >= self.settings['duplicate_threshold']:
            return {
                'action': 'delete',
                'reason': 'duplicate_detected',
                'details': f'Same message sent {len(self.duplicate_messages[key])} times'
            }
        
        return {'action': 'allow', 'reason': 'duplicate_check_passed'}
    
    async def _check_caps(self, content: str) -> Dict[str, Any]:
        """Check for excessive caps"""
        if not content or len(content) < 10:
            return {'action': 'allow', 'reason': 'message_too_short'}
        
        # Count caps
        caps_count = sum(1 for char in content if char.isupper())
        caps_percentage = (caps_count / len(content)) * 100
        
        if caps_percentage > self.settings['caps_threshold']:
            return {
                'action': 'warn',
                'reason': 'excessive_caps',
                'details': f'{caps_percentage:.1f}% caps (limit: {self.settings["caps_threshold"]}%)'
            }
        
        return {'action': 'allow', 'reason': 'caps_check_passed'}
    
    async def _check_links(self, content: str) -> Dict[str, Any]:
        """Check for unauthorized links using cached regex patterns"""
        for i, pattern in enumerate(self.link_patterns):
            cache_key = f"link_pattern_{i}"
            compiled_pattern = self._get_cached_regex(cache_key, pattern)
            
            if compiled_pattern and compiled_pattern.search(content):
                return {
                    'action': 'delete',
                    'reason': 'unauthorized_link',
                    'details': 'Links not allowed in this channel'
                }
        
        return {'action': 'allow', 'reason': 'link_check_passed'}
    
    async def _check_invites(self, content: str) -> Dict[str, Any]:
        """Check for Discord invites using cached regex patterns"""
        for i, pattern in enumerate(self.invite_patterns):
            cache_key = f"invite_pattern_{i}"
            compiled_pattern = self._get_cached_regex(cache_key, pattern)
            
            if compiled_pattern and compiled_pattern.search(content):
                return {
                    'action': 'delete',
                    'reason': 'discord_invite',
                    'details': 'Discord invites not allowed'
                }
        
        return {'action': 'allow', 'reason': 'invite_check_passed'}
    
    async def _check_profanity(self, content: str) -> Dict[str, Any]:
        """Check for profanity using cached regex patterns"""
        for i, pattern in enumerate(self.profanity_patterns):
            cache_key = f"profanity_pattern_{i}"
            compiled_pattern = self._get_cached_regex(cache_key, pattern)
            
            if compiled_pattern and compiled_pattern.search(content):
                return {
                    'action': 'delete',
                    'reason': 'profanity_detected',
                    'details': 'Message contains inappropriate language'
                }
        
        return {'action': 'allow', 'reason': 'profanity_check_passed'}
    
    async def _check_phone_numbers(self, content: str) -> Dict[str, Any]:
        """Check for phone numbers using cached regex patterns"""
        for i, pattern in enumerate(self.phone_patterns):
            cache_key = f"phone_pattern_{i}"
            compiled_pattern = self._get_cached_regex(cache_key, pattern)
            
            if compiled_pattern and compiled_pattern.search(content):
                return {
                    'action': 'delete',
                    'reason': 'phone_number_detected',
                    'details': 'Phone numbers are not allowed for privacy protection'
                }
        
        return {'action': 'allow', 'reason': 'phone_check_passed'}
    
    async def _check_addresses(self, content: str) -> Dict[str, Any]:
        """Check for home addresses using cached regex patterns"""
        for i, pattern in enumerate(self.address_patterns):
            cache_key = f"address_pattern_{i}"
            compiled_pattern = self._get_cached_regex(cache_key, pattern)
            
            if compiled_pattern and compiled_pattern.search(content):
                return {
                    'action': 'delete',
                    'reason': 'address_detected',
                    'details': 'Home addresses are not allowed for privacy protection'
                }
        
        return {'action': 'allow', 'reason': 'address_check_passed'}
    
    async def _is_user_whitelisted(self, user, message) -> bool:
        """Check if user is whitelisted to bypass automod"""
        user_id = str(user.id)
        
        # Check if user ID is directly whitelisted
        if user_id in self.whitelisted_users:
            return True
        
        # Check if user has a whitelisted role (if in a guild)
        if hasattr(message, 'guild') and message.guild and hasattr(user, 'roles'):
            user_role_ids = {str(role.id) for role in user.roles}
            if self.whitelisted_roles.intersection(user_role_ids):
                return True
        
        return False
    
    def add_user_to_whitelist(self, user_id: str):
        """Add user ID to automod whitelist"""
        self.whitelisted_users.add(str(user_id))
        print(f"AUTOMOD: Added user {user_id} to whitelist")
    
    def remove_user_from_whitelist(self, user_id: str):
        """Remove user ID from automod whitelist"""
        self.whitelisted_users.discard(str(user_id))
        print(f"AUTOMOD: Removed user {user_id} from whitelist")
    
    def add_role_to_whitelist(self, role_id: str):
        """Add role ID to automod whitelist"""
        self.whitelisted_roles.add(str(role_id))
        print(f"AUTOMOD: Added role {role_id} to whitelist")
    
    def remove_role_from_whitelist(self, role_id: str):
        """Remove role ID from automod whitelist"""
        self.whitelisted_roles.discard(str(role_id))
        print(f"AUTOMOD: Removed role {role_id} from whitelist")
    
    def get_whitelisted_users(self) -> set:
        """Get set of whitelisted user IDs"""
        return self.whitelisted_users.copy()
    
    def get_whitelisted_roles(self) -> set:
        """Get set of whitelisted role IDs"""
        return self.whitelisted_roles.copy()
    
    def clear_whitelist(self):
        """Clear all whitelist entries"""
        self.whitelisted_users.clear()
        self.whitelisted_roles.clear()
        print("AUTOMOD: Cleared all whitelist entries")
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """
        Update automod settings and invalidate cache for security
        Call this when VIP servers update their moderation rules
        """
        self.settings.update(new_settings)
        # Invalidate all cached patterns when settings change
        self._invalidate_cache()
        print(f"AUTOMOD: Settings updated, regex cache cleared for security")
    
    def add_custom_patterns(self, link_patterns: List[str] = None, invite_patterns: List[str] = None):
        """
        Add custom patterns for VIP servers and invalidate related cache
        """
        if link_patterns:
            self.link_patterns.extend(link_patterns)
            # Invalidate only link pattern cache
            for i in range(len(self.link_patterns)):
                self._invalidate_cache(f"link_pattern_{i}")
        
        if invite_patterns:
            self.invite_patterns.extend(invite_patterns)
            # Invalidate only invite pattern cache
            for i in range(len(self.invite_patterns)):
                self._invalidate_cache(f"invite_pattern_{i}")
        
        print(f"AUTOMOD: Custom patterns added, specific cache cleared")
    
    async def handle_violation(self, message, violation_info: Dict[str, Any]):
        """Handle moderation violation with automatic warning/ban system"""
        action = violation_info.get('action', 'allow')
        reason = violation_info.get('reason', 'unknown')
        user_id = str(message.author.id)
        
        try:
            # Track violation for user
            await self._track_violation(user_id, reason, message)
            
            if action == 'delete':
                await message.delete()
                print(f"🗑️ Deleted message from {message.author} for {reason}")
                
                # Send temporary removal notification
                if hasattr(message.channel, 'send'):
                    warning_msg = await message.channel.send(
                        f"{message.author.mention}, your message was removed: {reason}"
                    )
                    # Delete warning after 5 seconds
                    await asyncio.sleep(5)
                    try:
                        await warning_msg.delete()
                    except:
                        pass
                        
            elif action == 'warn':
                print(f"⚠️ Warning for {message.author}: {reason}")
                
                # Send temporary warning message
                if hasattr(message.channel, 'send'):
                    warning_msg = await message.channel.send(
                        f"{message.author.mention}, please watch your {reason.replace('_', ' ')}"
                    )
                    # Delete warning after 3 seconds
                    await asyncio.sleep(3)
                    try:
                        await warning_msg.delete()
                    except:
                        pass
                        
        except Exception as e:
            print(f"❌ Error handling moderation violation: {e}")
    
    async def _track_violation(self, user_id: str, reason: str, message):
        """Track user violations and issue warnings/bans as needed"""
        try:
            # Initialize user violation tracking
            if user_id not in self.automod_violations:
                self.automod_violations[user_id] = {
                    'count': 0,
                    'last_violation': None,
                    'violations': []
                }
            
            # Add current violation
            current_time = datetime.now()
            self.automod_violations[user_id]['count'] += 1
            self.automod_violations[user_id]['last_violation'] = current_time
            self.automod_violations[user_id]['violations'].append({
                'reason': reason,
                'timestamp': current_time,
                'channel_id': str(message.channel.id),
                'guild_id': str(message.guild.id) if message.guild else 'dm'
            })
            
            violation_count = self.automod_violations[user_id]['count']
            
            # Check if user needs formal warning (every 3 violations)
            if violation_count % self.violation_threshold == 0:
                await self._issue_formal_warning(user_id, violation_count, message)
            
            # Check if user needs service ban (after 3 warnings = 9 total violations)
            warning_count = violation_count // self.violation_threshold
            if warning_count >= self.warning_threshold:
                await self._issue_service_ban(user_id, warning_count, message)
                
        except Exception as e:
            print(f"❌ Error tracking violation for user {user_id}: {e}")
    
    async def _issue_formal_warning(self, user_id: str, violation_count: int, message):
        """Issue formal warning to database using bot's existing system"""
        try:
            warning_count = violation_count // self.violation_threshold
            reason = f"Automod violation #{violation_count} (Warning #{warning_count}): Multiple rule violations"
            
            # Create moderation data matching your existing system format
            moderation_data = {
                'action': 'warning',
                'target_user': user_id,
                'target_username': str(message.author),
                'moderator': 'automod',
                'moderator_username': 'AutoMod System',
                'reason': reason,
                'duration_hours': None,
                'guild_id': str(message.guild.id) if message.guild else 'global',
                'guild_name': message.guild.name if message.guild else 'Global Network',
                'source': 'automod_system',
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'violation_count': violation_count,
                    'warning_count': warning_count,
                    'recent_violations': [v['reason'] for v in self.automod_violations[user_id]['violations'][-3:]]
                }
            }
            
            # Add to database using MongoDB handler
            if self.db_handler:
                warning_logged = self.db_handler.add_warning(
                    user_id=str(user_id),
                    moderator_id="automod",
                    reason=reason
                )
                if warning_logged:
                    print(f"✅ AUTOMOD: Warning #{warning_count} logged to database for user {user_id}")
                else:
                    print(f"⚠️ AUTOMOD: Failed to log warning to database for user {user_id}")
                
                # Send DM notification if possible
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    if user:
                        dm_embed = discord.Embed(
                            title="⚠️ Automatic Warning",
                            description=f"You have received warning #{warning_count} from the SynapseChat moderation system.",
                            color=0xffaa00
                        )
                        dm_embed.add_field(name="Reason", value=reason, inline=False)
                        dm_embed.add_field(name="Total Violations", value=str(violation_count), inline=True)
                        dm_embed.add_field(name="Warning Number", value=f"{warning_count}/3", inline=True)
                        dm_embed.add_field(name="Next Action", value="Service ban after 3 warnings", inline=False)
                        dm_embed.set_footer(text="SynapseChat AutoMod System")
                        
                        await user.send(embed=dm_embed)
                        print(f"✅ AUTOMOD: Warning DM sent to user {user_id}")
                except Exception as e:
                    print(f"⚠️ AUTOMOD: Failed to send warning DM to user {user_id}: {e}")
            else:
                print(f"⚠️ AUTOMOD: No database handler available to log warning for user {user_id}")
                    
        except Exception as e:
            print(f"❌ Error issuing formal warning to user {user_id}: {e}")
    
    async def _issue_service_ban(self, user_id: str, warning_count: int, message):
        """Issue automatic 20-minute service ban"""
        try:
            ban_reason = f"Automod service ban: {warning_count} warnings received (automatic enforcement)"
            
            # Create ban data matching your existing system format
            ban_data = {
                'action': 'service_ban',
                'target_user': user_id,
                'target_username': str(message.author),
                'moderator': 'automod',
                'moderator_username': 'AutoMod System',
                'reason': ban_reason,
                'duration_hours': self.ban_duration_minutes / 60,  # Convert to hours
                'guild_id': str(message.guild.id) if message.guild else 'global',
                'guild_name': message.guild.name if message.guild else 'Global Network',
                'source': 'automod_system',
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'total_violations': self.automod_violations[user_id]['count'],
                    'total_warnings': warning_count,
                    'ban_duration_minutes': self.ban_duration_minutes,
                    'automatic_ban': True
                }
            }
            
            # Add ban to database using MongoDB handler
            if self.db_handler:
                ban_logged = self.db_handler.ban_user(
                    user_id=str(user_id),
                    moderator_id="automod",
                    reason=ban_reason
                )
                if ban_logged:
                    print(f"✅ AUTOMOD: {self.ban_duration_minutes}-minute service ban logged for user {user_id}")
                else:
                    print(f"⚠️ AUTOMOD: Failed to log service ban to database for user {user_id}")
                
                # Reset violation count after ban
                self.automod_violations[user_id] = {
                    'count': 0,
                    'last_violation': None,
                    'violations': []
                }
                
                # Send DM notification
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    if user:
                        ban_until = datetime.now() + timedelta(minutes=self.ban_duration_minutes)
                        dm_embed = discord.Embed(
                            title="🔨 Automatic Service Ban",
                            description=f"You have been banned from SynapseChat crosschat service for {self.ban_duration_minutes} minutes.",
                            color=0xff0000
                        )
                        dm_embed.add_field(name="Reason", value=ban_reason, inline=False)
                        dm_embed.add_field(name="Duration", value=f"{self.ban_duration_minutes} minutes", inline=True)
                        dm_embed.add_field(name="Expires", value=ban_until.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
                        dm_embed.add_field(name="Warning Count", value=f"{warning_count}/3 (limit reached)", inline=True)
                        dm_embed.add_field(name="Note", value="Your violation count has been reset. You can still use Discord normally.", inline=False)
                        dm_embed.set_footer(text="SynapseChat AutoMod System")
                        
                        await user.send(embed=dm_embed)
                        print(f"✅ AUTOMOD: Ban DM sent to user {user_id}")
                except Exception as e:
                    print(f"⚠️ AUTOMOD: Failed to send ban DM to user {user_id}: {e}")
            else:
                print(f"⚠️ AUTOMOD: No database handler available to log ban for user {user_id}")
                    
        except Exception as e:
            print(f"❌ Error issuing service ban to user {user_id}: {e}")
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update moderation settings"""
        self.settings.update(new_settings)
        print(f"🔧 Auto-moderation settings updated: {new_settings}")
    
    def enable(self):
        """Enable auto-moderation"""
        self.enabled = True
        print("✅ Auto-moderation enabled")
    
    def disable(self):
        """Disable auto-moderation"""
        self.enabled = False
        print("❌ Auto-moderation disabled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current moderation status"""
        return {
            'enabled': self.enabled,
            'settings': self.settings,
            'active_users': len(self.user_message_history),
            'tracked_duplicates': len(self.duplicate_messages)
        }

# Compatibility class for backward compatibility
class ModerationManager(AutoModerationManager):
    """Alias for backward compatibility"""
    pass