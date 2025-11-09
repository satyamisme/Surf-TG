import re
import datetime
from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.helper.file_size import get_readable_file_size
from bot.helper.index import get_messages
from bot.helper.media import is_media
from bot.telegram import StreamBot
from pyrogram import filters, Client
from pyrogram.types import Message
from os.path import splitext
from pyrogram.errors import FloodWait
from pyrogram.enums.parse_mode import ParseMode
from asyncio import sleep

db = Database()

@StreamBot.on_message(filters.command('reindex') & filters.private)
async def reindex_command(bot: Client, message: Message):
    """Complete reindexing of a channel"""
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]

    if str(channel_id) in AUTH_CHANNEL:
        try:
            last_id = message.id
            start_message = (
                "🔄 Starting complete reindexing of this channel...\n\n"
                "📋 This will update all files in the database to match the current channel state.\n\n"
                "🗑️ Files that no longer exist in the channel will be removed from database.\n\n"
                "⏳ This may take a while depending on channel size..."
            )

            wait_msg = await message.reply(text=start_message)

            # Get all current files from the channel
            files = await get_messages(message.chat.id, 1, last_id)

            # Perform complete reindex
            await db.reindex_channel(str(channel_id), files)

            await wait_msg.delete()
            done_message = (
                "✅ Channel reindexing completed successfully!\n\n"
                f"📁 Updated database with {len(files)} current files.\n\n"
                "🗃️ Database now matches the current channel state."
            )

            await bot.send_message(chat_id=message.chat.id, text=done_message)

        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
            await message.reply(text=f"Got Floodwait of {str(e.value)}s",
                              disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            LOGGER.error(f"Reindex error: {e}")
            await message.reply(text=f"Reindex failed: {str(e)}")
    else:
        await message.reply(text="Channel is not in AUTH_CHANNEL")

@StreamBot.on_message(filters.command('index'))
async def start(bot: Client, message: Message):
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]

    if str(channel_id) in AUTH_CHANNEL:
        try:
            last_id = message.id
            start_message = (
                "🔄 Starting file indexing...\n\n"
                "📋 File listing is currently in progress.\n\n"
                "🔄 Existing files will be updated, new files will be added.\n\n"
                "⏳ Please be patient and wait a few moments."
            )

            wait_msg = await message.reply(text=start_message)

            # Get all files from the channel
            files = await get_messages(message.chat.id, 1, last_id)

            # Use bulk update/insert instead of simple insert
            await db.add_btgfiles(files)

            await wait_msg.delete()
            done_message = (
                "✅ File indexing completed successfully!\n\n"
                f"📁 Processed {len(files)} files.\n\n"
                "🔄 Existing files were updated, new files were added to database."
            )

            await bot.send_message(chat_id=message.chat.id, text=done_message)

        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
            await message.reply(text=f"Got Floodwait of {str(e.value)}s",
                              disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(text="Channel is not in AUTH_CHANNEL")

@StreamBot.on_message(
    filters.channel
    & (
        filters.document
        | filters.video
        | filters.photo
        | filters.audio
    )
)
async def file_receive_handler(bot: Client, message: Message):
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]

    if str(channel_id) in AUTH_CHANNEL:
        try:
            # Handle different media types
            file = (message.video or message.document or
                   message.audio or message.photo)

            if not file:
                return

            # For photos, get the largest size
            if message.photo:
                file = message.photo.sizes[-1]  # Largest photo size
                file_name = f"photo_{message.id}.jpg"
                file_size = file.file_size
                mime_type = "image/jpeg"
            else:
                file_name = file.file_name or message.caption or file.file_id
                file_size = file.file_size
                mime_type = file.mime_type

            title, _ = splitext(file_name)
            title = re.sub(r'[.,|_\',]', ' ', title).strip()
            msg_id = message.id
            file_hash = file.file_unique_id[:6]
            size = get_readable_file_size(file_size)
            file_type = mime_type

            # Auto-update database with new file
            success = await db.add_tgfiles(
                str(channel_id), str(msg_id), str(file_hash),
                str(title), str(size), str(file_type)
            )

            if success:
                LOGGER.info(f"✅ Auto-indexed new file: {title}")
            else:
                LOGGER.error(f"❌ Failed to auto-index: {title}")

        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
        except Exception as e:
            LOGGER.error(f"Auto-index error: {e}")

@StreamBot.on_message(filters.command('update') & filters.private)
async def update_index(bot: Client, message: Message):
    """Incremental update - only index new files since last index"""
    channel_id = message.chat.id
    AUTH_CHANNEL = await db.get_variable('auth_channel')
    if AUTH_CHANNEL is None or AUTH_CHANNEL.strip() == '':
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL
    else:
        AUTH_CHANNEL = [channel.strip() for channel in AUTH_CHANNEL.split(",")]

    if str(channel_id) in AUTH_CHANNEL:
        try:
            # Get last indexed message ID
            last_indexed_id = await db.get_last_indexed_id(str(channel_id))
            current_last_id = message.id

            if last_indexed_id >= current_last_id:
                await message.reply("✅ Database is already up to date! No new files to index.")
                return

            update_message = (
                f"🔄 Incremental update starting...\n\n"
                f"📊 Indexing messages from {last_indexed_id} to {current_last_id}\n"
                f"📈 Approximately {current_last_id - last_indexed_id} new messages\n\n"
                f"⏳ Please wait..."
            )

            wait_msg = await message.reply(text=update_message)

            # Only index new messages
            new_files = await get_messages(channel_id, last_indexed_id + 1, current_last_id)

            if new_files:
                await db.add_btgfiles(new_files)
                await wait_msg.delete()

                done_message = (
                    f"✅ Incremental update completed!\n\n"
                    f"📁 Added {len(new_files)} new files to database.\n"
                    f"🗃️ Database now contains all files up to message #{current_last_id}"
                )
            else:
                await wait_msg.delete()
                done_message = "✅ No new files found to index!"

            await bot.send_message(chat_id=channel_id, text=done_message)

        except Exception as e:
            LOGGER.error(f"Incremental update error: {e}")
            await message.reply(f"❌ Update failed: {str(e)}")
    else:
        await message.reply("Channel is not in AUTH_CHANNEL")
