from pymongo import DESCENDING, MongoClient, UpdateOne, TEXT
from bson import ObjectId
from bot.config import Telegram
import re
import datetime
from datetime import timezone
from bot import LOGGER


class Database:
    def __init__(self):
        MONGODB_URI = Telegram.DATABASE_URL
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client["surftg"]
        self.collection = self.db["playlist"]
        self.config = self.db["config"]
        self.files = self.db["files"]
        self.index_status = self.db["index_status"]  # New collection

        self._create_indexes()

    def _create_indexes(self):
        """Create text indexes for fast searching"""
        try:
            self.collection.create_index([("name", TEXT)], default_language="english")
            self.collection.create_index([("parent_folder", 1), ("type", 1)])
            self.collection.create_index([("file_id", DESCENDING)])
            self.files.create_index([("title", TEXT)], default_language="english")
            self.files.create_index([("chat_id", 1), ("msg_id", DESCENDING)])
            self.files.create_index([("chat_id", 1), ("hash", 1)], unique=True)
        except Exception as e:
            print(f"Index creation: {e}")

    # Statistics methods
    async def get_index_stats(self, chat_id):
        """Get indexing statistics for a channel"""
        stats = self.index_status.find_one({"chat_id": str(chat_id)})
        if not stats:
            return {
                "chat_id": str(chat_id),
                "status": "not_started",
                "total_messages": 0,
                "indexed_count": 0,
                "failed_count": 0,
                "start_time": None,
                "last_update": None,
                "estimated_completion": None,
                "last_indexed_id": 0
            }
        return stats

    async def update_index_stats(self, chat_id, total=None, indexed=None,
                                 failed=None, status=None, last_id=None):
        """Update indexing progress"""
        update_data = {"last_update": datetime.now(timezone.utc)}

        if total is not None:
            update_data["total_messages"] = total
        if indexed is not None:
            update_data["indexed_count"] = indexed
        if failed is not None:
            update_data["failed_count"] = failed
        if status is not None:
            update_data["status"] = status
        if last_id is not None:
            update_data["last_indexed_id"] = last_id

        self.index_status.update_one(
            {"chat_id": str(chat_id)},
            {"$set": update_data},
            upsert=True
        )

    async def get_total_indexed_files(self, chat_id=None):
        """Get total indexed files count"""
        query = {"chat_id": str(chat_id)} if chat_id else {}
        return self.files.count_documents(query)

    async def get_channel_stats(self):
        """Get statistics for all indexed channels"""
        pipeline = [
            {
                "$group": {
                    "_id": "$chat_id",
                    "count": {"$sum": 1},
                    "total_size": {"$sum": "$size"}
                }
            }
        ]
        return list(self.files.aggregate(pipeline))

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
        words = re.findall(r'\w+', query.lower())
        regex_pattern = '.*'.join(f'(?=.*{re.escape(word)})' for word in words)
        regex_query = {'$regex': f'.*{regex_pattern}.*', '$options': 'i'}
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

    async def search_dbfiles(self, id, query, page=1, per_page=50):
        words = re.findall(r'\w+', query.lower())
        regex_pattern = '.*'.join(f'(?=.*{re.escape(word)})' for word in words)
        regex_query = {'$regex': f'.*{regex_pattern}.*', '$options': 'i'}
        query = {'type': 'file', 'parent_folder': id, 'name': regex_query}
        offset = (int(page) - 1) * per_page
        mydoc = self.collection.find(query).sort(
            'file_id', DESCENDING).skip(offset).limit(per_page)
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
        """Update or insert file with proper upsert logic"""
        try:
            # Use update_one with upsert to update existing or insert new
            result = self.files.update_one(
                {
                    "chat_id": chat_id,
                    "hash": hash,
                    "msg_id": file_id
                },
                {
                    "$set": {
                        "chat_id": chat_id,
                        "msg_id": file_id,
                        "hash": hash,
                        "title": name,
                        "size": size,
                        "type": file_type,
                        "last_updated": datetime.datetime.now()
                    }
                },
                upsert=True  # This is key - creates if doesn't exist
            )

            if result.upserted_id:
                LOGGER.info(f"Inserted new file: {name}")
            elif result.modified_count > 0:
                LOGGER.info(f"Updated existing file: {name}")
            else:
                LOGGER.info(f"File already up to date: {name}")

            return True
        except Exception as e:
            LOGGER.error(f"Error adding file to database: {e}")
            return False

    async def add_btgfiles(self, data):
        """Bulk update or insert files with proper upsert"""
        try:
            if not data:
                return

            operations = []
            for file_data in data:
                operations.append(
                    UpdateOne(
                        {
                            "chat_id": file_data["chat_id"],
                            "hash": file_data["hash"],
                            "msg_id": file_data["msg_id"]
                        },
                        {
                            "$set": {
                                "chat_id": file_data["chat_id"],
                                "msg_id": file_data["msg_id"],
                                "hash": file_data["hash"],
                                "title": file_data["title"],
                                "size": file_data["size"],
                                "type": file_data["type"],
                                "last_updated": datetime.datetime.now()
                            }
                        },
                        upsert=True
                    )
                )

            if operations:
                result = self.files.bulk_write(operations)
                LOGGER.info(f"Bulk update: {result.upserted_count} inserted, {result.modified_count} updated")

        except Exception as e:
            LOGGER.error(f"Error in bulk file update: {e}")

    async def cleanup_old_files(self, chat_id, current_file_hashes):
        """Remove files that no longer exist in the channel"""
        try:
            # Delete files that are in database but not in current file list
            result = self.files.delete_many({
                "chat_id": chat_id,
                "hash": {"$nin": current_file_hashes}
            })

            if result.deleted_count > 0:
                LOGGER.info(f"Cleaned up {result.deleted_count} old files from {chat_id}")

        except Exception as e:
            LOGGER.error(f"Error cleaning up old files: {e}")

    async def reindex_channel(self, chat_id, new_files_data):
        """Complete reindexing of a channel"""
        try:
            # Get current file hashes for cleanup
            current_hashes = [file["hash"] for file in new_files_data]

            # Update/insert all files
            await self.add_btgfiles(new_files_data)

            # Clean up files that no longer exist
            await self.cleanup_old_files(chat_id, current_hashes)

            LOGGER.info(f"Successfully reindexed channel {chat_id} with {len(new_files_data)} files")

        except Exception as e:
            LOGGER.error(f"Error reindexing channel {chat_id}: {e}")

    async def auto_index_file(self, chat_id, message_id, file_data):
        """Optimized method for automatic file indexing"""
        try:
            result = self.files.update_one(
                {
                    "chat_id": chat_id,
                    "msg_id": message_id,
                    "hash": file_data["hash"]
                },
                {
                    "$set": {
                        "chat_id": chat_id,
                        "msg_id": message_id,
                        "hash": file_data["hash"],
                        "title": file_data["title"],
                        "size": file_data["size"],
                        "type": file_data["type"],
                        "last_updated": datetime.datetime.now(),
                        "auto_indexed": True
                    },
                    "$setOnInsert": {
                        "created_at": datetime.datetime.now()
                    }
                },
                upsert=True
            )

            if result.upserted_id:
                LOGGER.info(f"🆕 New file auto-indexed: {file_data['title']}")
                return "inserted"
            elif result.modified_count > 0:
                LOGGER.info(f"🔄 File updated: {file_data['title']}")
                return "updated"
            else:
                return "exists"

        except Exception as e:
            LOGGER.error(f"Auto-index database error: {e}")
            return "error"

    async def get_last_indexed_id(self, chat_id):
        """Get the last message ID that was indexed for a channel"""
        try:
            last_file = self.files.find_one(
                {"chat_id": chat_id},
                sort=[("msg_id", DESCENDING)]
            )
            return last_file["msg_id"] if last_file else 1
        except Exception as e:
            LOGGER.error(f"Error getting last indexed ID: {e}")
            return 1

    async def search_files(self, query, chat_id=None, page=1, per_page=1000):
        """Optimized search using MongoDB text index, with optional channel filter"""
        if not query or query.strip() == '':
            return []

        # Main query using text search
        search_query = {
            '$text': {'$search': query}
        }

        if chat_id:
            search_query['chat_id'] = str(chat_id)

        # Projection to add a score for relevance
        projection = {'score': {'$meta': 'textScore'}}

        offset = (int(page) - 1) * per_page

        # Execute search and sort by relevance score
        mydoc = self.files.find(search_query, projection).sort(
            [('score', {'$meta': 'textScore'})]
        ).skip(offset).limit(per_page)

        return list(mydoc)
