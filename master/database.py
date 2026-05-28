import motor.motor_asyncio
import pytz
from datetime import datetime
from config import Config

IST = pytz.timezone('Asia/Kolkata')


class Database:
    def __init__(self, uri, database_name):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[database_name]
        self.batches = self.db["batches"]
        self.batch_status = self.db["batch_status"]
        self.uploaded_files = self.db["uploaded_files"]
        self.topics = self.db["topics"]
        self.messages = self.db["messages"]

    async def add_batch(self, user_id, course_id, token, select, time, group_id, length, credit, filename, thumb):
        batch_data = {
            "user_id": user_id,
            "course_id": str(course_id),
            "token": token,
            "select": select,
            "time": time,
            "group_id": str(group_id),
            "length": length,
            "credit": credit,
            "filename": filename,
            "thumb": thumb,
            "created_at": datetime.now(IST).isoformat()
        }
        await self.batches.update_one(
            {"user_id": user_id, "course_id": str(course_id)},
            {"$set": batch_data},
            upsert=True
        )

    async def delete_batch(self, user_id, course_id):
        await self.batches.delete_one({"user_id": user_id, "course_id": str(course_id)})
        await self.batch_status.delete_one({"user_id": user_id, "course_id": str(course_id)})

    async def get_all_batches(self, user_id):
        cursor = self.batches.find({"user_id": user_id})
        return await cursor.to_list(length=None)

    async def get_all_batches_with_schedule(self):
        cursor = self.batches.find({"time": {"$nin": [None, "no", ""]}})
        return await cursor.to_list(length=None)

    async def get_batch(self, user_id, course_id):
        return await self.batches.find_one({"user_id": user_id, "course_id": str(course_id)})

    async def get_batch_by_course_id(self, course_id):
        return await self.batches.find_one({"course_id": str(course_id)})

    async def get_batch_status(self, user_id, course_id):
        return await self.batch_status.find_one({"user_id": user_id, "course_id": str(course_id)})

    async def get_incomplete_batches(self):
        cursor = self.batch_status.find({"status": {"$nin": ["completed", None]}})
        return await cursor.to_list(length=None)

    async def get_msg_id(self, url):
        doc = await self.messages.find_one({"url": url})
        return doc.get("msg_id") if doc else None

    async def get_topic(self, group_id, subjectname):
        doc = await self.topics.find_one({"group_id": str(group_id), "subjectname": subjectname})
        return doc.get("forum_id") if doc else None

    async def is_batch_exists(self, user_id, course_id):
        doc = await self.batches.find_one({"user_id": user_id, "course_id": str(course_id)})
        return doc is not None

    async def is_file_uploaded(self, course_id, url):
        doc = await self.uploaded_files.find_one({"course_id": str(course_id), "url": url})
        return doc is not None

    async def mark_file_uploaded(self, course_id, url, chat_id):
        await self.uploaded_files.update_one(
            {"course_id": str(course_id), "url": url},
            {"$set": {
                "course_id": str(course_id),
                "url": url,
                "chat_id": str(chat_id),
                "uploaded_at": datetime.now(IST).isoformat()
            }},
            upsert=True
        )

    async def save_batch_status(self, user_id, course_id, status):
        await self.batch_status.update_one(
            {"user_id": user_id, "course_id": str(course_id)},
            {"$set": {
                "user_id": user_id,
                "course_id": str(course_id),
                "status": status,
                "updated_at": datetime.now(IST).isoformat()
            }},
            upsert=True
        )

    async def save_msg_id(self, url, msg_id):
        await self.messages.update_one(
            {"url": url},
            {"$set": {"url": url, "msg_id": msg_id}},
            upsert=True
        )

    async def save_topic(self, group_id, forum_id, subjectname):
        await self.topics.update_one(
            {"group_id": str(group_id), "subjectname": subjectname},
            {"$set": {"group_id": str(group_id), "forum_id": forum_id, "subjectname": subjectname}},
            upsert=True
        )


db_instance = Database(Config.DB_URL, Config.DB_NAME)
