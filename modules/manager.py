"""
modules/manager.py — Telegram group and forum topic management
"""
import re
import unicodedata
from pyrogram.enums import ChatType
from pyrogram.errors import ChatAdminRequired, ChatWriteForbidden
from master.database import db_instance
from logger import LOGGER


def _safe_topic_name(name: str) -> str:
    """Sanitize topic name: NFC normalize, collapse spaces, truncate to 128 chars."""
    if not name:
        return "General"
    name = unicodedata.normalize("NFC", name.strip())
    name = re.sub(r'\s+', ' ', name)
    name = name[:128]
    return name if name else "General"


async def create_topic(bot, group_id, subjectname):
    """Create a forum topic in a supergroup and save it to DB."""
    safe_name = _safe_topic_name(subjectname)
    try:
        # FIX: Some Pyrogram builds expose create_forum_topic differently
        # Try multiple approaches
        if hasattr(bot, 'create_forum_topic'):
            result = await bot.create_forum_topic(int(group_id), safe_name)
            forum_id = result.id
        else:
            # Pyrogram 2.0.x raw API fallback
            from pyrogram.raw import functions, types as raw_types
            result = await bot.invoke(
                functions.channels.CreateForumTopic(
                    channel=await bot.resolve_peer(int(group_id)),
                    title=safe_name,
                    random_id=__import__('random').randint(1, 2**31),
                )
            )
            # result.updates contains the new topic info
            forum_id = None
            for upd in result.updates:
                if hasattr(upd, 'id'):
                    forum_id = upd.id
                    break
            if not forum_id:
                raise Exception("Could not get forum_id from raw API response")

        await db_instance.save_topic(group_id, forum_id, subjectname)
        LOGGER.info(f"Created forum topic: {safe_name} (id={forum_id})")
        return forum_id

    except Exception as e:
        LOGGER.warning(f"Could not create forum topic '{safe_name}': {e}")
        # Return None so upload continues to main chat without crashing batch
        return None


async def get_or_create_topic(bot, group_id, subjectname):
    """Get existing topic or create a new one."""
    forum_id = await db_instance.get_topic(group_id, subjectname)
    if forum_id:
        return forum_id
    return await create_topic(bot, group_id, subjectname)


async def set_chat(bot, group_id, editable):
    """Verify bot has permissions in a group chat."""
    try:
        chat = await bot.get_chat(int(group_id))
        bot_member = await bot.get_chat_member(int(group_id), (await bot.get_me()).id)

        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            if bot_member.privileges:
                return True
            else:
                await editable.edit_text("❌ Bot needs admin permissions in the group!")
                return False
        else:
            await editable.edit_text("❌ Invalid group. Please use a Group or Supergroup ID.")
            return False

    except ChatAdminRequired:
        await editable.edit_text("❌ Bot needs admin permissions in the group!")
        return False
    except ChatWriteForbidden:
        await editable.edit_text("❌ Bot cannot write messages in this group!")
        return False
    except Exception as e:
        await editable.edit_text(f"❌ Error: {e}")
        return False
