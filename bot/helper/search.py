from bot.helper.database import Database

db = Database()

async def search(chat_id, query, page=1):
    """Channel-specific search"""
    return await db.search_files(query=query, chat_id=chat_id, page=page)

async def global_search(query, page=1):
    """Global search across all authorized channels"""
    return await db.search_files(query=query, page=page)
