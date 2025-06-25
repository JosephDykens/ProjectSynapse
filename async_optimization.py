"""
Async Optimization Module
Advanced async patterns for maximum bot performance
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

class AsyncOptimizer:
    """Advanced async optimization patterns for bot performance"""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="BotOptim")
        self._background_tasks = set()
        
    async def parallel_channel_distribution(self, channels: List, message_data: Dict[str, Any], 
                                          send_func: Callable) -> List[Dict[str, Any]]:
        """Distribute messages to multiple channels in parallel"""
        if not channels:
            return []
        
        # Create tasks for parallel execution
        tasks = []
        for channel in channels:
            task = asyncio.create_task(
                self._safe_channel_send(channel, message_data, send_func)
            )
            tasks.append(task)
        
        # Execute all sends simultaneously
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_sends = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"ASYNC_OPT: Failed to send to channel {channels[i]}: {result}")
            else:
                successful_sends.append(result)
        
        return successful_sends
    
    async def _safe_channel_send(self, channel, message_data: Dict[str, Any], 
                               send_func: Callable) -> Optional[Dict[str, Any]]:
        """Safely send message to a channel with error handling"""
        try:
            result = await send_func(channel, message_data)
            return {
                'channel_id': str(channel.id),
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'channel_id': str(channel.id),
                'success': False,
                'error': str(e)
            }
    
    def background_task(self, coro):
        """Execute coroutine as background task without blocking"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task
    
    async def batch_database_operations(self, operations: List[Callable], 
                                      batch_size: int = 10) -> List[Any]:
        """Execute database operations in optimized batches"""
        results = []
        
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            
            # Execute batch in thread pool to avoid blocking
            batch_tasks = [
                asyncio.get_event_loop().run_in_executor(
                    self._executor, op
                ) for op in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    async def timeout_wrapper(self, coro, timeout_seconds: float = 5.0, 
                            default_value=None):
        """Wrap coroutine with timeout for performance guarantees"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            print(f"ASYNC_OPT: Operation timed out after {timeout_seconds}s")
            return default_value
    
    async def rate_limited_execution(self, operations: List[Callable], 
                                   rate_limit: float = 0.1) -> List[Any]:
        """Execute operations with rate limiting to prevent overwhelming services"""
        results = []
        
        for operation in operations:
            start_time = time.time()
            
            try:
                result = await operation()
                results.append(result)
            except Exception as e:
                print(f"ASYNC_OPT: Rate limited operation failed: {e}")
                results.append(None)
            
            # Enforce rate limit
            elapsed = time.time() - start_time
            if elapsed < rate_limit:
                await asyncio.sleep(rate_limit - elapsed)
        
        return results
    
    def cleanup(self):
        """Clean up resources"""
        self._executor.shutdown(wait=False)
        
        # Cancel remaining background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

class MessageProcessingOptimizer:
    """Specialized optimizer for message processing pipeline"""
    
    def __init__(self):
        self.async_optimizer = AsyncOptimizer()
        self._processing_lock = asyncio.Lock()
        
    async def optimized_crosschat_send(self, channels: List, embed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimized crosschat message distribution with performance tracking"""
        start_time = time.time()
        
        async def send_to_channel(channel):
            """Send embed to single channel"""
            try:
                import discord
                
                embed = discord.Embed(
                    description=embed_data.get('description', ''),
                    color=embed_data.get('color', 0x3498db)
                )
                
                if embed_data.get('author'):
                    embed.set_author(
                        name=embed_data['author'].get('name', ''),
                        icon_url=embed_data['author'].get('icon_url', '')
                    )
                
                message = await channel.send(embed=embed)
                return message
                
            except Exception as e:
                print(f"SEND_OPT: Failed to send to {channel.id}: {e}")
                return None
        
        # Execute parallel distribution
        results = await self.async_optimizer.parallel_channel_distribution(
            channels, embed_data, send_to_channel
        )
        
        processing_time = time.time() - start_time
        
        return {
            'sent_count': len([r for r in results if r and r.get('success')]),
            'total_channels': len(channels),
            'processing_time': round(processing_time, 3),
            'results': results
        }
    
    async def batch_logging_operation(self, log_entries: List[Dict[str, Any]]) -> bool:
        """Batch multiple log entries for efficient database insertion"""
        if not log_entries:
            return True
        
        def batch_insert():
            """Synchronous batch insert operation"""
            try:
                from database_storage_new import database_storage
                
                # Batch insert multiple log entries
                conn = database_storage.get_connection()
                try:
                    with conn.cursor() as cur:
                        # Prepare batch insert
                        insert_query = """
                            INSERT INTO chat_logs 
                            (message_id, user_id, username, content, guild_id, guild_name, 
                             channel_id, channel_name, timestamp, cc_id, tag_level, tag_name, is_vip)
                            VALUES %s
                        """
                        
                        # Prepare values tuple
                        values = []
                        for entry in log_entries:
                            values.append((
                                entry.get('message_id'),
                                entry.get('user_id'),
                                entry.get('username'),
                                entry.get('content'),
                                entry.get('guild_id'),
                                entry.get('guild_name'),
                                entry.get('channel_id'),
                                entry.get('channel_name'),
                                entry.get('timestamp'),
                                entry.get('cc_id'),
                                entry.get('tag_level'),
                                entry.get('tag_name'),
                                entry.get('is_vip', False)
                            ))
                        
                        # Execute batch insert using psycopg2's execute_values
                        from psycopg2.extras import execute_values
                        execute_values(cur, insert_query, values)
                        conn.commit()
                        
                        return True
                        
                finally:
                    database_storage.return_connection(conn)
                    
            except Exception as e:
                print(f"BATCH_LOG: Failed to batch insert logs: {e}")
                return False
        
        # Execute in thread pool to avoid blocking
        result = await asyncio.get_event_loop().run_in_executor(
            self.async_optimizer._executor, batch_insert
        )
        
        return result
    
    async def smart_duplicate_check(self, message_ids: List[str]) -> Dict[str, bool]:
        """Check multiple message IDs for duplicates in single operation"""
        if not message_ids:
            return {}
        
        def batch_duplicate_check():
            """Synchronous batch duplicate check"""
            try:
                from database_storage_new import database_storage
                
                conn = database_storage.get_connection()
                try:
                    with conn.cursor() as cur:
                        # Check multiple message IDs at once
                        placeholders = ','.join(['%s'] * len(message_ids))
                        query = f"""
                            SELECT message_id FROM chat_logs 
                            WHERE message_id IN ({placeholders})
                        """
                        
                        cur.execute(query, message_ids)
                        existing_ids = {row[0] for row in cur.fetchall()}
                        
                        # Return dict mapping message_id to exists boolean
                        return {
                            msg_id: msg_id in existing_ids 
                            for msg_id in message_ids
                        }
                        
                finally:
                    database_storage.return_connection(conn)
                    
            except Exception as e:
                print(f"BATCH_DUP: Failed to check duplicates: {e}")
                # Return all as non-duplicates to allow processing
                return {msg_id: False for msg_id in message_ids}
        
        # Execute in thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            self.async_optimizer._executor, batch_duplicate_check
        )
        
        return result

# Global optimizer instances
async_optimizer = AsyncOptimizer()
message_optimizer = MessageProcessingOptimizer()