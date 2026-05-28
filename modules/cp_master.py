"""
modules/cp_master.py — Classplus login, batch selection, and batch add flow
"""
import asyncio
import uuid
import base64
import io
import json
import re
import pytz
from datetime import datetime
from pyrogram.types import InlineKeyboardButton as KB, InlineKeyboardMarkup as KM
from logger import LOGGER
from config import Config
from master.database import db_instance
from master.server import HttpxClient
from modules import cpdata
from constant import msg

IST = pytz.timezone('Asia/Kolkata')
CP_API = "https://api.classplusapp.com"

scraper = HttpxClient(verify_ssl=False)

# In-memory store for pending batch confirmations
pending_batches = {}


# ─── Helpers ────────────────────────────────────────────────────────────────

def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload (no signature verification needed)."""
    try:
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        return json.loads(base64.b64decode(
            payload_b64.replace('-', '+').replace('_', '/')
        ))
    except Exception:
        return {}


def get_base_headers(device_id=None):
    did = device_id or str(uuid.uuid4()).replace('-', '')[:16]
    return {
        "Accept": "application/json, text/plain, */*",
        "region": "IN",
        "accept-language": "en",
        "Content-Type": "application/json;charset=utf-8",
        "Api-Version": "29",
        "device-id": did,
        "user-agent": "Mobile-Android",
        "app-version": "1.4.65.3",
        "device-details": did + "_2848b866799971ca_SDK-30",
        "accept-encoding": "gzip",
    }


def mode_keyboard(user_id, batch_id):
    return KM([
        [KB("📄 Get .txt File",           callback_data=f"cpmode_txt_{user_id}_{batch_id}")],
        [KB("📤 Upload to Telegram Group", callback_data=f"cpmode_upload_{user_id}_{batch_id}")],
        [KB("❌ Cancel",                   callback_data="close")],
    ])


# ─── Login ──────────────────────────────────────────────────────────────────

async def token_login(token):
    """Verify a direct Classplus token."""
    valid = await cpdata.verify_token(token)
    if valid:
        return {"success": True, "token": token, "message": "Token verified"}
    return {"success": False, "message": "Invalid or expired token"}


async def otp_login(org_code_mobile, editable, bot, m):
    """OTP-based Classplus login.  Format: ORGCODE*MobileNumber"""

    async def safe_edit(text):
        try:
            await editable.edit_text(text)
        except Exception:
            pass

    try:
        parts = org_code_mobile.strip().split("*")
        if len(parts) != 2:
            return {"success": False, "message": "Invalid format. Use ORGCODE*Mobile"}

        org_code, mobile = parts[0].strip(), parts[1].strip()
        device_id = str(uuid.uuid4()).replace('-', '')[:16]
        headers = get_base_headers(device_id)

        await safe_edit("🔍 Fetching organization details...")
        org_resp = await scraper.get(f"{CP_API}/v2/orgs/{org_code}", headers=headers)
        if org_resp.status_code != 200:
            return {"success": False, "message": f"Org not found: {org_code}"}

        org_data = org_resp.json().get("data", {})
        org_id   = org_data.get("orgId", "")
        org_name = org_data.get("orgName", org_code)

        await safe_edit(f"📱 Sending OTP to {mobile}...")
        otp_payload = {
            "countryExt": "91",
            # FIX: Use org_code (user input) not org_name — API expects the code, not display name
            "orgCode": org_code,
            "viaSms": "1",
            "mobile": mobile,
            "orgId": org_id,
            "otpCount": 0,
        }
        otp_resp = await scraper.post(f"{CP_API}/v2/otp/generate", json=otp_payload, headers=headers)
        if otp_resp.status_code != 200:
            otp_err = ""
            try:
                otp_err = otp_resp.json().get("message", "")
            except Exception:
                pass
            return {"success": False, "message": f"Failed to send OTP: {otp_resp.status_code} {otp_err}"}

        otp_resp_data = otp_resp.json().get("data") or {}
        session_id = otp_resp_data.get("sessionId", "")
        await safe_edit(msg.OTP_SENT)

        otp_input = await bot.listen(m.chat.id, timeout=180)
        otp = otp_input.text.strip()
        try:
            await otp_input.delete()
        except Exception:
            pass

        fingerprint_id = str(uuid.uuid4()).replace('-', '')
        verify_payload = {
            "otp": otp,
            "countryExt": "91",
            "sessionId": session_id,
            "orgId": org_id,
            "fingerprintId": fingerprint_id,
            "mobile": mobile,
            # FIX: some Classplus endpoints require name in verify payload
            "name": "Student",
        }
        verify_resp = await scraper.post(f"{CP_API}/v2/users/verify", json=verify_payload, headers=headers)
        LOGGER.info(f"verify_resp status={verify_resp.status_code}")

        if verify_resp.status_code == 200:
            verify_data = verify_resp.json()
            LOGGER.info(f"verify_data={verify_data}")
            if verify_data.get("status") == "success":
                # FIX: token can be nested under data.token or data.data.token
                vdata = verify_data.get("data") or {}
                token = vdata.get("token") or (vdata.get("data") or {}).get("token", "")
                if token:
                    return {"success": True, "token": token, "message": "Login Successful"}
            # Return actual server message for debugging
            err_msg = verify_data.get("message") or verify_data.get("msg") or "OTP verification failed"
            return {"success": False, "message": err_msg}
        return {"success": False, "message": f"Verification failed: {verify_resp.status_code}"}

    except asyncio.TimeoutError:
        return {"success": False, "message": "OTP timeout. Try again."}
    except Exception as e:
        LOGGER.error(f"otp_login error: {e}")
        return {"success": False, "message": str(e)}


# ─── Batch Add Flow ─────────────────────────────────────────────────────────

async def add_batch(bot, m, token, user_id=None):
    """
    Step 1 of batch-add flow:
      Fetch batches → show numbered list → user selects → show mode buttons.
    The rest is handled by cpmode_txt / cpmode_upload callbacks.
    """
    if user_id is None:
        user_id = m.from_user.id

    chat_id = m.chat.id

    try:
        editable = await bot.send_message(chat_id, "📚 Fetching your Classplus batches...")
        batches = await cpdata.get_batch_list(token)

        if not batches:
            await editable.edit_text(
                "❌ <b>No batches found for this account.</b>\n\n"
                "Please check your token is valid and you are enrolled in at least one batch."
            )
            return

        # Build numbered list
        batch_text = "<b>📚 Available Batches</b>\n\n"
        batch_map = {}
        for i, batch in enumerate(batches, start=1):
            b_id = str(
                batch.get("id") or batch.get("batchId") or
                batch.get("courseId") or batch.get("_id") or ""
            )
            b_name = (
                batch.get("name") or batch.get("batchName") or
                batch.get("courseName") or "Unknown"
            )
            batch_map[str(i)] = {"id": b_id, "name": b_name}
            batch_text += f"{i}. {b_name}\n"
            if len(batch_text) > 3800:
                await editable.edit_text(batch_text)
                editable = await bot.send_message(chat_id, "(continued...)")
                batch_text = ""

        batch_text += "\n<b>Reply with the number (e.g. <code>1</code>) to select a batch:</b>"
        await editable.edit_text(batch_text[:4000])

        # Wait for user selection
        batch_input = await bot.listen(chat_id, timeout=120)
        selection = batch_input.text.strip()
        try:
            await batch_input.delete()
        except Exception:
            pass

        selected = batch_map.get(selection)
        if not selected:
            await bot.send_message(
                chat_id,
                f"❌ Invalid selection: <code>{selection}</code>\n"
                f"Please enter a number between 1 and {len(batches)}."
            )
            return

        batch_id   = selected["id"]
        batch_name = selected["name"]

        # Store pending info (token kept for both txt and upload flows)
        pending_batches[f"{user_id}_{batch_id}"] = {
            "user_id":   user_id,
            "course_id": batch_id,
            "token":     token,
            "select":    batch_name,
        }

        # Show mode selection buttons
        await bot.send_message(
            chat_id,
            msg.MODE_SELECTION.format(batch_name=batch_name),
            reply_markup=mode_keyboard(user_id, batch_id),
        )

    except asyncio.TimeoutError:
        await bot.send_message(chat_id, "⏰ Timeout! Please try again.")
    except Exception as e:
        LOGGER.error(f"add_batch error: {e}")
        await bot.send_message(chat_id, f"❌ Error: {e}")


# ─── TXT Export ─────────────────────────────────────────────────────────────

async def generate_and_send_txt(bot, chat_id, user_id, batch_id):
    """Fetch all batch content and send as a formatted .txt file."""
    key  = f"{user_id}_{batch_id}"
    data = pending_batches.pop(key, None)
    if not data:
        await bot.send_message(chat_id, "❌ Session expired. Please start again with /start.")
        return

    token      = data["token"]
    batch_name = data["select"]
    course_id  = data["course_id"]

    jwt_payload = decode_jwt_payload(token)
    org_code    = jwt_payload.get("orgCode", "classplus")
    now_ist     = datetime.now(IST).strftime("%d-%m-%Y %I:%M %p IST")

    status_msg = await bot.send_message(chat_id, "⏳ Fetching all batch content... please wait.")

    try:
        items = await cpdata.collect_data(course_id, token)

        # FIX: collect_data can return None on exception — always use list
        if not items:
            items = []

        videos = [x for x in items if x.get("type") == "video"]
        pdfs   = [x for x in items if x.get("type") == "pdf"]
        others = [x for x in items if x.get("type") not in ("video", "pdf")]

        if not items:
            try:
                await status_msg.edit_text("❌ No content found in this batch. Token may be expired or batch is empty.")
            except Exception:
                await bot.send_message(chat_id, "❌ No content found in this batch.")
            return

        # Build txt — header section first, then a clear separator, then ONLY links
        # The separator "LINKS_START" lets any DRM/downloader bot skip the header safely
        lines = [
            "🎓 COURSE EXTRACTED 🎓",
            "",
            f"📱 APP: {org_code}",
            f"📚 BATCH: {batch_name}",
            f"📅 DATE: {now_ist}",
            "",
            "📊 CONTENT STATS",
            f"├── 📁 Total Links: {len(items)}",
            f"├── 🎬 Videos: {len(videos)}",
            f"├── 📄 PDFs: {len(pdfs)}",
            f"└── 📦 Others: {len(others)}",
            "",
            "=" * 60,
            "# LINKS START BELOW — DO NOT EDIT THIS LINE",
            "=" * 60,
            "",
        ]

        for item in items:
            subject = item.get("subjectName", "")
            name    = item.get("name", "Unknown")
            url     = item.get("url", "")
            # FIX: skip items with no URL — these caused "Skipping invalid link" errors
            if not url or not url.startswith("http"):
                continue
            if subject and subject != name:
                lines.append(f"{subject} - {name}: {url}")
            else:
                lines.append(f"{name}: {url}")

        txt_content = "\n".join(lines)
        txt_bytes   = txt_content.encode("utf-8")
        file_name   = f"{batch_name}.txt".replace("/", "_").replace("\\", "_")

        try:
            await status_msg.delete()
        except Exception:
            pass

        caption = (
            f"🎓 <b>COURSE EXTRACTED</b> 🎓\n\n"
            f"📱 <b>APP:</b> {org_code}\n"
            f"📚 <b>BATCH:</b> {batch_name}\n"
            f"📅 <b>DATE:</b> {now_ist}\n\n"
            f"📊 <b>CONTENT STATS</b>\n"
            f"├── 📁 Total Links: {len(items)}\n"
            f"├── 🎬 Videos: {len(videos)}\n"
            f"├── 📄 PDFs: {len(pdfs)}\n"
            f"└── 📦 Others: {len(others)}"
        )

        await bot.send_document(
            chat_id,
            document=io.BytesIO(txt_bytes),
            file_name=file_name,
            caption=caption,
        )

    except Exception as e:
        LOGGER.error(f"generate_and_send_txt error: {e}")
        try:
            await status_msg.edit_text(f"❌ Error generating txt file: {e}")
        except Exception:
            await bot.send_message(chat_id, f"❌ Error: {e}")


# ─── Upload Flow (continued after mode selection) ────────────────────────────

async def continue_upload_setup(bot, chat_id, user_id, batch_id):
    """
    Step 2 of upload flow (after user chose 'Upload to Telegram').
    Asks group, schedule, credit, filename, thumb, then shows confirm button.
    """
    key  = f"{user_id}_{batch_id}"
    data = pending_batches.get(key)
    if not data:
        await bot.send_message(chat_id, "❌ Session expired. Please start again.")
        return

    batch_name = data["select"]

    try:
        # Group ID
        gm = await bot.send_message(chat_id, msg.GROUP_SETUP)
        gi = await bot.listen(chat_id, timeout=120)
        group_id = gi.text.strip()
        try:
            await gi.delete()
        except Exception:
            pass
        await gm.edit_text("🔍 Verifying group access...")
        ok = await verify_group(bot, group_id, gm)
        if not ok:
            return

        # Schedule time
        tm = await bot.send_message(chat_id, msg.TIME_SETUP)
        ti = await bot.listen(chat_id, timeout=120)
        schedule_time = ti.text.strip()
        try:
            await ti.delete()
        except Exception:
            pass
        if schedule_time.lower() == "no":
            schedule_time = None
        else:
            if not re.match(r'^\d{1,2}:\d{2}$', schedule_time):
                await tm.edit_text("❌ Invalid time format. Use HH:MM (e.g. 08:00) or 'no'.")
                return
        try:
            await tm.delete()
        except Exception:
            pass

        # Credit / caption
        cm = await bot.send_message(chat_id, msg.CREDIT_OPTIONS)
        ci = await bot.listen(chat_id, timeout=120)
        credit = ci.text.strip()
        if credit.lower() == "no":
            credit = ""
        try:
            await ci.delete()
            await cm.delete()
        except Exception:
            pass

        # Filename prefix
        fm = await bot.send_message(chat_id, msg.FILENAME_OPTIONS)
        fi = await bot.listen(chat_id, timeout=120)
        filename_prefix = fi.text.strip()
        if filename_prefix.lower() == "no":
            filename_prefix = ""
        try:
            await fi.delete()
            await fm.delete()
        except Exception:
            pass

        # Thumbnail URL
        thm = await bot.send_message(chat_id, msg.THUMB_OPTIONS)
        thi = await bot.listen(chat_id, timeout=120)
        thumb_url = thi.text.strip()
        if thumb_url.lower() == "no" or not thumb_url.startswith("http"):
            thumb_url = None
        try:
            await thi.delete()
            await thm.delete()
        except Exception:
            pass

        # Update pending data with full upload config
        pending_batches[key].update({
            "time":     schedule_time,
            "group_id": group_id,
            "length":   0,
            "credit":   credit,
            "filename": filename_prefix,
            "thumb":    thumb_url,
        })

        confirm_text = msg.CONFIRM_CONFIG.format(
            batch_name, batch_id, group_id,
            schedule_time or "Manual only", credit or "None"
        )
        await bot.send_message(
            chat_id,
            confirm_text,
            reply_markup=KM([
                [KB("✅ Confirm & Start Upload", callback_data=f"cpconfirm_{user_id}_{batch_id}")],
                [KB("❌ Cancel",                 callback_data="close")],
            ])
        )

    except asyncio.TimeoutError:
        await bot.send_message(chat_id, "⏰ Timeout! Please try again.")
    except Exception as e:
        LOGGER.error(f"continue_upload_setup error: {e}")
        await bot.send_message(chat_id, f"❌ Error: {e}")


# ─── Confirm & Process ───────────────────────────────────────────────────────

async def confirm_and_process_batch(bot, user_id, batch_id):
    """Called after user confirms upload setup. Save to DB and start upload."""
    key  = f"{user_id}_{batch_id}"
    data = pending_batches.pop(key, None)
    if not data:
        return False

    await db_instance.add_batch(
        user_id   = data["user_id"],
        course_id = data["course_id"],
        token     = data["token"],
        select    = data["select"],
        time      = data["time"],
        group_id  = data["group_id"],
        length    = data["length"],
        credit    = data["credit"],
        filename  = data["filename"],
        thumb     = data["thumb"],
    )
    await db_instance.save_batch_status(user_id, batch_id, "pending")

    asyncio.create_task(_run_batch(bot, data))

    if data.get("time"):
        from modules.scheduler import schedule_batch_update
        asyncio.create_task(schedule_batch_update(
            bot, data["course_id"], data["time"],
            data["token"], 0, data["select"], data["group_id"],
        ))

    return True


async def _run_batch(bot, data):
    """Background: collect and upload all batch content."""
    from modules.cpdata import collect_data
    from modules.tasks import process_batch_upload

    course_id  = data["course_id"]
    token      = data["token"]
    group_id   = data["group_id"]
    batch_name = data["select"]

    try:
        await bot.send_message(int(group_id), msg.COLLECTING_DATA)
        all_data = await collect_data(course_id, token)
        if all_data:
            await process_batch_upload(bot, course_id, all_data)
        else:
            await bot.send_message(int(group_id), f"❌ No content found for batch: {batch_name}")
    except Exception as e:
        LOGGER.error(f"_run_batch error: {e}")


# ─── Group Verify ────────────────────────────────────────────────────────────

async def verify_group(bot, group_id, editable):
    """Verify bot has admin access in the group."""
    try:
        group_id_int = int(group_id)
        chat   = await bot.get_chat(group_id_int)
        me     = await bot.get_me()
        member = await bot.get_chat_member(group_id_int, me.id)

        if member.privileges:
            try:
                await editable.edit_text(f"✅ Group verified: <b>{chat.title}</b>")
            except Exception:
                pass
            return True
        else:
            try:
                await editable.edit_text(msg.GROUP_ERROR)
            except Exception:
                pass
            return False
    except ValueError:
        try:
            await editable.edit_text("❌ Invalid Group ID. Must be a negative number (e.g. -1001234567890)")
        except Exception:
            pass
        return False
    except Exception as e:
        try:
            await editable.edit_text(f"❌ Cannot access group: {e}\n\n{msg.GROUP_ERROR}")
        except Exception:
            pass
        return False
