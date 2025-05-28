import re
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


@StreamBot.on_message(filters.command('start') & filters.private)
async def start(bot: Client, message: Message):
    if "file_" in message.text:
        try:
            usr_cmd = message.text.split("_")[-1]
            data = usr_cmd.split("-")
            message_id, chat_id = data[0], f"-{data[1]}"
            file = await bot.get_messages(int(chat_id), int(message_id))
            media = is_media(file)
            await message.reply_cached_media(file_id=media.file_id, caption=f'**{media.file_name}**')
        except Exception as e:
            print(f"An error occurred: {e}")


@StreamBot.on_message(filters.command('index'))
async def start(bot: Client, message: Message):
    channel_id = message.chat.id
    # Fetch AUTH_CHANNEL from the database
    # In database.py, sync_config_from_env stores keys like 'AUTH_CHANNEL'
    auth_channel_val = await db.get_variable('AUTH_CHANNEL') 

    if isinstance(auth_channel_val, list):
        # If it's a list from DB (expected), ensure all elements are stripped strings
        AUTH_CHANNEL = [str(c).strip() for c in auth_channel_val if str(c).strip()]
    elif isinstance(auth_channel_val, str) and auth_channel_val.strip():
        # This case should ideally not be hit if sync_config_from_env works as expected
        # and AUTH_CHANNEL in config.env is a list/comma-separated string that Telegram.AUTH_CHANNEL parses to a list.
        # However, adding for robustness if old string format data exists in DB.
        LOGGER.warning("AUTH_CHANNEL from DB was a string; parsing. Should be a list.")
        AUTH_CHANNEL = [c.strip() for c in auth_channel_val.split(',') if c.strip()]
    else:
        # Fallback to Telegram.AUTH_CHANNEL if DB value is missing, not a list, 
        # an empty list (after stripping), or an unsuitable type.
        # Telegram.AUTH_CHANNEL is already a list of stripped strings.
        if not auth_channel_val: # Handles None, empty list from DB after processing
            LOGGER.info("AUTH_CHANNEL not found or empty in DB, falling back to config.env.")
        else: # Handles other unexpected types
            LOGGER.warning(f"AUTH_CHANNEL from DB was of unexpected type: {type(auth_channel_val)}. Falling back to config.env.")
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL

    # Ensure AUTH_CHANNEL is always a list, even if Telegram.AUTH_CHANNEL was somehow empty.
    if AUTH_CHANNEL is None: # Should not happen with current Telegram.AUTH_CHANNEL parsing
        AUTH_CHANNEL = []
    
    if str(channel_id) in AUTH_CHANNEL:
        try:
            last_id = message.id
            start_message = (
                "🔄 Please perform this action only once at the beginning of Surf-Tg usage.\n\n"
                "📋 File listing is currently in progress.\n\n"
                "🚫 Please refrain from sending any additional files or indexing other channels until this process completes.\n\n"
                "⏳ Please be patient and wait a few moments."
            )

            wait_msg = await message.reply(text=start_message)
            files = await get_messages(message.chat.id, 1, last_id)
            await db.add_btgfiles(files)
            await wait_msg.delete()
            done_message = (
                "✅ All your files have been successfully stored in the database. You're all set!\n\n"
                "📁 You don't need to index again unless you make changes to the database."
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
    )
)
async def file_receive_handler(bot: Client, message: Message):
    channel_id = message.chat.id
    # Fetch AUTH_CHANNEL from the database
    # In database.py, sync_config_from_env stores keys like 'AUTH_CHANNEL'
    auth_channel_val = await db.get_variable('AUTH_CHANNEL') 

    if isinstance(auth_channel_val, list):
        # If it's a list from DB (expected), ensure all elements are stripped strings
        AUTH_CHANNEL = [str(c).strip() for c in auth_channel_val if str(c).strip()]
    elif isinstance(auth_channel_val, str) and auth_channel_val.strip():
        # This case should ideally not be hit if sync_config_from_env works as expected
        # and AUTH_CHANNEL in config.env is a list/comma-separated string that Telegram.AUTH_CHANNEL parses to a list.
        # However, adding for robustness if old string format data exists in DB.
        LOGGER.warning("AUTH_CHANNEL from DB was a string; parsing. Should be a list.")
        AUTH_CHANNEL = [c.strip() for c in auth_channel_val.split(',') if c.strip()]
    else:
        # Fallback to Telegram.AUTH_CHANNEL if DB value is missing, not a list, 
        # an empty list (after stripping), or an unsuitable type.
        # Telegram.AUTH_CHANNEL is already a list of stripped strings.
        if not auth_channel_val: # Handles None, empty list from DB after processing
            LOGGER.info("AUTH_CHANNEL not found or empty in DB, falling back to config.env.")
        else: # Handles other unexpected types
            LOGGER.warning(f"AUTH_CHANNEL from DB was of unexpected type: {type(auth_channel_val)}. Falling back to config.env.")
        AUTH_CHANNEL = Telegram.AUTH_CHANNEL

    # Ensure AUTH_CHANNEL is always a list, even if Telegram.AUTH_CHANNEL was somehow empty.
    if AUTH_CHANNEL is None: # Should not happen with current Telegram.AUTH_CHANNEL parsing
        AUTH_CHANNEL = []
    
    if str(channel_id) in AUTH_CHANNEL:
        try:
            file = message.video or message.document
            title = file.file_name or message.caption or file.file_id
            title, _ = splitext(title)
            title = re.sub(r'[.,|_\',]', ' ', title)
            msg_id = message.id
            hash = file.file_unique_id[:6]
            size = get_readable_file_size(file.file_size)
            type = file.mime_type
            await db.add_tgfiles(str(channel_id), str(msg_id), str(hash), str(title), str(size), str(type))
        except FloodWait as e:
            LOGGER.info(f"Sleeping for {str(e.value)}s")
            await sleep(e.value)
            await message.reply(text=f"Got Floodwait of {str(e.value)}s",
                                disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply(text="Channel is not in AUTH_CHANNEL")
