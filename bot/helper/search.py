import re
from bot.config import Telegram
from bot.helper.database import Database
from bot.telegram import UserBot
from os.path import splitext
from bot.helper.file_size import get_readable_file_size

db = Database()

async def search(chat_id, query, page=1, global_search=False):
    if global_search:
        # Global search across all channels
        return await db.global_search_files(query=query, page=page)

    if Telegram.SESSION_STRING == '':
        # Enhanced database search
        return await db.search_tgfiles(id=chat_id, query=query, page=page)

    # Enhanced UserBot search
    posts = []
    search_limit = 1000  # Increased limit for better results

    async for post in UserBot.search_messages(
        chat_id=int(chat_id),
        limit=search_limit,
        query=str(query),
        offset=(int(page) - 1) * search_limit
    ):
        file = post.video or post.document
        if not file:
            continue

        # Enhanced filename processing
        title = file.file_name or post.caption or file.file_id
        title, _ = splitext(title)
        title = re.sub(r'[.,|_\',]', ' ', title)

        posts.append({
            "msg_id": post.id,
            "title": title,
            "hash": file.file_unique_id[:6],
            "size": get_readable_file_size(file.file_size),
            "type": file.mime_type
        })

    return posts

async def global_search(query, page=1):
    """Global search across all authorized channels"""
    return await db.global_search_files(query=query, page=page)
