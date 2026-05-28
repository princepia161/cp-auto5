"""
plugins/command.py — Bot slash commands
"""
import os
import sys
from pyrogram import Client as bot, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from constant import buttom, msg
from config import Config
from master.utils import send_random_photo


def fix_keyboard(markup):
    """Remove buttons with empty/invalid URLs."""
    if not markup or not hasattr(markup, 'inline_keyboard'):
        return markup
    fixed_rows = []
    for row in markup.inline_keyboard:
        fixed_row = []
        for btn in row:
            if btn.url is not None and btn.url.strip() == '':
                continue
            fixed_row.append(btn)
        if fixed_row:
            fixed_rows.append(fixed_row)
    if not fixed_rows:
        return None
    return InlineKeyboardMarkup(fixed_rows)


@bot.on_message(filters.command("start") & filters.private)
async def start_msg(client, m):
    try:
        user_mention = m.from_user.mention
        caption = msg.START.format(user_mention, Config.USERLINK)
        kb = fix_keyboard(buttom.home())
        photo = await send_random_photo()
        if photo:
            await client.send_photo(m.chat.id, photo=photo, caption=caption, reply_markup=kb)
        else:
            await m.reply_text(caption, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")


@bot.on_message(filters.command("help") & filters.private)
async def help_msg(client, m):
    try:
        caption = msg.HELP.format(Config.USERLINK)
        kb = fix_keyboard(buttom.help_keyboard())
        photo = await send_random_photo()
        if photo:
            await client.send_photo(m.chat.id, photo=photo, caption=caption, reply_markup=kb)
        else:
            await m.reply_text(caption, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")


@bot.on_message(filters.command("restart") & filters.private)
async def restart_handler(_, m):
    if not Config.is_admin(m.from_user.id):
        return await m.reply_text(
            "╭━━━━━━ ERROR ━━━━━━➣\n"
            "┣⪼ ⚠️ **Access Denied**\n"
            "┣⪼ 🔒 Admin only command\n"
            "╰━━━━━━━━━━━━━━━━━━━━━➣"
        )
    await m.reply_text("🚦 **Restarting...**", True)
    os.execl(sys.executable, sys.executable, *sys.argv)


@bot.on_message(filters.command("legal") & filters.private)
async def legal_disclaimer(_, m):
    try:
        await m.reply_text(
            msg.DISCLAIMER,
            disable_web_page_preview=True,
            reply_markup=fix_keyboard(buttom.contact())
        )
    except Exception as e:
        await m.reply_text(f"⚠️ Error: {e}")


@bot.on_message(filters.command("id"))
async def get_chat_id(_, m):
    await m.reply_text(f"<blockquote><b>Chat ID:</b></blockquote> `{m.chat.id}`")


@bot.on_message(filters.command("addbatch") & filters.private)
async def addbatch_cmd(client, m):
    """Shortcut command to start batch add flow."""
    if not Config.is_admin(m.from_user.id):
        return await m.reply_text("🔒 Admin only command.")
    await m.reply_text(msg.APP, reply_markup=buttom.login_keyboard())
