import os

class Config(object):
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8564398983:AAGxMpPkmLcgZsPnVzIQzCUIro5KNk76QBw")
    DB_NAME = os.environ.get("DB_NAME", "@nxtgenx_bot")
    API_ID = os.environ.get("API_ID", "20807000")
    API_HASH = os.environ.get("API_HASH", "cde2366a7c61e23f4cb44618cbe6cf70")
    DB_URL = os.environ.get("DB_URL", "mongodb+srv://princepia161_db_user:KZWhQUyEe59dF1jh@cluster0.uhoxe0h.mongodb.net/?appName=Cluster0")
    LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "-1003646612944")
    USERLINK = os.environ.get("USERLINK", "https://t.me/princepia")
    TUTORIAL_VIDEO = os.environ.get("TUTORIAL_VIDEO", "https://t.me/princepia")

    # ─── Owner & Admin ──────────────────────────────────────────────────────
    # Owner — hardcoded, always has full access
    OWNER_ID = 890749443

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
