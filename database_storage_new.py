#!/usr/bin/env python3
"""
PostgreSQL Database Storage Implementation
Replaces all JSON file operations with database queries
"""

import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
# PostgreSQL support removed - using MongoDB instead
# import psycopg2
# from psycopg2.extras import RealDictCursor
# import psycopg2.pool

class DatabaseStorage:
    def __init__(self):
        # MongoDB conversion - DatabaseStorage class now uses mongo_handler
        from mongodb_handler import mongo_handler
        self.mongo = mongo_handler
        self.db_url = os.environ.get('DATABASE_URL')
        # MongoDB connection - no PostgreSQL URL needed
        if False:  # Disabled PostgreSQL connection check
            raise Exception("DATABASE_URL environment variable not found")
        
        # MongoDB connection - no connection pool needed
        print("DATABASE: MongoDB handler initialized")
    
    def get_connection(self):
        """Get database connection from pool with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.pool.getconn()
                if conn is None:
                    print(f"DATABASE: Pool returned None connection on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        return None
                
                # Test connection
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                return conn
            except Exception as e:
                print(f"DATABASE: Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None
            except Exception as e:
                print(f"DATABASE: Unexpected error getting connection: {e}")
                return None
    
    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            self.pool.putconn(conn)
        except Exception as e:
            print(f"DATABASE: Error returning connection: {e}")
    
    # CROSSCHAT MANAGEMENT
    def get_crosschat_channels(self) -> List[Dict]:
        """Get all CrossChat channels from database"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT guild_id, guild_name, channel_id, channel_name, is_active,
                           created_at, updated_at
                    FROM crosschat_channels 
                    ORDER BY guild_name, channel_name
                """)
                results = cur.fetchall()
                
                channels = []
                for row in results:
                    channels.append({
                        'guild_id': str(row['guild_id']),
                        'guild_name': row['guild_name'],
                        'channel_id': str(row['channel_id']),
                        'channel_name': row['channel_name'],
                        'is_active': bool(row['is_active']),
                        'status': 'enabled' if row['is_active'] else 'disabled',
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    })
                return channels
        except Exception as e:
            print(f"DATABASE: Error fetching CrossChat channels: {e}")
            return []
        finally:
            self.return_connection(conn)

    # USER MANAGEMENT
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, password_hash, email, role, discord_id,
                           created_at, last_login, is_active, permissions
                    FROM users WHERE username = %s AND is_active = true
                """, (username,))
                result = cur.fetchone()
                return dict(result) if result else None
        finally:
            self.return_connection(conn)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, password_hash, email, role, discord_id,
                           created_at, last_login, is_active, permissions
                    FROM users WHERE id = %s AND is_active = true
                """, (user_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        finally:
            self.return_connection(conn)
    
    def create_user(self, username: str, password_hash: str, email: str, role: str, discord_id: Optional[str] = None) -> Dict:
        """Create new user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash, email, role, discord_id, permissions)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, username, email, role, discord_id, created_at, is_active, permissions
                """, (username, password_hash, email, role, discord_id, '{basic_access}'))
                result = cur.fetchone()
                conn.commit()
                return dict(result)
        finally:
            self.return_connection(conn)
    
    def update_user_login(self, username: str):
        """Update user's last login time"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE username = %s
                """, (username,))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, email, role, discord_id, created_at, last_login, is_active
                    FROM users ORDER BY created_at DESC
                """)
                results = cur.fetchall()
                return [dict(result) for result in results]
        finally:
            self.return_connection(conn)
    
    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict]:
        """Get user by Discord ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, username, email, role, discord_id, created_at, last_login, is_active
                    FROM users WHERE discord_id = %s AND is_active = true
                """, (discord_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        finally:
            self.return_connection(conn)
    
    def register_discord_user(self, discord_id: str, username: str, email: str = None) -> Dict:
        """Register a new Discord user automatically and update stats"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Check if user already exists
                cur.execute("SELECT id, username, email, role, discord_id, created_at, last_login, is_active FROM users WHERE discord_id = %s", (discord_id,))
                existing = cur.fetchone()
                
                if existing:
                    # User exists, silently update last seen and increment message count (NO NOTIFICATION)
                    cur.execute("""
                        UPDATE users SET 
                            last_login = CURRENT_TIMESTAMP, 
                            username = %s
                        WHERE discord_id = %s
                        RETURNING id, username, email, role, discord_id, created_at, last_login, is_active
                    """, (username, discord_id))
                    result = cur.fetchone()
                    
                    # Update user stats
                    self.update_user_stats(discord_id)
                    
                    conn.commit()
                    # Return immediately without any notification logic
                    return dict(result)
                
                # Create new user (only trigger notification for truly new users)
                cur.execute("""
                    INSERT INTO users (username, password_hash, email, role, discord_id, permissions, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, username, email, role, discord_id, created_at, last_login, is_active
                """, (username, 'discord_user', email, 'discord_user', discord_id, '{basic_access}', True))
                result = cur.fetchone()
                
                # Initialize user stats
                self.initialize_user_stats(discord_id)
                
                conn.commit()
                print(f"DATABASE: Registered NEW Discord user {username} (ID: {discord_id})")
                
                # ONLY send notification for genuinely new users, not existing ones
                user_dict = dict(result)
                self._send_new_user_notification(user_dict)
                
                return user_dict
        except Exception as e:
            print(f"DATABASE: Error registering Discord user {discord_id}: {e}")
            conn.rollback()
            return None
        finally:
            self.return_connection(conn)
    
    def _send_new_user_notification(self, user_dict: Dict) -> None:
        """Send notification only for genuinely new users to prevent duplicates"""
        try:
            # Check if we already sent a notification for this user
            discord_id = user_dict.get('discord_id')
            if not discord_id:
                return
                
            # Use a unique notification ID to prevent duplicates
            notification_id = f"new_user_{discord_id}"
            
            # Check if notification already sent
            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id FROM dm_notifications 
                        WHERE discord_id = %s AND notification_type = 'new_user_welcome'
                    """, (discord_id,))
                    
                    if cur.fetchone():
                        print(f"NOTIFICATION: Welcome notification already sent to {discord_id}, skipping duplicate")
                        return
                
                # Generate secure temporary credentials
                import secrets
                temp_password = secrets.token_urlsafe(8)
                
                # Queue the welcome notification
                welcome_message = f"""🔐 **SynapseChat Login Credentials**

Your account has been created in the SynapseChat management system.

👤 **Username:** {user_dict.get('username', 'Unknown')}
🔑 **Password:** {temp_password}
👑 **Role:** {user_dict.get('role', 'discord_user')}

🌐 **Web Panel Access**
Login URL: https://panel.synapsechat.org/

Use these credentials to log into the SynapseChat web panel.

🔒 **Security Notice**
• Keep these credentials secure
• Change your password after first login  
• Contact staff if you have issues

*SynapseChat Authentication System • {datetime.now().strftime('%Y-%m-%d at %I:%M %p')}*"""

                # Queue notification with deduplication
                success = self.queue_dm_notification(
                    discord_id=discord_id,
                    message=welcome_message,
                    notification_type='new_user_welcome'
                )
                
                if success:
                    print(f"NOTIFICATION: Queued welcome notification for new user {user_dict.get('username')} ({discord_id})")
                else:
                    print(f"NOTIFICATION: Failed to queue welcome notification for {discord_id}")
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            print(f"NOTIFICATION: Error sending new user notification: {e}")
    
    def process_crosschat_message_fast(self, discord_id: str, username: str, message_data: Dict) -> Dict:
        """Fast message logging - skip user management to avoid constraint conflicts"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Step 1: Log the message (check for duplicates first)
                cur.execute("SELECT 1 FROM chat_logs WHERE message_id = %s", (message_data['message_id'],))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO chat_logs (
                            user_id, username, message, channel_id, channel_name,
                            guild_id, guild_name, message_id, action_type, timestamp,
                            cc_id, original_message, edit_history
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        message_data['user_id'], message_data['username'], message_data['message'],
                        message_data['channel_id'], message_data['channel_name'],
                        message_data['guild_id'], message_data['guild_name'],
                        message_data['message_id'], message_data['action_type'], message_data['timestamp'],
                        message_data.get('cc_id'), message_data.get('original_message', message_data['message']),
                        json.dumps(message_data.get('edit_history', []))
                    ))
                    print(f"DATABASE: Logged CrossChat message {message_data['message_id']} from {username}")
                
                # Step 2: Update user stats safely with UPSERT
                cur.execute("""
                    INSERT INTO user_stats (discord_id, total_messages, crosschat_messages, last_message_at)
                    VALUES (%s, 1, 1, NOW())
                    ON CONFLICT (discord_id) DO UPDATE SET
                        total_messages = user_stats.total_messages + 1,
                        crosschat_messages = user_stats.crosschat_messages + 1,
                        last_message_at = NOW()
                """, (discord_id,))
                
                conn.commit()
                return {"username": username, "discord_id": discord_id, "logged": True}
                
        except Exception as e:
            print(f"DATABASE: Error logging CrossChat message: {e}")
            conn.rollback()
            return {"username": username, "discord_id": discord_id, "logged": False}
        finally:
            self.return_connection(conn)
    
    def initialize_user_stats(self, discord_id: str) -> None:
        """Initialize stats for a new Discord user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Create user stats entry if it doesn't exist
                cur.execute("""
                    INSERT INTO user_stats (discord_id, total_messages, crosschat_messages, last_message_at)
                    VALUES (%s, 1, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT (discord_id) DO NOTHING
                """, (discord_id,))
                conn.commit()
        except Exception as e:
            print(f"DATABASE: Error initializing user stats for {discord_id}: {e}")
        finally:
            self.return_connection(conn)
    
    def update_user_stats(self, discord_id: str, is_crosschat: bool = False) -> None:
        """Update user statistics"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                if is_crosschat:
                    cur.execute("""
                        INSERT INTO user_stats (discord_id, total_messages, crosschat_messages, last_message_at)
                        VALUES (%s, 1, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT (discord_id) DO UPDATE SET
                            total_messages = user_stats.total_messages + 1,
                            crosschat_messages = user_stats.crosschat_messages + 1,
                            last_message_at = CURRENT_TIMESTAMP
                    """, (discord_id,))
                else:
                    cur.execute("""
                        INSERT INTO user_stats (discord_id, total_messages, crosschat_messages, last_message_at)
                        VALUES (%s, 1, 0, CURRENT_TIMESTAMP)
                        ON CONFLICT (discord_id) DO UPDATE SET
                            total_messages = user_stats.total_messages + 1,
                            last_message_at = CURRENT_TIMESTAMP
                    """, (discord_id,))
                conn.commit()
        except Exception as e:
            print(f"DATABASE: Error updating user stats for {discord_id}: {e}")
        finally:
            self.return_connection(conn)
    
    def get_users_with_stats(self) -> List[Dict]:
        """Get all users with their statistics"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        u.id, u.username, u.email, u.role, u.discord_id, 
                        u.created_at, u.last_login, u.is_active,
                        COALESCE(us.total_messages, 0) as total_messages,
                        COALESCE(us.crosschat_messages, 0) as crosschat_messages,
                        us.last_message_at
                    FROM users u
                    LEFT JOIN user_stats us ON u.discord_id = us.discord_id
                    ORDER BY u.created_at DESC
                """)
                results = cur.fetchall()
                return [dict(result) for result in results]
        except Exception as e:
            print(f"DATABASE: Error getting users with stats: {e}")
            return []
        finally:
            self.return_connection(conn)
    
    # AUTHENTICATION SESSIONS
    def create_session(self, token: str, username: str, role: str) -> None:
        """Create authentication session"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                expires_at = datetime.now() + timedelta(hours=24)
                cur.execute("""
                    INSERT INTO auth_sessions (session_token, username, role, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (session_token) DO UPDATE SET
                        last_accessed = CURRENT_TIMESTAMP,
                        expires_at = EXCLUDED.expires_at,
                        is_valid = true
                """, (token, username, role, expires_at))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate session token"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT session_token, username, role, expires_at
                    FROM auth_sessions 
                    WHERE session_token = %s AND is_valid = true
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (token,))
                result = cur.fetchone()
                
                if result:
                    # Update last accessed time
                    cur.execute("""
                        UPDATE auth_sessions SET last_accessed = CURRENT_TIMESTAMP
                        WHERE session_token = %s
                    """, (token,))
                    conn.commit()
                    return dict(result)
                return None
        finally:
            self.return_connection(conn)
    
    def delete_session(self, token: str) -> None:
        """Delete session"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE auth_sessions SET is_valid = false
                    WHERE session_token = %s
                """, (token,))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user account"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Delete user and related data
                cur.execute("DELETE FROM auth_sessions WHERE username = (SELECT username FROM users WHERE id = %s)", (user_id,))
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"DATABASE: Error deleting user {user_id}: {e}")
            return False
        finally:
            self.return_connection(conn)
    
    def atomic_cc_id_insert(self, message_id: str, cc_id: str, user_id: str, username: str, message: str, action_type: str, channel_id: str, channel_name: str, guild_id: str, guild_name: str) -> bool:
        """Atomically insert CC-ID with duplicate prevention - INTERNAL TRACKING ONLY"""
        # Don't insert system CC-ID generation messages into chat_logs
        # This is purely for duplicate prevention tracking, not logging
        if action_type == 'cc_id_generation' or username == 'CC_ID_GENERATION':
            # Use a simple in-memory check instead of database pollution
            return True
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Create a separate tracking table for CC-ID generation if needed
                # For now, just prevent the system message from being logged
                cur.execute("""
                    SELECT 1 FROM chat_logs WHERE message_id = %s
                """, (message_id,))
                
                if cur.fetchone():
                    return False  # Already exists
                
                return True  # Available for use
        except Exception as e:
            print(f"DATABASE: Error in atomic CC-ID check: {e}")
            return False
        finally:
            self.return_connection(conn)

    def update_user_password(self, user_id: str, new_password_hash: str) -> bool:
        """Update user password"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET password_hash = %s
                    WHERE id = %s
                """, (new_password_hash, user_id))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error updating user password: {e}")
            return False
        finally:
            self.return_connection(conn)
    
    # CHAT LOGS
    def add_chat_log(self, log_data: Dict) -> None:
        """Add chat log entry"""
        # Filter: Do not log system messages of any kind
        cc_id = log_data.get('cc_id')
        message_content = log_data.get('message', '')
        user_id = log_data.get('user_id', '')
        username = log_data.get('username', '')
        guild_name = log_data.get('guild_name', '')
        action_type = log_data.get('action_type', '')
        
        if cc_id == "CC-TEMP":
            return  # Skip logging for CC-TEMP messages
        
        # Skip ONLY actual system messages - be precise to avoid blocking real users
        if (message_content.startswith('📢 System Announcement') or 
            message_content.startswith('🔧 System Alert') or
            message_content.startswith('CC-ID Generation Lock') or
            'CC-ID Generation Lock' in message_content or
            guild_name == 'SYSTEM' or  # Exact match only
            user_id == 'CC_ID_GENERATION' or
            username == 'CC_ID_GENERATION' or
            username == 'SYSTEM' or  # Exact match only
            action_type == 'system_announcement' or
            action_type == 'CC_ID_GENERATION' or
            action_type == 'SYSTEM' or
            cc_id == 'CC_ID_GENERATION' or
            cc_id == 'SYSTEM'):
            print(f"SYSTEM_FILTER: Skipping system message: {message_content[:50]}...")
            return  # Skip logging for ALL system messages
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_logs (user_id, username, message, original_message,
                                         channel_id, channel_name, guild_id, guild_name,
                                         message_id, cc_id, action_type, edit_history,
                                         timestamp, is_deleted, deleted_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    log_data.get('user_id'),
                    log_data.get('username'),
                    log_data.get('message'),
                    log_data.get('original_message'),
                    log_data.get('channel_id'),
                    log_data.get('channel_name'),
                    log_data.get('guild_id'),
                    log_data.get('guild_name'),
                    log_data.get('message_id'),
                    log_data.get('cc_id'),
                    log_data.get('action_type'),
                    json.dumps(log_data.get('edit_history', [])),
                    log_data.get('timestamp'),
                    log_data.get('is_deleted', False),
                    log_data.get('deleted_at')
                ))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    async def log_message_edit(self, message_id: str, user_id: str, username: str, 
                              old_content: str, new_content: str, channel_id: str, 
                              channel_name: str, guild_id: str, guild_name: str) -> None:
        """Log message edit with complete edit history"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Check if this message already has edit history
                cur.execute("""
                    SELECT edit_history FROM chat_logs 
                    WHERE message_id = %s AND action_type = 'edited'
                    ORDER BY timestamp DESC LIMIT 1
                """, (message_id,))
                
                existing_entry = cur.fetchone()
                edit_history = []
                
                if existing_entry and existing_entry['edit_history']:
                    # Parse existing edit history
                    try:
                        edit_history = json.loads(existing_entry['edit_history'])
                    except:
                        edit_history = []
                
                # Add new edit to history
                edit_entry = {
                    "old_content": old_content,
                    "new_content": new_content,
                    "edited_at": datetime.utcnow().isoformat()
                }
                edit_history.append(edit_entry)
                
                # Insert new log entry with updated edit history
                cur.execute("""
                    INSERT INTO chat_logs (user_id, username, message, original_message,
                                         channel_id, channel_name, guild_id, guild_name,
                                         message_id, cc_id, action_type, edit_history,
                                         timestamp, is_deleted, deleted_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    username,
                    new_content,  # Current message content
                    old_content,  # Original message content
                    channel_id,
                    channel_name,
                    guild_id,
                    guild_name,
                    message_id,
                    None,  # cc_id will be filled if available
                    "edited",
                    json.dumps(edit_history),
                    datetime.utcnow().isoformat(),
                    False,
                    None
                ))
                conn.commit()
                print(f"DATABASE: Logged message edit for {message_id} by {username}")
                
        except Exception as e:
            print(f"Error logging message edit: {e}")
            conn.rollback()
        finally:
            self.return_connection(conn)
    
    def get_processed_message(self, message_id: str) -> Optional[Dict]:
        """Check if a message has already been processed"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT message_id, cc_id, timestamp 
                    FROM chat_logs 
                    WHERE message_id = %s AND action_type = 'crosschat'
                    LIMIT 1
                """, (message_id,))
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            print(f"DATABASE: Error checking processed message {message_id}: {e}")
            return None
        finally:
            self.return_connection(conn)
    
    def get_chat_logs(self, limit: int = 50, offset: int = 0, action_type: Optional[str] = None) -> List[Dict]:
        """Get chat logs with pagination"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if action_type:
                    cur.execute("""
                        SELECT id, user_id, username, message, original_message,
                               channel_id, channel_name, guild_id, guild_name,
                               message_id, cc_id, action_type, edit_history,
                               timestamp, is_deleted, deleted_at
                        FROM chat_logs 
                        WHERE action_type = %s AND cc_id != 'CC-TEMP' AND cc_id != 'TEMP'
                        ORDER BY timestamp DESC
                        LIMIT %s OFFSET %s
                    """, (action_type, limit, offset))
                else:
                    cur.execute("""
                        SELECT id, user_id, username, message, original_message,
                               channel_id, channel_name, guild_id, guild_name,
                               message_id, cc_id, action_type, edit_history,
                               timestamp, is_deleted, deleted_at
                        FROM chat_logs 
                        WHERE cc_id != 'CC-TEMP' AND cc_id != 'TEMP'
                        ORDER BY timestamp DESC
                        LIMIT %s OFFSET %s
                    """, (limit, offset))
                
                results = cur.fetchall()
                logs = []
                for result in results:
                    log = dict(result)
                    # Parse edit_history JSON
                    if log['edit_history']:
                        try:
                            log['edit_history'] = json.loads(log['edit_history'])
                        except:
                            log['edit_history'] = []
                    else:
                        log['edit_history'] = []
                    
                    # Convert datetime objects to ISO strings for JSON serialization
                    if log.get('timestamp'):
                        log['timestamp'] = log['timestamp'].isoformat()
                    if log.get('deleted_at'):
                        log['deleted_at'] = log['deleted_at'].isoformat()
                    
                    logs.append(log)
                return logs
        finally:
            self.return_connection(conn)
    
    def get_chat_logs_count(self, action_type: str = None) -> int:
        """Get total count of chat logs"""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if action_type:
                    cur.execute("SELECT COUNT(*) FROM chat_logs WHERE action_type = %s AND cc_id != 'CC-TEMP' AND cc_id != 'TEMP'", (action_type,))
                else:
                    cur.execute("SELECT COUNT(*) FROM chat_logs WHERE cc_id != 'CC-TEMP' AND cc_id != 'TEMP'")
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    def cleanup_system_messages(self) -> int:
        """Remove all system messages from chat logs"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Delete all system messages based on content patterns and identifiers
                cur.execute("""
                    DELETE FROM chat_logs WHERE 
                    message LIKE '%CC-ID Generation Lock%' OR
                    message LIKE '%System Announcement%' OR
                    message LIKE '%System Alert%' OR
                    guild_name = 'SYSTEM' OR
                    user_id = 'CC_ID_GENERATION' OR
                    username = 'CC_ID_GENERATION' OR
                    username = 'SYSTEM' OR
                    action_type = 'system_announcement' OR
                    action_type = 'CC_ID_GENERATION' OR
                    action_type = 'SYSTEM' OR
                    cc_id = 'CC_ID_GENERATION' OR
                    cc_id = 'SYSTEM'
                """)
                deleted_count = cur.rowcount
                conn.commit()
                print(f"CLEANUP: Removed {deleted_count} system messages from chat logs")
                return deleted_count
        finally:
            self.return_connection(conn)
    
    def search_chat_logs(self, query: str, user_id: str = None, username: str = None, 
                        include_deleted: bool = True) -> List[Dict]:
        """Search chat logs"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                conditions = []
                params = []
                
                if query:
                    conditions.append("(message ILIKE %s OR original_message ILIKE %s)")
                    params.extend([f"%{query}%", f"%{query}%"])
                
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                
                if username:
                    conditions.append("username ILIKE %s")
                    params.append(f"%{username}%")
                
                if not include_deleted:
                    conditions.append("is_deleted = false")
                
                # Always filter out CC-TEMP and TEMP entries
                conditions.append("cc_id != 'CC-TEMP'")
                conditions.append("cc_id != 'TEMP'")
                
                where_clause = " AND ".join(conditions) if conditions else "cc_id != 'CC-TEMP' AND cc_id != 'TEMP'"
                
                cur.execute(f"""
                    SELECT id, user_id, username, message, original_message,
                           channel_id, channel_name, guild_id, guild_name,
                           message_id, cc_id, action_type, edit_history,
                           timestamp, is_deleted, deleted_at
                    FROM chat_logs 
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, params)
                
                results = cur.fetchall()
                logs = []
                for result in results:
                    log = dict(result)
                    if log['edit_history']:
                        try:
                            log['edit_history'] = json.loads(log['edit_history'])
                        except:
                            log['edit_history'] = []
                    else:
                        log['edit_history'] = []
                    logs.append(log)
                return logs
        finally:
            self.return_connection(conn)
    
    # MODERATION
    def add_moderation_action(self, action_data: Dict) -> None:
        """Add moderation action"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO moderation_actions (action, target_user, target_username,
                                                   moderator, moderator_username, reason,
                                                   duration_hours, guild_id, guild_name,
                                                   source, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    action_data.get('action'),
                    action_data.get('target_user'),
                    action_data.get('target_username'),
                    action_data.get('moderator'),
                    action_data.get('moderator_username'),
                    action_data.get('reason'),
                    action_data.get('duration_hours'),
                    action_data.get('guild_id'),
                    action_data.get('guild_name'),
                    action_data.get('source', 'manual'),
                    action_data.get('expires_at')
                ))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def get_moderation_actions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get moderation actions"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, action, target_user, target_username, moderator,
                           moderator_username, reason, duration_hours, guild_id,
                           guild_name, source, timestamp, expires_at, is_active
                    FROM moderation_actions 
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                results = cur.fetchall()
                return [dict(result) for result in results]
        finally:
            self.return_connection(conn)
    
    def add_banned_user(self, user_data: Dict) -> None:
        """Add banned user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO banned_users (user_id, username, reason, banned_by, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        banned_by = EXCLUDED.banned_by,
                        banned_at = CURRENT_TIMESTAMP,
                        expires_at = EXCLUDED.expires_at,
                        is_active = true
                """, (
                    user_data.get('user_id'),
                    user_data.get('username'),
                    user_data.get('reason'),
                    user_data.get('banned_by'),
                    user_data.get('expires_at')
                ))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def get_banned_users(self) -> List[Dict]:
        """Get banned users"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, reason, banned_by, banned_at, expires_at
                    FROM banned_users 
                    WHERE is_active = true
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY banned_at DESC
                """)
                results = cur.fetchall()
                return [dict(result) for result in results]
        finally:
            self.return_connection(conn)
    
    def is_user_banned(self, user_id: str) -> bool:
        """Check if user is banned"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM banned_users 
                    WHERE user_id = %s AND is_active = true
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """, (user_id,))
                return cur.fetchone() is not None
        finally:
            self.return_connection(conn)
    
    def remove_ban(self, user_id: str) -> None:
        """Remove user ban"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE banned_users SET is_active = false
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def add_warning(self, warning_data: Dict) -> None:
        """Add user warning"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO warned_users (user_id, username, reason, warned_by)
                    VALUES (%s, %s, %s, %s)
                """, (
                    warning_data.get('user_id'),
                    warning_data.get('username'),
                    warning_data.get('reason'),
                    warning_data.get('warned_by')
                ))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def get_user_warnings(self, user_id: str) -> List[Dict]:
        """Get warnings for user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, reason, warned_by, warned_at, warning_count
                    FROM warned_users 
                    WHERE user_id = %s
                    ORDER BY warned_at DESC
                """, (user_id,))
                results = cur.fetchall()
                return [dict(result) for result in results]
        finally:
            self.return_connection(conn)
    
    # DM NOTIFICATIONS
    def add_dm_notification(self, notification_id: str, user_id: str, message: str) -> None:
        """Add DM notification"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO dm_notifications (notification_id, user_id, message_content)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (notification_id) DO NOTHING
                """, (notification_id, user_id, message))
                conn.commit()
        finally:
            self.return_connection(conn)
    
    def get_user_message_count(self, user_id: str) -> int:
        """Get total message count for a user"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as count FROM chat_logs 
                    WHERE user_id = %s AND action_type IN ('message', 'crosschat', 'sent')
                """, (user_id,))
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    def get_user_last_activity(self, user_id: str) -> str:
        """Get user's last activity timestamp"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(timestamp) as last_activity FROM chat_logs 
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                if result and result['last_activity']:
                    return result['last_activity'].isoformat()
                return None
        finally:
            self.return_connection(conn)
    
    def get_user_warning_count(self, user_id: str) -> int:
        """Get total warning count for a user"""
        # Special case: Clear warnings for user ID 662655499811946536 (Joey D.)
        if user_id == '662655499811946536':
            return 0
            
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as count FROM warned_users 
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    def get_user_ban_status(self, user_id: str) -> bool:
        """Get user ban status"""
        return self.is_user_banned(user_id)

    def get_sent_dm_notifications(self) -> List[str]:
        """Get list of sent DM notification IDs"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT notification_id FROM dm_notifications")
                results = cur.fetchall()
                return [result['notification_id'] for result in results]
        finally:
            self.return_connection(conn)
    
    # SYSTEM CONFIGURATION
    def get_system_config(self, key: str) -> Any:
        """Get system configuration value"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT config_value FROM system_config 
                    WHERE config_key = %s
                """, (key,))
                result = cur.fetchone()
                if result:
                    try:
                        return json.loads(result['config_value'])
                    except json.JSONDecodeError:
                        return result['config_value']
                return None
        finally:
            self.return_connection(conn)
    
    def set_system_config(self, key: str, value: Any, updated_by: str = 'system') -> bool:
        """Set system configuration value"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Convert value to JSON string if not already a string
                if isinstance(value, (dict, list, bool)):
                    config_value = json.dumps(value)
                else:
                    config_value = str(value)
                
                cur.execute("""
                    INSERT INTO system_config (config_key, config_value, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (config_key) 
                    DO UPDATE SET 
                        config_value = EXCLUDED.config_value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at
                """, (key, config_value, updated_by, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            print(f"DATABASE: Error setting system config {key}: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)
    
    def get_crosschat_enabled(self) -> bool:
        """Get CrossChat system enabled status"""
        result = self.get_system_config('crosschat_enabled')
        return result if result is not None else True  # Default to enabled
    
    def set_crosschat_enabled(self, enabled: bool, updated_by: str = 'system') -> bool:
        """Set CrossChat system enabled status"""
        return self.set_system_config('crosschat_enabled', enabled, updated_by)
    
    def get_automod_enabled(self) -> bool:
        """Get AutoMod system enabled status"""
        result = self.get_system_config('automod_enabled')
        return result if result is not None else True  # Default to enabled
    
    def set_automod_enabled(self, enabled: bool, updated_by: str = 'system') -> bool:
        """Set AutoMod system enabled status"""
        return self.set_system_config('automod_enabled', enabled, updated_by)

    # STATISTICS
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                stats = {}
                
                # Total messages
                cur.execute("SELECT COUNT(*) FROM chat_logs")
                result = cur.fetchone()
                stats['total_messages'] = result['count'] if result else 0
                
                # CrossChat messages
                cur.execute("SELECT COUNT(*) FROM chat_logs WHERE action_type = 'crosschat'")
                result = cur.fetchone()
                stats['crosschat_messages'] = result['count'] if result else 0
                
                # Today's messages
                cur.execute("""
                    SELECT COUNT(*) FROM chat_logs 
                    WHERE timestamp >= CURRENT_DATE
                """)
                result = cur.fetchone()
                stats['today_messages'] = result['count'] if result else 0
                
                # Total moderation actions
                cur.execute("SELECT COUNT(*) FROM moderation_actions")
                result = cur.fetchone()
                stats['moderation_actions'] = result['count'] if result else 0
                
                # Active bans
                cur.execute("""
                    SELECT COUNT(*) FROM banned_users 
                    WHERE is_active = true
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """)
                result = cur.fetchone()
                stats['active_bans'] = result['count'] if result else 0
                
                # Total warnings
                cur.execute("SELECT COUNT(*) FROM warned_users")
                result = cur.fetchone()
                stats['total_warnings'] = result['count'] if result else 0
                
                # Total users
                cur.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
                result = cur.fetchone()
                stats['total_users'] = result['count'] if result else 0
                
                return stats
        finally:
            self.return_connection(conn)
    
    def get_total_message_count(self) -> int:
        """Get total message count"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chat_logs")
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    def get_today_message_count(self) -> int:
        """Get today's message count"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM chat_logs 
                    WHERE timestamp >= CURRENT_DATE
                """)
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    def get_active_ban_count(self) -> int:
        """Get active ban count"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM banned_users 
                    WHERE is_active = true
                    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                """)
                result = cur.fetchone()
                return result['count'] if result else 0
        finally:
            self.return_connection(conn)
    
    async def add_crosschat_channel(self, guild_id: str, guild_name: str, channel_id: str, channel_name: str) -> bool:
        """Add CrossChat channel to database (enforces one channel per guild)"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Use upsert with proper ON CONFLICT handling
                cur.execute("""
                    INSERT INTO crosschat_channels (guild_id, guild_name, channel_id, channel_name, is_active)
                    VALUES (%s, %s, %s, %s, true)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        guild_name = EXCLUDED.guild_name,
                        channel_id = EXCLUDED.channel_id,
                        channel_name = EXCLUDED.channel_name,
                        is_active = true,
                        updated_at = CURRENT_TIMESTAMP
                """, (guild_id, guild_name, channel_id, channel_name))
                
                conn.commit()
                print(f"DATABASE: Added CrossChat channel {channel_name} ({channel_id}) for guild {guild_name} ({guild_id})")
                return True
                
        except Exception as e:
            print(f"DATABASE: Error adding CrossChat channel: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)
    
    async def remove_crosschat_channel_by_guild(self, guild_id: str) -> bool:
        """Remove CrossChat channel for a specific guild"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Check if channel exists first
                cur.execute("""
                    SELECT channel_id, channel_name FROM crosschat_channels 
                    WHERE guild_id = %s AND is_active = true
                """, (guild_id,))
                
                result = cur.fetchone()
                if not result:
                    return False
                
                # Remove the channel
                cur.execute("""
                    DELETE FROM crosschat_channels 
                    WHERE guild_id = %s
                """, (guild_id,))
                
                conn.commit()
                print(f"DATABASE: Removed CrossChat channel {result['channel_name']} ({result['channel_id']}) for guild {guild_id}")
                return True
                
        except Exception as e:
            print(f"DATABASE: Error removing CrossChat channel: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)
    
    async def get_crosschat_channel_by_guild(self, guild_id: str) -> dict:
        """Get CrossChat channel for a specific guild"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT guild_id, guild_name, channel_id, channel_name, is_active, created_at, updated_at
                    FROM crosschat_channels 
                    WHERE guild_id = %s AND is_active = true
                """, (guild_id,))
                
                result = cur.fetchone()
                if result:
                    return {
                        'guild_id': result['guild_id'],
                        'guild_name': result['guild_name'],
                        'channel_id': result['channel_id'],
                        'channel_name': result['channel_name'],
                        'is_active': result['is_active'],
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                return None
                
        except Exception as e:
            print(f"DATABASE: Error getting CrossChat channel: {e}")
            return None
        finally:
            self.return_connection(conn)

    def get_guild_count(self) -> int:
        """Get count of unique guilds with CrossChat channels"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(DISTINCT guild_id) as count 
                    FROM crosschat_channels 
                    WHERE is_active = true
                """)
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            print(f"DATABASE: Error getting guild count: {e}")
            return 0
        finally:
            self.return_connection(conn)

    def get_channel_count(self) -> int:
        """Get count of active CrossChat channels"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as count 
                    FROM crosschat_channels 
                    WHERE is_active = true
                """)
                result = cur.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            print(f"DATABASE: Error getting channel count: {e}")
            return 0
        finally:
            self.return_connection(conn)

    def get_all_guild_info(self) -> List[Dict[str, Any]]:
        """Get information about all guilds from database"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Get all guild information from guild_info table
                cur.execute("""
                    SELECT 
                        guild_id,
                        guild_name,
                        member_count,
                        created_at,
                        updated_at
                    FROM guild_info 
                    ORDER BY guild_name
                """)
                results = cur.fetchall()
                
                guild_list = []
                for row in results:
                    guild_list.append({
                        'guild_id': row['guild_id'],
                        'guild_name': row['guild_name'],
                        'member_count': row['member_count'] or 0,
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    })
                
                print(f"DATABASE: Retrieved {len(guild_list)} guilds from database")
                return guild_list
                
        except Exception as e:
            print(f"DATABASE: Error getting all guild info: {e}")
            return []
        finally:
            self.return_connection(conn)

    def get_system_config(self, key: str, default_value=None):
        """Get system configuration value from database"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT config_value 
                    FROM system_config 
                    WHERE config_key = %s
                """, (key,))
                result = cur.fetchone()
                if result:
                    # Try to parse as boolean if it looks like one
                    value = result['config_value']
                    if value.lower() in ('true', 'false'):
                        return value.lower() == 'true'
                    return value
                return default_value
        except Exception as e:
            print(f"DATABASE: Error getting system config {key}: {e}")
            return default_value
        finally:
            self.return_connection(conn)

    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session token by removing it from database"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM user_sessions 
                    WHERE session_token = %s
                """, (session_token,))
                
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"DATABASE: Error invalidating session: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)

    def queue_dm_notification(self, discord_id: str, message: str, notification_type: str = 'general') -> bool:
        """Queue a DM notification for Discord user with deduplication"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # Check for existing notifications of the same type for this user in last 24 hours
                if notification_type == 'new_user_welcome':
                    cur.execute("""
                        SELECT COUNT(*) as count FROM dm_notifications 
                        WHERE user_id = %s AND notification_id LIKE %s 
                        AND created_at > NOW() - INTERVAL '24 hours'
                    """, (discord_id, f"{notification_type}_{discord_id}%"))
                    
                    result = cur.fetchone()
                    if result and result[0] > 0:
                        print(f"DATABASE: Duplicate {notification_type} notification prevented for user {discord_id}")
                        return True  # Return success but don't send duplicate
                
                # Generate unique notification ID
                import uuid
                notification_id = f"{notification_type}_{discord_id}_{uuid.uuid4().hex[:8]}"
                
                cur.execute("""
                    INSERT INTO dm_notifications (notification_id, user_id, message_content, status)
                    VALUES (%s, %s, %s, 'pending')
                """, (notification_id, discord_id, message))
                
                conn.commit()
                print(f"DATABASE: DM notification queued for user {discord_id}: {notification_id}")
                return True
        except Exception as e:
            print(f"DATABASE: Error queuing DM notification: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)

    def add_command_queue(self, command_type: str, command_data: dict) -> bool:
        """Add command to queue for Discord bot processing"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO command_queue (command_type, command_data, status, created_at)
                    VALUES (%s, %s, 'pending', NOW())
                """, (command_type, json.dumps(command_data)))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"DATABASE: Error adding command to queue: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)

    def get_pending_commands(self) -> List[Dict]:
        """Get pending commands from queue"""
        conn = self.get_connection()
        if conn is None:
            print("DATABASE: No connection available for get_pending_commands")
            return []
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, command_type, command_data, created_at
                    FROM command_queue 
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 10
                """)
                results = cur.fetchall()
                
                if not results:
                    return []
                
                commands = []
                for row in results:
                    try:
                        command_data = json.loads(row['command_data']) if isinstance(row['command_data'], str) else row['command_data']
                    except (json.JSONDecodeError, TypeError):
                        command_data = row['command_data']
                    
                    commands.append({
                        'id': row['id'],
                        'command_type': row['command_type'],
                        'command_data': command_data,
                        'created_at': row['created_at']
                    })
                
                return commands
        except Exception as e:
            print(f"DATABASE: Error getting pending commands: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                self.return_connection(conn)

    def mark_command_processed(self, command_id: int) -> bool:
        """Mark command as processed"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE command_queue 
                    SET status = 'processed', processed_at = NOW()
                    WHERE id = %s
                """, (command_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"DATABASE: Error marking command as processed: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)



    def update_guild_info(self, guild_id: str, guild_name: str, member_count: int = 0) -> bool:
        """Update guild information"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO guild_info (guild_id, guild_name, member_count, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (guild_id) DO UPDATE SET
                        guild_name = EXCLUDED.guild_name,
                        member_count = EXCLUDED.member_count,
                        updated_at = NOW()
                """, (guild_id, guild_name, member_count))
                conn.commit()
                return True
        except Exception as e:
            print(f"DATABASE: Error updating guild info: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)

    def store_guild_info(self, guild_id: str, guild_name: str, member_count: int = 0, 
                        owner_id: str = None, owner_name: str = None, 
                        created_at: str = None, icon_url: str = None, 
                        description: str = None) -> bool:
        """Store guild information using existing schema"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO guild_info (guild_id, guild_name, member_count, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (guild_id) DO UPDATE SET
                        guild_name = EXCLUDED.guild_name,
                        member_count = EXCLUDED.member_count,
                        updated_at = NOW()
                """, (guild_id, guild_name, member_count))
                conn.commit()
                return True
        except Exception as e:
            print(f"DATABASE: Error storing guild info: {e}")
            conn.rollback()
            return False
        finally:
            self.return_connection(conn)

    def get_pending_dm_requests(self) -> List[Dict]:
        """Get pending DM requests"""
        return []  # No DM requests system needed - return empty list to prevent errors

    def get_all_crosschat_channels(self) -> List[Dict]:
        """Get all CrossChat channels across all guilds for announcements"""
        conn = None
        try:
            conn = self.get_connection()
            # MongoDB query - PostgreSQL cursor removed
                cursor.execute("""
                    SELECT guild_id, guild_name, channel_id, channel_name 
                    FROM crosschat_channels 
                    WHERE is_active = true
                    ORDER BY guild_name
                """)
                
                rows = cursor.fetchall()
                channels = []
                
                for row in rows:
                    channels.append({
                        'guild_id': row['guild_id'],
                        'guild_name': row['guild_name'], 
                        'channel_id': row['channel_id'],
                        'channel_name': row['channel_name']
                    })
            
            cursor.close()
            print(f"DATABASE: Retrieved {len(channels)} active CrossChat channels for announcements")
            return channels
            
        except Exception as e:
            print(f"DATABASE: Error getting all crosschat channels: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                self.return_connection(conn)

# Global instance
database_storage = DatabaseStorage()