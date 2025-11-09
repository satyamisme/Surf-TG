import re
from bot.config import Telegram
from bot.helper.database import Database
from bot.telegram import UserBot
from os.path import splitext
from bot.helper.file_size import get_readable_file_size

db = Database()
async def search(chat_id, query, page):
    if Telegram.SESSION_STRING == '':
        return await db.search_tgfiles(id=chat_id, query=query, page=page)

    all_posts = []
    async for post in UserBot.search_messages(chat_id=int(chat_id), query=str(query)):
        file = post.video or post.document
        if not file:
            continue
        title = file.file_name or post.caption or file.file_id
        title, _ = splitext(title)
        title = re.sub(r'[.,|_\',]', ' ', title)
        all_posts.append({"msg_id": post.id, "title": title,
                        "hash": file.file_unique_id[:6], "size": get_readable_file_size(file.file_size), "type": file.mime_type})

    # Fuzzy search
    matching_posts = [
        post for post in all_posts
        if re.search(query, post['title'], re.IGNORECASE)
    ]

    # Pagination
    page = int(page)
    page_size = 50
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_posts = matching_posts[start_index:end_index]

    return paginated_posts
