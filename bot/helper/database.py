import asyncio
from pymongo import DESCENDING, MongoClient
from bson import ObjectId
from bot.config import Telegram
import re
from os.path import splitext
from bot import LOGGER


class Database:
    def __init__(self):
        MONGODB_URI = Telegram.DATABASE_URL
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client["surftg"]
        self.collection = self.db["playlist"]
        self.config = self.db["config"]
        self.files = self.db["files"]

    async def create_folder(self, parent_id, folder_name, thumbnail):
        folder = {"parent_folder": parent_id, "name": folder_name,
                  "thumbnail": thumbnail, "type": "folder"}
        await asyncio.to_thread(self.collection.insert_one, folder)

    async def delete(self, document_id): # Changed to async def
        try:
            has_child_documents = await asyncio.to_thread(
                self.collection.count_documents, {'parent_folder': document_id}
            )
            if has_child_documents > 0: # count_documents returns a number
                await asyncio.to_thread(
                    self.collection.delete_many, {'parent_folder': document_id}
                )
            result = await asyncio.to_thread(
                self.collection.delete_one, {'_id': ObjectId(document_id)}
            )
            return result.deleted_count > 0
        except Exception as e:
            LOGGER.error(f'An error occurred during DB delete operation: {type(e).__name__} - {e}', exc_info=True)
            return False

    async def edit(self, id, name, thumbnail):
        result = await asyncio.to_thread(
            self.collection.update_one,
            {"_id": ObjectId(id)},
            {"$set": {"name": name, "thumbnail": thumbnail}}
        )
        return result.modified_count > 0

    async def search_DbFolder(self, query):
        words = re.findall(r'\w+', query.lower())
        regex_pattern = '.*'.join(f'(?=.*{re.escape(word)})' for word in words)
        regex_query = {'$regex': f'.*{regex_pattern}.*', '$options': 'i'}
        myquery = {'type': 'folder', 'name': regex_query}
        
        mydoc_list = await asyncio.to_thread(
            lambda: list(self.collection.find(myquery).sort('_id', DESCENDING))
        )
        return [{'_id': str(x['_id']), 'name': x['name']} for x in mydoc_list]

    async def add_json(self, data):
        await asyncio.to_thread(self.collection.insert_many, data)

    async def get_Dbfolder(self, parent_id="root", page=1, per_page=50):
        query = {"parent_folder": parent_id, "type": "folder"} if parent_id != 'root' else {
            "parent_folder": 'root', "type": "folder"}
        
        if parent_id != 'root':
            offset = (int(page) - 1) * per_page
            return await asyncio.to_thread(
                lambda: list(self.collection.find(query).skip(offset).limit(per_page))
            )
        else:
            return await asyncio.to_thread(
                lambda: list(self.collection.find(query))
            )

    async def get_dbFiles(self, parent_id=None, page=1, per_page=50):
        query = {"parent_folder": parent_id, "type": "file"}
        offset = (int(page) - 1) * per_page
        return await asyncio.to_thread(
            lambda: list(self.collection.find(query).sort('file_id', DESCENDING).skip(offset).limit(per_page))
        )

    async def get_info(self, id):
        query = {'_id': ObjectId(id)}
        document = await asyncio.to_thread(self.collection.find_one, query)
        if document:
            return document.get('name', None)
        else:
            return None

    async def search_dbfiles(self, id, query, page=1, per_page=50):
        query_text, _ = splitext(query)  # Renamed to avoid conflict with the dict 'query'
        query_text = re.sub(r"[.,|_',]", ' ', query_text)  # Normalize punctuation
        words = re.findall(r'\w+', query_text.lower())
        regex_pattern = '.*'.join(f'(?=.*{re.escape(word)})' for word in words)
        regex_query_val = {'$regex': f'.*{regex_pattern}.*', '$options': 'i'}
        
        mongo_query = {'type': 'file', 'parent_folder': id, 'name': regex_query_val}
        offset = (int(page) - 1) * per_page
        
        mydoc_list = await asyncio.to_thread(
            lambda: list(self.collection.find(mongo_query).sort('file_id', DESCENDING).skip(offset).limit(per_page))
        )
        return mydoc_list

    async def update_config(self, theme, auth_channel):
        bot_id = Telegram.BOT_TOKEN.split(":", 1)[0]
        
        config = await asyncio.to_thread(self.config.find_one, {"_id": bot_id})
        
        if config is None:
            result = await asyncio.to_thread(
                self.config.insert_one,
                {"_id": bot_id, "theme": theme, "auth_channel": auth_channel}
            )
            return result.inserted_id is not None
        else:
            result = await asyncio.to_thread(
                self.config.update_one,
                {"_id": bot_id},
                {"$set": {"theme": theme, "auth_channel": auth_channel}}
            )
            return result.modified_count > 0

    async def get_variable(self, key):
        bot_id = Telegram.BOT_TOKEN.split(":", 1)[0]
        config = await asyncio.to_thread(self.config.find_one, {"_id": bot_id})
        return config.get(key) if config is not None else None

    async def list_tgfiles(self, id, page=1, per_page=50):
        query = {'chat_id': id}
        offset = (int(page) - 1) * per_page
        
        mydoc_list = await asyncio.to_thread(
            lambda: list(self.files.find(query).sort('msg_id', DESCENDING).skip(offset).limit(per_page))
        )
        return mydoc_list

    async def add_tgfiles(self, chat_id, file_id, hash_val, name, size, file_type): # Renamed hash to hash_val
        fetch_old = await asyncio.to_thread(
            self.files.find_one, {"chat_id": chat_id, "hash": hash_val}
        )
        if fetch_old:
            return
            
        file_doc = {"chat_id": chat_id, "msg_id": file_id,
                    "hash": hash_val, "title": name, "size": size, "type": file_type}
        await asyncio.to_thread(self.files.insert_one, file_doc)

    async def search_tgfiles(self, id, query, page=1, per_page=50):
        query_text, _ = splitext(query) # Renamed to avoid conflict
        query_text = re.sub(r"[.,|_',]", ' ', query_text)  # Normalize punctuation
        words = re.findall(r'\w+', query_text.lower())
        regex_pattern = '.*'.join(f'(?=.*{re.escape(word)})' for word in words)
        regex_query_val = {'$regex': f'.*{regex_pattern}.*', '$options': 'i'}
        
        mongo_query = {'chat_id': id, 'title': regex_query_val}
        offset = (int(page) - 1) * per_page
        
        mydoc_list = await asyncio.to_thread(
            lambda: list(self.files.find(mongo_query).sort('msg_id', DESCENDING).skip(offset).limit(per_page))
        )
        return mydoc_list
    
    async def add_btgfiles(self, data):
        await asyncio.to_thread(self.files.insert_many, data)
