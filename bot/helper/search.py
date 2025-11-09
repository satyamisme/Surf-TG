from bot.helper.database import Database

db = Database()

async def search(chat_id, query, page=1):
    """Channel-specific search"""
    return await db.search_tgfiles(id=chat_id, query=query, page=page)

async def global_search(query, page=1):
    """Global search across all authorized channels"""
    return await db.global_search_files(query=query, page=page)
