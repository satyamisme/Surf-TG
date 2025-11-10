from os.path import splitext
import re
import datetime
from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.telegram import StreamBot, UserBot
from bot.helper.file_size import get_readable_file_size
from bot.helper.cache import get_cache, save_cache
from asyncio import gather

db = Database()

async def fetch_message(chat_id, message_id):
    try:
        message = await StreamBot.get_messages(chat_id, message_id)
        return message
    except Exception as e:
        LOGGER.error(f"Error fetching message {message_id} from {chat_id}: {e}")
        return None

async def get_messages(chat_id, first_message_id, last_message_id, batch_size=50):
    """Get all messages with better error handling"""
    messages = []
    current_message_id = first_message_id
    processed_count = 0

    LOGGER.info(f"Starting to fetch messages from {chat_id}, range: {first_message_id} to {last_message_id}")

    while current_message_id <= last_message_id:
        batch_message_ids = list(range(current_message_id, min(current_message_id + batch_size, last_message_id + 1)))
        tasks = [fetch_message(chat_id, message_id) for message_id in batch_message_ids]
        batch_messages = await gather(*tasks, return_exceptions=True)

        for message in batch_messages:
            if isinstance(message, Exception):
                LOGGER.error(f"Error in batch processing: {message}")
                continue

            if message and not message.empty:
                if file := message.video or message.document:
                    title = file.file_name or message.caption or file.file_id
                    title, _ = splitext(title)
                    title = re.sub(r'[.,|_\',]', ' ', title).strip()

                    messages.append({
                        "msg_id": message.id,
                        "title": title,
                        "hash": file.file_unique_id[:6],
                        "size": get_readable_file_size(file.file_size),
                        "type": file.mime_type,
                        "chat_id": str(chat_id),
                        "timestamp": datetime.datetime.now()
                    })
                    processed_count += 1

        current_message_id += batch_size

        # Progress logging
        if processed_count % 100 == 0:
            LOGGER.info(f"Processed {processed_count} messages from {chat_id}")

    LOGGER.info(f"Completed fetching {len(messages)} files from {chat_id}")
    return messages

async def get_files(chat_id, page=1):
    if Telegram.SESSION_STRING == '':
        return await db.list_tgfiles(id=chat_id, page=page)

    if cache := get_cache(chat_id, int(page)):
        return cache

    posts = []
    try:
        async for post in UserBot.get_chat_history(chat_id=int(chat_id), limit=50, offset=(int(page) - 1) * 50):
            file = post.video or post.document
            if not file:
                continue

            title = file.file_name or post.caption or file.file_id
            title, _ = splitext(title)
            title = re.sub(r'[.,|_\',]', ' ', title).strip()

            posts.append({
                "msg_id": post.id,
                "title": title,
                "hash": file.file_unique_id[:6],
                "size": get_readable_file_size(file.file_size),
                "type": file.mime_type
            })

        save_cache(chat_id, {"posts": posts}, page)

    except Exception as e:
        LOGGER.error(f"Error getting files from {chat_id}: {e}")

    return posts

async def index_channel_files(chat_id):
    """Index all files from a channel into the database"""
    all_files = []
    async for message in UserBot.get_chat_history(int(chat_id)):
        if file := message.video or message.document:
            title = file.file_name or message.caption or file.file_id
            title, _ = splitext(title)
            title = re.sub(r'[.,|_\',]', ' ', title)
            all_files.append({
                "chat_id": str(chat_id),
                "msg_id": message.id,
                "hash": file.file_unique_id[:6],
                "title": title,
                "size": get_readable_file_size(file.file_size),
                "type": file.mime_type
            })

    await db.add_btgfiles(all_files)

async def posts_file(posts, chat_id):
    phtml = """
            <div class="col">
                <div class="card text-white bg-primary mb-3">
                    <input type="checkbox" class="admin-only form-check-input position-absolute top-0 end-0 m-2"
                        onchange="checkSendButton()" id="selectCheckbox"
                        data-id="{id}|{hash}|{title}|{size}|{type}|{img}">
                    <img src="https://cdn.jsdelivr.net/gh/weebzone/weebzone/data/Surf-TG/src/loading.gif" class="lzy_img card-img-top rounded-top"
                        data-src="{img}" alt="{title}">
                    <a href="/watch/{chat_id}?id={id}&hash={hash}">
                    <div class="card-body p-1">
                        <h6 class="card-title" style="user-select: text; -webkit-user-select: text;">{title}</h6>
                        <span class="badge bg-warning">{type}</span>
                        <span class="badge bg-info">{size}</span>
                    </div>
                    </a>
                </div>
            </div>
"""

    formatted_posts = []
    for post in posts:
        # Handle global search results
        if chat_id == 'global':
            actual_chat_id = post.get('chat_id', 'global')
            display_chat_id = str(actual_chat_id).replace("-100", "")
            img_url = f"/api/thumb/{actual_chat_id}?id={post['msg_id']}"
        else:
            display_chat_id = str(chat_id).replace("-100", "")
            img_url = f"/api/thumb/{chat_id}?id={post['msg_id']}"

        formatted_posts.append(phtml.format(
            chat_id=display_chat_id,
            id=post["msg_id"],
            img=img_url,
            title=post["title"],
            hash=post["hash"],
            size=post['size'],
            type=post['type']
        ))

    return ''.join(formatted_posts)
