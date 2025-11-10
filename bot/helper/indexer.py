import asyncio
from datetime import datetime, timedelta, timezone
from bot.helper.database import Database
from bot.telegram import StreamBot
from bot import LOGGER
import time

db = Database()

class RateLimiter:
    """Adaptive rate limiter with exponential backoff"""
    def __init__(self, calls_per_second=18):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
        self.flood_wait_until = 0

    async def acquire(self):
        """Wait if necessary to respect rate limits"""
        now = time.time()

        # Handle flood wait
        if now < self.flood_wait_until:
            wait_time = self.flood_wait_until - now
            LOGGER.warning(f"FloodWait: sleeping {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

        # Normal rate limiting
        time_since_last = now - self.last_call
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        self.last_call = time.time()

    def set_flood_wait(self, seconds):
        """Set flood wait penalty"""
        self.flood_wait_until = time.time() + seconds
        LOGGER.error(f"FloodWait triggered: {seconds}s")

class ChannelIndexer:
    """Smart channel indexer with progress tracking"""

    def __init__(self, chat_id, batch_size=50):
        self.chat_id = int(chat_id)
        self.batch_size = batch_size
        self.rate_limiter = RateLimiter(calls_per_second=18)  # Safe limit
        self.stats = {
            "indexed": 0,
            "failed": 0,
            "start_time": None,
            "last_message_id": 0
        }

    async def get_channel_info(self):
        """Get channel total message count"""
        try:
            chat = await StreamBot.get_chat(self.chat_id)
            # Get last message to estimate total
            async for message in StreamBot.get_chat_history(self.chat_id, limit=1):
                return message.id
            return 0
        except Exception as e:
            LOGGER.error(f"Failed to get channel info: {e}")
            return 0

    async def index_batch(self, message_ids):
        """Index a batch of messages with rate limiting"""
        indexed_files = []

        for msg_id in message_ids:
            try:
                await self.rate_limiter.acquire()

                message = await StreamBot.get_messages(self.chat_id, msg_id)

                if not message:
                    continue

                file = message.video or message.document
                if not file:
                    continue

                # Extract file info
                title = file.file_name or message.caption or file.file_id
                title = title.split('.')[0] if '.' in title else title

                indexed_files.append({
                    "chat_id": str(self.chat_id),
                    "msg_id": message.id,
                    "hash": file.file_unique_id[:6],
                    "title": title,
                    "size": file.file_size,
                    "type": file.mime_type or "unknown"
                })

                self.stats["indexed"] += 1
                self.stats["last_message_id"] = msg_id

            except Exception as e:
                error_str = str(e)
                if "FloodWait" in error_str or "FLOOD_WAIT" in error_str:
                    # Extract wait time and apply
                    import re
                    match = re.search(r'(\d+)', error_str)
                    wait_seconds = int(match.group(1)) if match else 60
                    self.rate_limiter.set_flood_wait(wait_seconds + 5)
                    # Retry this message
                    await asyncio.sleep(wait_seconds + 5)
                    continue
                else:
                    self.stats["failed"] += 1
                    LOGGER.error(f"Error indexing message {msg_id}: {e}")

        # Bulk insert to database
        if indexed_files:
            try:
                await db.add_btgfiles(indexed_files)
            except Exception as e:
                LOGGER.error(f"Bulk insert error: {e}")

        return len(indexed_files)

    async def start_indexing(self, start_msg_id=1, end_msg_id=None):
        """Start full channel indexing with progress tracking"""
        self.stats["start_time"] = datetime.now(timezone.utc)

        # Get total messages if not provided
        if end_msg_id is None:
            end_msg_id = await self.get_channel_info()

        # Initialize status in database
        await db.update_index_stats(
            self.chat_id,
            total=end_msg_id,
            indexed=0,
            status="indexing"
        )

        LOGGER.info(f"Starting index: {self.chat_id}, messages: {start_msg_id}-{end_msg_id}")

        current_id = start_msg_id

        while current_id <= end_msg_id:
            batch_end = min(current_id + self.batch_size, end_msg_id + 1)
            batch_ids = list(range(current_id, batch_end))

            # Index batch
            count = await self.index_batch(batch_ids)

            # Update progress in database
            elapsed = (datetime.now(timezone.utc) - self.stats["start_time"]).total_seconds()
            rate = self.stats["indexed"] / elapsed if elapsed > 0 else 0
            remaining = end_msg_id - current_id
            eta_seconds = remaining / rate if rate > 0 else 0

            await db.update_index_stats(
                self.chat_id,
                indexed=self.stats["indexed"],
                failed=self.stats["failed"],
                last_id=current_id,
                status="indexing"
            )

            LOGGER.info(
                f"Progress: {current_id}/{end_msg_id} "
                f"({self.stats['indexed']} indexed, "
                f"ETA: {eta_seconds/60:.1f}m)"
            )

            current_id = batch_end

        # Mark as complete
        await db.update_index_stats(
            self.chat_id,
            status="completed"
        )

        LOGGER.info(
            f"Indexing complete: {self.stats['indexed']} files, "
            f"{self.stats['failed']} failed"
        )

        return self.stats

# Background indexing manager
indexing_tasks = {}

async def start_background_index(chat_id):
    """Start indexing in background"""
    if chat_id in indexing_tasks:
        return {"error": "Indexing already in progress"}

    indexer = ChannelIndexer(chat_id)
    task = asyncio.create_task(indexer.start_indexing())
    indexing_tasks[chat_id] = task

    return {"status": "started", "chat_id": chat_id}

async def stop_background_index(chat_id):
    """Stop background indexing"""
    if chat_id in indexing_tasks:
        indexing_tasks[chat_id].cancel()
        del indexing_tasks[chat_id]
        await db.update_index_stats(chat_id, status="stopped")
        return {"status": "stopped"}
    return {"error": "No indexing in progress"}
