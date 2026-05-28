"""
modules/tasks.py — Download + upload pipeline
Fixed flow:
  1. Resolve URL → plain HLS / DRM MPD / original
  2. If HLS → download_hls (httpx, auth headers) — NO yt-dlp CDN 403 issue
  3. If DRM MPD → download_drm (yt-dlp encrypted + mp4decrypt + ffmpeg)
  4. If plain MP4 → yt-dlp normally
  5. PDF → download_file (httpx+auth for Classplus CDN)
"""
import asyncio
import os
from logger import LOGGER
from config import Config
from master.database import db_instance
from master import helper, logdb
from constant import msg, buttom
from modules.manager import get_or_create_topic
from modules.cpdata import get_signed_video_url


async def process_batch_upload(bot, course_id, all_data):
    if not all_data:
        LOGGER.warning(f"Empty data for course_id: {course_id}")
        return

    batch = await db_instance.get_batch_by_course_id(course_id)
    if not batch:
        LOGGER.error(f"Batch not found: {course_id}")
        return

    user_id       = batch.get("user_id")
    course_name   = batch.get("select", "Unknown Batch")
    credit        = batch.get("credit", "")
    filename_prefix = batch.get("filename", "")
    thumb_url     = batch.get("thumb", None)
    chat_id       = batch.get("group_id", "")
    token         = batch.get("token", "")

    await db_instance.save_batch_status(user_id, course_id, "processing")
    save_dir = os.path.join("downloads", str(course_id))
    os.makedirs(save_dir, exist_ok=True)

    p_count = v_count = 0

    for i, item in enumerate(all_data):
        try:
            url          = item.get("url", "")
            name         = item.get("name", f"file_{i+1}")
            file_type    = item.get("type", "video")
            subject_name = item.get("subjectName", "General")
            topic_name   = item.get("topicName", "General")
            timestamp    = item.get("timestamp", "")

            if not url:
                continue

            if await db_instance.is_file_uploaded(course_id, url):
                LOGGER.info(f"Skip (already uploaded): {name}")
                continue

            forum_id = await get_or_create_topic(bot, chat_id, subject_name)
            safe_name = await helper.sanitize_name(name)
            display_name = f"{filename_prefix} {safe_name}".strip() if filename_prefix else safe_name
            ts_str = helper.convert_timestamp(timestamp) if timestamp else "N/A"

            video_caption = msg.VIDEO_CAPTION_V2.format(display_name, course_name, topic_name, ts_str, credit or "")
            pdf_caption   = msg.PDF_CAPTION_V2.format(display_name, course_name, topic_name, ts_str, credit or "")

            # ── Check log channel cache ────────────────────────────────────
            already_sent = await logdb.check_and_send_from_db(
                bot, url, chat_id, video_caption, pdf_caption, p_count, v_count, forum_id
            )
            if already_sent:
                await db_instance.mark_file_uploaded(course_id, url, chat_id)
                if file_type == "pdf":
                    p_count += 1
                else:
                    v_count += 1
                continue

            # ── YouTube ────────────────────────────────────────────────────
            if file_type == "youtube":
                yt_id = await helper.get_youtube_video_id(url)
                if yt_id:
                    yt_url = f"https://www.youtube.com/watch?v={yt_id}"
                    kb = buttom.yt_keyboard(yt_url, yt_url)
                    kwargs = {
                        "chat_id": int(chat_id),
                        "text": f"{msg.YT_VIDEO_CAPTION}\n\n<b>{display_name}</b>\n\n{credit}",
                        "reply_markup": kb,
                        "disable_web_page_preview": False,
                    }
                    if forum_id:
                        kwargs["message_thread_id"] = forum_id
                    sent = await bot.send_message(**kwargs)
                    await db_instance.save_msg_id(url, sent.id)
                    await db_instance.mark_file_uploaded(course_id, url, chat_id)
                    v_count += 1
                continue

            # ── PDF ────────────────────────────────────────────────────────
            if file_type == "pdf":
                output_path = os.path.join(save_dir, f"{safe_name}.pdf")
                LOGGER.info(f"Downloading PDF: {name}")
                dl_path = await helper.download_file(url, output_path, token=token)
                if dl_path and os.path.exists(dl_path):
                    await helper.send_pdf(bot, url, pdf_caption, dl_path, display_name, chat_id, forum_id)
                    await db_instance.mark_file_uploaded(course_id, url, chat_id)
                    p_count += 1
                else:
                    LOGGER.error(f"PDF download failed: {name}")
                continue

            # ── Video: resolve URL first ───────────────────────────────────
            LOGGER.info(f"Processing video: {name}")
            resolved = await get_signed_video_url(url, token)

            output_path = os.path.join(save_dir, f"{safe_name}.mkv")
            downloaded = None

            # ── Case A: DRM (MPD + decryption keys) ───────────────────────
            if "mpd" in resolved and resolved.get("keys"):
                LOGGER.info(f"DRM video: {name}")
                downloaded = await helper.download_drm(
                    resolved["mpd"], resolved["keys"], output_path, quality="720"
                )

            # ── Case B: HLS m3u8 ─────────────────────────────────────────
            elif "url" in resolved and "m3u8" in resolved["url"].lower():
                signed_url = resolved["url"]
                used_token = resolved.get("token", token)
                is_direct_cdn = resolved.get("direct_cdn", False)

                if is_direct_cdn:
                    # CDN URL with no signed token — try ffmpeg direct stream first
                    LOGGER.info(f"CDN direct HLS (ffmpeg): {name}")
                    downloaded = await helper.download_hls_ffmpeg(signed_url, output_path, used_token)

                if not downloaded:
                    # httpx segment-by-segment download
                    LOGGER.info(f"HLS video (httpx downloader): {name}")
                    downloaded = await helper.download_hls(signed_url, output_path, used_token)

                if not downloaded:
                    # Last resort: yt-dlp with headers
                    LOGGER.warning(f"httpx HLS failed, trying yt-dlp: {name}")
                    hdr_args = (
                        f'--add-header "x-access-token:{used_token}" '
                        f'--add-header "user-agent:Mobile-Android" '
                        f'--add-header "Api-Version:29" '
                        f'--add-header "X-CDN-Tag:empty" '
                    )
                    cmd = (
                        f'yt-dlp -o "{output_path}" --no-check-certificate '
                        f'{hdr_args}'
                        f'--hls-prefer-native --hls-use-mpegts '
                        f'-R 5 --fragment-retries 5 --concurrent-fragments 4 '
                        f'"{signed_url}"'
                    )
                    proc = await asyncio.create_subprocess_shell(
                        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()
                    for ext in [".mkv", ".mp4", ".webm", ".ts"]:
                        c = output_path.replace(".mkv", ext)
                        if os.path.exists(c) and os.path.getsize(c) > 0:
                            downloaded = c
                            break

            # ── Case C: Plain MP4 / other ──────────────────────────────────
            elif "url" in resolved:
                signed_url = resolved["url"]
                used_token = resolved.get("token", token)
                LOGGER.info(f"Plain video (yt-dlp): {name}")
                hdr_args = (
                    f'--add-header "x-access-token:{used_token}" '
                    f'--add-header "user-agent:Mobile-Android" '
                    f'--add-header "Api-Version:29" '
                    f'--add-header "X-CDN-Tag:empty" '
                )
                cmd = (
                    f'yt-dlp -o "{output_path}" --no-check-certificate '
                    f'{hdr_args}'
                    f'-R 10 --fragment-retries 10 --retry-sleep 3 '
                    f'--concurrent-fragments 4 "{signed_url}"'
                )
                proc = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                for ext in [".mkv", ".mp4", ".webm", ".ts"]:
                    c = output_path.replace(".mkv", ext)
                    if os.path.exists(c) and os.path.getsize(c) > 0:
                        downloaded = c
                        break

            # ── Upload or log error ────────────────────────────────────────
            if downloaded and os.path.exists(downloaded) and os.path.getsize(downloaded) > 0:
                await helper.send_vid(
                    bot, url, video_caption, downloaded, display_name, chat_id, forum_id, thumb_url
                )
                await db_instance.mark_file_uploaded(course_id, url, chat_id)
                v_count += 1
            else:
                LOGGER.error(f"Video download FAILED: {name}")
                try:
                    await bot.send_message(
                        int(Config.LOG_CHANNEL),
                        msg.ERROR_UPLOADING.format(name, url, "Download failed after all fallbacks"),
                    )
                except Exception:
                    pass

            await asyncio.sleep(2)

        except Exception as e:
            LOGGER.error(f"Error processing item {i} ({item.get('name', '?')}): {e}")
            try:
                await bot.send_message(
                    int(Config.LOG_CHANNEL),
                    msg.ERROR_UPLOADING.format(item.get("name", "?"), item.get("url", "?"), str(e)),
                )
            except Exception:
                pass
            continue

    await db_instance.save_batch_status(user_id, course_id, "completed")
    LOGGER.info(f"Batch {course_id} done: {v_count} videos, {p_count} PDFs")

    import shutil
    try:
        shutil.rmtree(save_dir, ignore_errors=True)
    except Exception:
        pass
