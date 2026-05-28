"""
plugins/callbacks.py — Inline keyboard callback handlers
"""
import asyncio
import traceback
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from constant import buttom, msg
from modules import cp_master
from modules.cp_master import pending_batches
from master.database import db_instance
from master.utils import send_random_photo
from config import Config
from logger import LOGGER


# ─── HOME ──────────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^home$"))
async def cb_home(bot: Client, query: CallbackQuery):
    try:
        user_mention = query.from_user.mention
        photo = await send_random_photo()
        caption = msg.START.format(user_mention, Config.USERLINK)
        kb = buttom.home()
        await query.message.delete()
        if photo:
            await bot.send_photo(query.message.chat.id, photo=photo, caption=caption, reply_markup=kb)
        else:
            await bot.send_message(query.message.chat.id, text=caption, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(f"cb_home error: {e}")
        try:
            await query.answer(f"⚠️ Error: {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^help$"))
async def cb_help(bot: Client, query: CallbackQuery):
    try:
        await query.message.edit_text(
            msg.HELP.format(Config.USERLINK),
            reply_markup=buttom.help_keyboard()
        )
    except Exception as e:
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^legal$"))
async def cb_legal(bot: Client, query: CallbackQuery):
    try:
        await query.message.edit_text(msg.DISCLAIMER, reply_markup=buttom.contact())
    except Exception as e:
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^close$"))
async def cb_close(bot: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        try:
            await query.answer("⚠️ Could not close.", show_alert=True)
        except Exception:
            pass


# ─── ADD BATCH ─────────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^cp_add_batch$"))
async def cb_add_batch(bot: Client, query: CallbackQuery):
    if not Config.is_admin(query.from_user.id):
        return await query.answer("🔒 Admin only.", show_alert=True)
    try:
        await query.message.edit_text(msg.APP, reply_markup=buttom.login_keyboard())
    except Exception as e:
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^cp_token_login$"))
async def cb_token_login(bot: Client, query: CallbackQuery):
    if not Config.is_admin(query.from_user.id):
        return await query.answer("🔒 Admin only.", show_alert=True)
    try:
        try:
            await query.message.edit_text(msg.LOGIN_PROMPT_TOKEN, reply_markup=buttom.back_home())
        except Exception:
            pass

        token_input = await bot.listen(query.message.chat.id, timeout=180)
        token = token_input.text.strip()
        try:
            await token_input.delete()
        except Exception:
            pass

        editable = await bot.send_message(query.message.chat.id, "🔍 Verifying token...")
        result = await cp_master.token_login(token)

        if result["success"]:
            try:
                await editable.edit_text(msg.LOGIN_SUCCESS)
            except Exception:
                pass
            await cp_master.add_batch(bot, query.message, token, user_id=query.from_user.id)
        else:
            try:
                await editable.edit_text(
                    msg.LOGIN_FAILED.format(result["message"]),
                    reply_markup=buttom.back_home()
                )
            except Exception:
                await bot.send_message(
                    query.message.chat.id,
                    msg.LOGIN_FAILED.format(result["message"]),
                    reply_markup=buttom.back_home()
                )

    except asyncio.TimeoutError:
        await bot.send_message(query.message.chat.id, "⏰ Timeout! Please try again.", reply_markup=buttom.back_home())
    except Exception as e:
        LOGGER.error(f"cb_token_login error: {e}")
        traceback.print_exc()
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^cp_otp_login$"))
async def cb_otp_login(bot: Client, query: CallbackQuery):
    if not Config.is_admin(query.from_user.id):
        return await query.answer("🔒 Admin only.", show_alert=True)
    try:
        try:
            editable = await query.message.edit_text(msg.LOGIN_PROMPT_OTP, reply_markup=buttom.back_home())
        except Exception:
            editable = await bot.send_message(query.message.chat.id, msg.LOGIN_PROMPT_OTP, reply_markup=buttom.back_home())

        input_msg = await bot.listen(query.message.chat.id, timeout=120)
        user_input = input_msg.text.strip()
        try:
            await input_msg.delete()
        except Exception:
            pass

        result = await cp_master.otp_login(user_input, editable, bot, query.message)

        if result["success"]:
            token = result["token"]
            try:
                await editable.edit_text(msg.LOGIN_SUCCESS)
            except Exception:
                pass
            await cp_master.add_batch(bot, query.message, token, user_id=query.from_user.id)
        else:
            try:
                await editable.edit_text(
                    msg.LOGIN_FAILED.format(result["message"]),
                    reply_markup=buttom.back_home()
                )
            except Exception:
                await bot.send_message(
                    query.message.chat.id,
                    msg.LOGIN_FAILED.format(result["message"]),
                    reply_markup=buttom.back_home()
                )

    except asyncio.TimeoutError:
        await bot.send_message(query.message.chat.id, "⏰ Timeout! Please try again.", reply_markup=buttom.back_home())
    except Exception as e:
        LOGGER.error(f"cb_otp_login error: {e}")
        traceback.print_exc()
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


# ─── MODE SELECTION ─────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^cpmode_txt_"))
async def cb_mode_txt(bot: Client, query: CallbackQuery):
    """User chose: Get .txt file of all batch links."""
    if not Config.is_admin(query.from_user.id):
        return await query.answer("🔒 Admin only.", show_alert=True)
    try:
        # Format: cpmode_txt_{user_id}_{batch_id}
        raw = query.data[len("cpmode_txt_"):]
        user_id_str, batch_id = raw.split("_", 1)
        user_id = int(user_id_str)

        try:
            await query.message.delete()
        except Exception:
            pass

        asyncio.create_task(
            cp_master.generate_and_send_txt(bot, query.message.chat.id, user_id, batch_id)
        )
        await query.answer("⏳ Generating .txt file...", show_alert=False)

    except Exception as e:
        LOGGER.error(f"cb_mode_txt error: {e}")
        traceback.print_exc()
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^cpmode_upload_"))
async def cb_mode_upload(bot: Client, query: CallbackQuery):
    """User chose: Upload content to Telegram group."""
    if not Config.is_admin(query.from_user.id):
        return await query.answer("🔒 Admin only.", show_alert=True)
    try:
        # Format: cpmode_upload_{user_id}_{batch_id}
        raw = query.data[len("cpmode_upload_"):]
        user_id_str, batch_id = raw.split("_", 1)
        user_id = int(user_id_str)

        try:
            await query.message.delete()
        except Exception:
            pass

        await cp_master.continue_upload_setup(bot, query.message.chat.id, user_id, batch_id)

    except Exception as e:
        LOGGER.error(f"cb_mode_upload error: {e}")
        traceback.print_exc()
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


# ─── CONFIRM BATCH ─────────────────────────────────────────────────────────

@Client.on_callback_query(filters.regex("^cpconfirm_"))
async def cb_confirm_batch(bot: Client, query: CallbackQuery):
    try:
        parts     = query.data.split("_")
        user_id   = int(parts[1])
        batch_id  = "_".join(parts[2:])

        if not Config.is_admin(query.from_user.id):
            return await query.answer("🔒 Admin only.", show_alert=True)

        try:
            await query.message.edit_text("✅ Batch confirmed! Starting upload process...")
        except Exception:
            pass

        success = await cp_master.confirm_and_process_batch(bot, user_id, batch_id)
        if success:
            try:
                await query.message.edit_text(
                    f"<b>✅ Batch added successfully!</b>\n\n"
                    f"🆔 <b>Batch ID:</b> <code>{batch_id}</code>\n\n"
                    "Content collection & upload started in background.\n"
                    "Check your group for updates!",
                    reply_markup=buttom.back_home()
                )
            except Exception:
                pass
        else:
            try:
                await query.message.edit_text(
                    "❌ Could not confirm batch. Please try adding it again.",
                    reply_markup=buttom.back_home()
                )
            except Exception:
                pass
    except Exception as e:
        LOGGER.error(f"cb_confirm_batch error: {e}")
        traceback.print_exc()
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


# ─── SHOW / MANAGE / DELETE BATCHES ────────────────────────────────────────

@Client.on_callback_query(filters.regex("^show_batch$"))
async def cb_show_batch(bot: Client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        batches = await db_instance.get_all_batches(user_id)
        if not batches:
            return await query.answer("📭 You have no batches yet.", show_alert=True)

        text = "<b>╭━━━━━━━━━━━━━━━━━━╮\n┃  📊 YOUR BATCHES\n╰━━━━━━━━━━━━━━━━━━╯</b>\n\n"
        buttons = []
        for batch in batches:
            cid  = batch.get("course_id", "")
            name = batch.get("select", "Unknown")
            t    = batch.get("time", "Manual")
            text += f"🆔 <code>{cid}</code> — <b>{name}</b>\n⏰ {t or 'Manual'}\n\n"
            buttons.append([InlineKeyboardButton(f"📊 {name[:25]}", callback_data=f"stats_{cid}")])

        buttons.append([
            InlineKeyboardButton("🏠 Home", callback_data="home"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ])
        await query.message.edit_text(text[:4000], reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        LOGGER.error(f"cb_show_batch error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^manage_batch$"))
async def cb_manage_batch(bot: Client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        batches = await db_instance.get_all_batches(user_id)
        if not batches:
            return await query.answer("📭 You have no batches yet.", show_alert=True)

        buttons = []
        for batch in batches:
            cid  = batch.get("course_id", "")
            name = batch.get("select", "Unknown")
            buttons.append([InlineKeyboardButton(f"⚙️ {name[:30]}", callback_data=f"stats_{cid}")])

        buttons.append([
            InlineKeyboardButton("🏠 Home", callback_data="home"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ])
        await query.message.edit_text(
            "<b>╭━━━━━━━━━━━━━━━━━━╮\n┃  ⚙️ MANAGE BATCH\n╰━━━━━━━━━━━━━━━━━━╯</b>\n\nSelect a batch:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        LOGGER.error(f"cb_manage_batch error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^delete_batch$"))
async def cb_delete_batch_list(bot: Client, query: CallbackQuery):
    try:
        if not Config.is_admin(query.from_user.id):
            return await query.answer("🔒 Admin only.", show_alert=True)

        user_id = query.from_user.id
        batches = await db_instance.get_all_batches(user_id)
        if not batches:
            return await query.answer("📭 You have no batches to delete.", show_alert=True)

        buttons = []
        for batch in batches:
            cid  = batch.get("course_id", "")
            name = batch.get("select", "Unknown")
            buttons.append([InlineKeyboardButton(f"🗑️ {name[:30]}", callback_data=f"del_{cid}")])

        buttons.append([
            InlineKeyboardButton("🏠 Home", callback_data="home"),
            InlineKeyboardButton("❌ Close", callback_data="close")
        ])
        await query.message.edit_text(
            "<b>╭━━━━━━━━━━━━━━━━━━╮\n┃  🗑️ DELETE BATCH\n╰━━━━━━━━━━━━━━━━━━╯</b>\n\nSelect a batch to delete:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        LOGGER.error(f"cb_delete_batch_list error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^del_"))
async def cb_delete_specific(bot: Client, query: CallbackQuery):
    try:
        if not Config.is_admin(query.from_user.id):
            return await query.answer("🔒 Admin only.", show_alert=True)

        user_id   = query.from_user.id
        course_id = query.data.replace("del_", "")
        await db_instance.delete_batch(user_id, course_id)
        await query.answer("✅ Batch deleted!", show_alert=True)
        try:
            await query.message.edit_text(msg.BATCH_DELETED, reply_markup=buttom.back_home())
        except Exception:
            pass
    except Exception as e:
        LOGGER.error(f"cb_delete_specific error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^stats_"))
async def cb_stats(bot: Client, query: CallbackQuery):
    try:
        user_id   = query.from_user.id
        course_id = query.data.replace("stats_", "")

        batch = await db_instance.get_batch(user_id, course_id)
        if not batch:
            return await query.answer("❌ Batch not found.", show_alert=True)

        status_doc = await db_instance.get_batch_status(user_id, course_id)
        status     = status_doc.get("status", "unknown") if status_doc else "not started"

        pdf_count   = await db_instance.uploaded_files.count_documents(
            {"course_id": course_id, "url": {"$regex": r"\.pdf", "$options": "i"}}
        )
        video_count = await db_instance.uploaded_files.count_documents({"course_id": course_id})

        text = msg.BATCH_STATUS.format(
            course_id, batch.get("select", "Unknown"), status.upper(),
            pdf_count, video_count - pdf_count, batch.get("time", "Manual"),
        )
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Re-run Upload", callback_data=f"rerun_{course_id}")],
            [InlineKeyboardButton("🗑️ Delete Batch",  callback_data=f"del_{course_id}")],
            [InlineKeyboardButton("🏠 Home", callback_data="home"),
             InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        await query.message.edit_text(text, reply_markup=buttons)
    except Exception as e:
        LOGGER.error(f"cb_stats error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass


@Client.on_callback_query(filters.regex("^rerun_"))
async def cb_rerun(bot: Client, query: CallbackQuery):
    try:
        if not Config.is_admin(query.from_user.id):
            return await query.answer("🔒 Admin only.", show_alert=True)

        course_id = query.data.replace("rerun_", "")
        batch     = await db_instance.get_batch_by_course_id(course_id)
        if not batch:
            return await query.answer("❌ Batch not found.", show_alert=True)

        token       = batch.get("token", "")
        group_id    = batch.get("group_id", "")
        course_name = batch.get("select", "Unknown")

        try:
            await query.message.edit_text(
                f"🔄 <b>Re-running upload for:</b> {course_name}\n\nChecking for new content...",
                reply_markup=buttom.back_home()
            )
        except Exception:
            pass

        async def run():
            from modules.cpdata import collect_data
            from modules.tasks import process_batch_upload
            all_data = await collect_data(course_id, token)
            if all_data:
                await process_batch_upload(bot, course_id, all_data)
                try:
                    await bot.send_message(int(group_id), f"✅ Re-run complete for: <b>{course_name}</b>")
                except Exception:
                    pass
            else:
                try:
                    await bot.send_message(int(group_id), f"ℹ️ No new content for: <b>{course_name}</b>")
                except Exception:
                    pass

        asyncio.create_task(run())
        await query.answer("✅ Re-run started!", show_alert=True)

    except Exception as e:
        LOGGER.error(f"cb_rerun error: {e}")
        try:
            await query.answer(f"⚠️ {e}", show_alert=True)
        except Exception:
            pass
