import os

class Config(object):
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    DB_NAME = os.environ.get("DB_NAME", "classplus_bot")
    API_ID = os.environ.get("API_ID", "YOUR_API_ID")
    API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
    DB_URL = os.environ.get("DB_URL", "mongodb+srv://amanraj8241245_db_user:l5ZdFFk0yuQckD5M@cluster0.4uxpbyq.mongodb.net/?appName=Cluster0")
    LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-100XXXXXXXXXX")
    USERLINK = os.environ.get("USERLINK", "https://t.me/YourChannel")
    TUTORIAL_VIDEO = os.environ.get("TUTORIAL_VIDEO", "https://t.me/YourChannel")

    # ─── Owner & Admin ──────────────────────────────────────────────────────
    # Owner — hardcoded, always has full access
    OWNER_ID = 8532700793

    # Extra admins from env (comma-separated IDs), e.g. "123456,789012"
    _extra_admins_env = os.environ.get("ADMIN_IDS", "")
    _extra = [int(x.strip()) for x in _extra_admins_env.split(",") if x.strip().isdigit()]

    # Full admin list = owner + env admins
    ADMIN_IDS: list = [OWNER_ID] + _extra

    # Legacy single ADMIN_ID kept for backward compat (points to owner)
    ADMIN_ID = OWNER_ID

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Return True if user_id is owner or any admin."""
        return user_id in cls.ADMIN_IDS

    @classmethod
    def is_owner(cls, user_id: int) -> bool:
        """Return True only for the owner."""
        return user_id == cls.OWNER_ID
