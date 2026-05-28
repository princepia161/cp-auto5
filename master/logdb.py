import asyncio
from logger import LOGGER
from config import Config
from master.database import db_instance
from pyrogram.errors import FloodWait


async def check_and_send_from_db(bot, url, group_id, video_caption, pdf_caption, pdf_counter, video_counter, forum_id=None):
    """Check if file already uploaded in LOG_CHANNEL and forward from there."""
    try:
        msg_id = await db_instance.get_msg_id(url)
        if not msg_id:
            return False

        kwargs = {
            "chat_id": int(group_id),
            "from_chat_id": int(Config.LOG_CHANNEL),
            "message_id": msg_id,
        }
        if forum_id:
            kwargs["message_thread_id"] = forum_id

        try:
            await bot.copy_message(**kwargs)
            return True
        except FloodWait as e:
            LOGGER.warning(f"FloodWait: Sleeping {e.value}s")
            await asyncio.sleep(e.value)
            return await check_and_send_from_db(bot, url, group_id, video_caption, pdf_caption, pdf_counter, video_counter, forum_id)
        except Exception as e:
            LOGGER.error(f"Error copying message from log: {e}")
            return False

    except Exception as e:
        LOGGER.error(f"check_and_send_from_db error: {e}")
        return False
