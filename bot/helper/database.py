from pymongo import DESCENDING, MongoClient
from bson import ObjectId
from bot.config import Telegram
import re


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
        self.collection.insert_one(folder)

    def delete(self, document_id):
        try:
            has_child_documents = self.collection.count_documents(
                {'parent_folder': document_id}) > 0
            if has_child_documents:
                result = self.collection.delete_many(
                    {'parent_folder': document_id})
            result = self.collection.delete_one({'_id': ObjectId(document_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f'An error occurred: {e}')
            return False

    async def edit(self, id, name, thumbnail):
        result = self.collection.update_one({"_id": ObjectId(id)}, {
            "$set": {"name": name, "thumbnail": thumbnail}})
        return result.modified_count > 0

    async def search_DbFolder(self, query):
        """Enhanced folder search with partial matching"""
        if not query or query.strip() == '':
            return await self.get_Dbfolder()

        # Create case-insensitive regex for partial matching
        regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
        myquery = {'type': 'folder', 'name': regex_query}
        mydoc = self.collection.find(myquery).sort('_id', DESCENDING)
        return [{'_id': str(x['_id']), 'name': x['name']} for x in mydoc]

    async def add_json(self, data):
        result = self.collection.insert_many(data)

    async def get_Dbfolder(self, parent_id="root", page=1, per_page=50):
        query = {"parent_folder": parent_id, "type": "folder"} if parent_id != 'root' else {
            "parent_folder": 'root', "type": "folder"}
        if parent_id != 'root':
            offset = (int(page) - 1) * per_page
            return list(self.collection.find(query).skip(offset).limit(per_page))
        else:
            return list(self.collection.find(query))

    async def get_dbFiles(self, parent_id=None, page=1, per_page=50):
        query = {"parent_folder": parent_id, "type": "file"}
        offset = (int(page) - 1) * per_page
        return list(self.collection.find(query).sort(
            'file_id', DESCENDING).skip(offset).limit(per_page))

    async def get_info(self, id):
        query = {'_id': ObjectId(id)}
        if document := self.collection.find_one(query):
            return document.get('name', None)
        else:
            return None

    async def search_dbfiles(self, id, query, page=1, per_page=1000):
        """Enhanced file search with global results"""
        if not query or query.strip() == '':
            return await self.get_dbFiles(parent_id=id, page=page, per_page=per_page)

        # Case-insensitive partial matching
        regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
        query_filter = {'type': 'file', 'parent_folder': id, 'name': regex_query}
        offset = (int(page) - 1) * per_page
        mydoc = self.files.find(query_filter).sort('file_id', DESCENDING).skip(offset).limit(per_page)
        return list(mydoc)

    async def update_config(self, theme, auth_channel):
        bot_id = Telegram.BOT_TOKEN.split(":", 1)[0]
        config = self.config.find_one({"_id": bot_id})
        if config is None:
            result = self.config.insert_one(
                {"_id": bot_id, "theme": theme, "auth_channel": auth_channel})
            return result.inserted_id is not None
        else:
            result = self.config.update_one({"_id": bot_id}, {
                "$set": {"theme": theme, "auth_channel": auth_channel}})
            return result.modified_count > 0

    async def get_variable(self, key):
        bot_id = Telegram.BOT_TOKEN.split(":", 1)[0]
        config = self.config.find_one({"_id": bot_id})
        return config.get(key) if config is not None else None

    async def list_tgfiles(self, id, page=1, per_page=50):
        query = {'chat_id': id}
        offset = (int(page) - 1) * per_page
        mydoc = self.files.find(query).sort(
            'msg_id', DESCENDING).skip(offset).limit(per_page)
        return list(mydoc)

    async def add_tgfiles(self, chat_id, file_id, hash, name, size, file_type):
        if fetch_old := self.files.find_one({"chat_id": chat_id, "hash": hash}):
            return
        file = {"chat_id": chat_id, "msg_id": file_id,
                "hash": hash, "title": name, "size": size, "type": file_type}
        self.files.insert_one(file)


    async def search_tgfiles(self, id, query, page=1, per_page=1000):
        """Enhanced Telegram files search with global results"""
        if not query or query.strip() == '':
            return await self.list_tgfiles(id=id, page=page, per_page=per_page)

        # Multiple search strategies
        search_conditions = []

        # 1. Direct partial match (case-insensitive)
        regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
        search_conditions.append({'chat_id': id, 'title': regex_query})

        # 2. Word-by-word matching for better results
        words = query.lower().split()
        if len(words) > 1:
            for word in words:
                if len(word) > 2:  # Only search for words longer than 2 characters
                    word_regex = {'$regex': f'.*{re.escape(word)}.*', '$options': 'i'}
                    search_conditions.append({'chat_id': id, 'title': word_regex})

        # Combine all conditions with OR
        final_query = {'$or': search_conditions} if len(search_conditions) > 1 else search_conditions[0]

        offset = (int(page) - 1) * per_page
        mydoc = self.files.find(final_query).sort('msg_id', DESCENDING).skip(offset).limit(per_page)
        return list(mydoc)

    async def global_search_files(self, query, page=1, per_page=1000):
        """Search across all files in database"""
        if not query or query.strip() == '':
            return []

        regex_query = {'$regex': f'.*{re.escape(query)}.*', '$options': 'i'}
        search_query = {'title': regex_query}

        offset = (int(page) - 1) * per_page
        mydoc = self.files.find(search_query).sort('msg_id', DESCENDING).skip(offset).limit(per_page)
        return list(mydoc)
    
    async def add_btgfiles(self, data):
        result = self.files.insert_many(data)
