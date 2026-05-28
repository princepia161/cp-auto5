from pyrogram.types import InlineKeyboardButton as KB, InlineKeyboardMarkup as KM
from config import Config


def home():
    keyboard = KM([
        [KB("➕ Add Batch", callback_data="cp_add_batch")],
        [KB("📊 My Batches", callback_data="show_batch"), KB("⚙️ Manage", callback_data="manage_batch")],
        [KB("🗑️ Delete Batch", callback_data="delete_batch")],
        [KB("📚 Help", callback_data="help"), KB("⚖️ Legal", callback_data="legal")],
        [KB("❌ Close ❌", callback_data="close")]
    ])
    return keyboard


def help_keyboard():
    keyboard = KM([
        [KB("➕ Add Batch", callback_data="cp_add_batch")],
        [KB("📊 My Batches", callback_data="show_batch")],
        [KB("⚙️ Manage Batch", callback_data="manage_batch")],
        [KB("🗑️ Delete Batch", callback_data="delete_batch")],
        [KB("📞 Contact", url=Config.USERLINK)],
        [KB("🏠 Home", callback_data="home"), KB("❌ Close", callback_data="close")]
    ])
    return keyboard


def login_keyboard():
    keyboard = KM([
        [KB("🔑 Token Login", callback_data="cp_token_login")],
        [KB("📱 OTP Login", callback_data="cp_otp_login")],
        [KB("🏠 Home", callback_data="home"), KB("❌ Cancel", callback_data="close")]
    ])
    return keyboard


def confirm_keyboard():
    keyboard = KM([
        [KB("✅ Confirm & Start", callback_data="cp_confirm_yes")],
        [KB("❌ Cancel", callback_data="close")]
    ])
    return keyboard


def contact():
    keyboard = KM([
        [KB("📞 Contact Admin", url=Config.USERLINK)],
        [KB("📺 Tutorial", url=Config.TUTORIAL_VIDEO)],
        [KB("🏠 Home", callback_data="home"), KB("❌ Close", callback_data="close")]
    ])
    return keyboard


def yt_keyboard(watchurl, downloadurl):
    keyboard = KM([
        [KB("▶️ Watch on YouTube", url=watchurl)],
        [KB("❌ Close", callback_data="close")]
    ])
    return keyboard


def back_home():
    keyboard = KM([
        [KB("🏠 Home", callback_data="home"), KB("❌ Close", callback_data="close")]
    ])
    return keyboard
