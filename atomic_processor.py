#!/usr/bin/env python3
"""
Atomic Message Processor
Uses PostgreSQL advisory locks for production-grade duplicate prevention
"""

import asyncio
import psycopg2
from database_storage_new import DatabaseStorage

class AtomicMessageProcessor:
    def __init__(self):
        self.database_storage = DatabaseStorage()
    
    async def process_message_atomically(self, message, cross_chat_manager):
        """
        Process message with atomic database-level locks
        Returns True if processed, False if duplicate
        """
        message_id = str(message.id)
        lock_id = hash(message_id) % 2147483647  # PostgreSQL bigint range
        
        conn = None
        try:
            # Get database connection
            conn = self.database_storage.get_connection()
            cursor = conn.cursor()
            
            # Acquire PostgreSQL advisory lock (atomic across all instances)
            print(f"ATOMIC_LOCK: Attempting to acquire lock {lock_id} for message {message_id}")
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
            lock_acquired = cursor.fetchone()[0]
            
            if not lock_acquired:
                print(f"ATOMIC_DUP: Message {message_id} already being processed by another instance")
                return False
            
            print(f"ATOMIC_LOCK: Lock {lock_id} acquired for message {message_id}")
            
            # Check if message already exists in database
            cursor.execute(
                "SELECT message_id FROM chat_logs WHERE message_id = %s LIMIT 1",
                (message_id,)
            )
            
            if cursor.fetchone():
                print(f"ATOMIC_DUP: Message {message_id} already exists in database")
                # Release lock before returning
                cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
                return False
            
            # Process the message (this is now atomic)
            print(f"ATOMIC_PROCESS: Processing message {message_id}")
            await cross_chat_manager.process(message)
            
            # Release the advisory lock
            cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
            print(f"ATOMIC_UNLOCK: Released lock {lock_id} for message {message_id}")
            
            return True
            
        except Exception as e:
            print(f"ATOMIC_ERROR: Error processing message {message_id}: {e}")
            
            # Ensure lock is released on error
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_id,))
                    print(f"ATOMIC_CLEANUP: Released lock {lock_id} after error")
                except:
                    pass
            
            return False
        
        finally:
            if conn:
                self.database_storage.return_connection(conn)

# Global atomic processor instance
atomic_processor = AtomicMessageProcessor()