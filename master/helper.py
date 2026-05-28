"""
master/helper.py — Download, merge, upload helpers
Combines best from: saini drm, without_idpw, classplus-v2-patched
"""
import asyncio
import os
import re
import time
import shutil
import httpx
import requests
from datetime import datetime
from logger import LOGGER
from config import Config
from master.database import db_instance
import pytz

UTC = pytz.utc
IST = pytz.timezone("Asia/Kolkata")

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def convert_timestamp(ts):
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=UTC)
        elif isinstance(ts, str):
            for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(ts, fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = datetime.now(UTC)
        else:
            dt = datetime.now(UTC)
        return dt.astimezone(IST).strftime("%d-%m-%Y %H:%M")
    except Exception as e:
        LOGGER.error(f"Timestamp error: {e}")
        return str(ts)


async def sanitize_name(name):
    if not name:
        return "untitled"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(name))
    name = name.strip().replace("  ", " ")[:180]
    return name or "untitled"


async def duration(video):
    try:
        proc = await asyncio.create_subprocess_shell(
            f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video}"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        return int(float(out.decode().strip()))
    except Exception:
        return 0


async def get_youtube_video_id(url):
    try:
        m = re.search(r'(?:youtube\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([^"&?/\s]{11})', url)
        return m.group(1) if m else None
    except Exception:
        return None


def _cp_auth_headers(token):
    return {
        "x-access-token": token,
        "user-agent": "Mobile-Android",
        "app-version": "1.4.73.2",
        "api-version": "29",
        "device-id": "39F093FF35F201D9",
        "X-CDN-Tag": "empty",
        "region": "IN",
        "accept": "*/*",
    }


# ──────────────────────────────────────────────────────────────────────────────
# PDF / file download (httpx with auth for Classplus CDN)
# ──────────────────────────────────────────────────────────────────────────────
async def download_file(url, output_path, token=None):
    """Download PDF/file. Uses httpx+auth for Classplus CDN, yt-dlp fallback for others."""
    is_cp = any(x in url for x in ["classplusapp", "classplus"])
    if is_cp and token:
        try:
            async with httpx.AsyncClient(verify=False, timeout=120.0, follow_redirects=True) as client:
                async with client.stream("GET", url, headers=_cp_auth_headers(token)) as r:
                    if r.status_code == 200:
                        with open(output_path, "wb") as f:
                            async for chunk in r.aiter_bytes(65536):
                                f.write(chunk)
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            LOGGER.info(f"httpx PDF download OK: {output_path}")
                            return output_path
                    LOGGER.warning(f"httpx PDF got {r.status_code}, trying yt-dlp")
        except Exception as e:
            LOGGER.warning(f"httpx PDF failed: {e}, trying yt-dlp")

    # Fallback: yt-dlp
    try:
        cmd = f'yt-dlp -o "{output_path}" --no-check-certificate "{url}"'
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and os.path.exists(output_path):
            return output_path
        LOGGER.error(f"yt-dlp PDF failed: {stderr.decode()[:300]}")
        return None
    except Exception as e:
        LOGGER.error(f"download_file error: {e}")
        return None




# ──────────────────────────────────────────────────────────────────────────────
# FFmpeg direct HLS stream (for CDN URLs where signing failed but CDN accepts headers)
# ──────────────────────────────────────────────────────────────────────────────
async def download_hls_ffmpeg(m3u8_url: str, output_path: str, token: str) -> str | None:
    """
    Use ffmpeg to directly download HLS — ffmpeg handles CDN auth headers natively.
    This works when CDN accepts token in header even without jw-signed URL.
    """
    try:
        hdrs = (
            f"x-access-token: {token}\r\n"
            f"user-agent: Mobile-Android\r\n"
            f"Api-Version: 29\r\n"
            f"X-CDN-Tag: empty\r\n"
            f"region: IN"
        )
        cmd = (
            f'ffmpeg -y '
            f'-headers "{hdrs}" '
            f'-i "{m3u8_url}" '
            f'-c copy -bsf:a aac_adtstoasc '
            f'"{output_path}" -loglevel warning'
        )
        LOGGER.info(f"ffmpeg HLS stream: {m3u8_url[:80]}")
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, err = await proc.communicate()

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            LOGGER.info(f"ffmpeg HLS OK: {output_path}")
            return output_path

        LOGGER.warning(f"ffmpeg HLS failed: {err.decode()[:200]}")
        return None
    except Exception as e:
        LOGGER.error(f"download_hls_ffmpeg error: {e}")
        return None

# ──────────────────────────────────────────────────────────────────────────────
# HLS download (httpx-based, bypasses CDN 403)
# ──────────────────────────────────────────────────────────────────────────────
async def download_hls(m3u8_url: str, output_path: str, token: str) -> str | None:
    """
    Download HLS m3u8 using httpx with auth headers.
    Fetches manifest → finds best quality sub-manifest → downloads all .ts segments → merges with ffmpeg.
    This is the key fix: replaces yt-dlp which gets 403 on Classplus CDN.
    """
    headers = _cp_auth_headers(token)
    seg_dir = output_path + "_segs"
    os.makedirs(seg_dir, exist_ok=True)

    try:
        async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
            # Fetch master m3u8
            r = await client.get(m3u8_url, headers=headers)
            if r.status_code != 200:
                LOGGER.warning(f"m3u8 master fetch got {r.status_code}")
                return None

            manifest = r.text
            base_url = m3u8_url.rsplit("/", 1)[0] + "/"

            # Find best quality sub-manifest (highest bandwidth)
            lines = manifest.splitlines()
            best_bw = -1
            best_sub = None
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("#EXT-X-STREAM-INF"):
                    bw_match = re.search(r"BANDWIDTH=(\d+)", line)
                    bw = int(bw_match.group(1)) if bw_match else 0
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not next_line.startswith("#"):
                            if bw > best_bw:
                                best_bw = bw
                                best_sub = next_line
                i += 1

            if best_sub:
                sub_url = best_sub if best_sub.startswith("http") else base_url + best_sub
                LOGGER.info(f"Using sub-manifest (bw={best_bw}): {sub_url[:80]}")
                r2 = await client.get(sub_url, headers=headers)
                if r2.status_code == 200:
                    manifest = r2.text
                    base_url = sub_url.rsplit("/", 1)[0] + "/"

            # Collect .ts segment URLs
            segments = []
            for line in manifest.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    seg_url = line if line.startswith("http") else base_url + line
                    segments.append(seg_url)

            if not segments:
                LOGGER.warning("No segments found in m3u8 manifest")
                return None

            LOGGER.info(f"Downloading {len(segments)} HLS segments...")
            seg_files = []

            # Download segments with concurrency
            sem = asyncio.Semaphore(8)

            async def dl_seg(idx, seg_url):
                async with sem:
                    seg_path = os.path.join(seg_dir, f"seg_{idx:06d}.ts")
                    for attempt in range(4):
                        try:
                            rs = await client.get(seg_url, headers=headers, timeout=30.0)
                            if rs.status_code == 200:
                                with open(seg_path, "wb") as f:
                                    f.write(rs.content)
                                return seg_path
                            LOGGER.warning(f"Seg {idx} got {rs.status_code}, attempt {attempt+1}")
                        except Exception as e:
                            LOGGER.warning(f"Seg {idx} attempt {attempt+1} error: {e}")
                        await asyncio.sleep(1.5)
                    return None

            results = await asyncio.gather(*[dl_seg(i, u) for i, u in enumerate(segments)])
            seg_files = [f for f in results if f]

            if len(seg_files) < len(segments) * 0.8:
                LOGGER.error(f"Too many failed segments: {len(seg_files)}/{len(segments)}")
                return None

            # Merge with ffmpeg
            concat_file = os.path.join(seg_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for sf in sorted(seg_files):
                    f.write(f"file '{sf}'\n")

            proc = await asyncio.create_subprocess_shell(
                f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}" -loglevel warning',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, ffmpeg_err = await proc.communicate()

            shutil.rmtree(seg_dir, ignore_errors=True)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                LOGGER.info(f"HLS download OK: {output_path} ({os.path.getsize(output_path)//1024}KB)")
                return output_path

            LOGGER.error(f"HLS merge failed: {ffmpeg_err.decode()[:300]}")
            return None

    except Exception as e:
        LOGGER.error(f"download_hls error: {e}")
        shutil.rmtree(seg_dir, ignore_errors=True)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# DRM video download (MPD + mp4decrypt)
# ──────────────────────────────────────────────────────────────────────────────
async def download_drm(mpd_url: str, keys: list, output_path: str, quality: str = "720") -> str | None:
    """
    Download DRM-encrypted video:
    1. yt-dlp downloads encrypted mp4+m4a
    2. mp4decrypt decrypts using extracted keys
    3. ffmpeg merges audio+video
    """
    work_dir = output_path + "_drm"
    os.makedirs(work_dir, exist_ok=True)

    try:
        # Step 1: Download encrypted streams
        cmd_dl = (
            f'yt-dlp -f "bv[height<={quality}]+ba/b" '
            f'-o "{work_dir}/file.%(ext)s" '
            f'--allow-unplayable-formats '
            f'--no-check-certificate '
            f'--external-downloader aria2c '
            f'"{mpd_url}"'
        )
        LOGGER.info(f"DRM download: {mpd_url[:80]}")
        proc = await asyncio.create_subprocess_shell(
            cmd_dl, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, err = await proc.communicate()

        files_in_dir = list(os.scandir(work_dir))
        if not files_in_dir:
            LOGGER.error(f"DRM download produced no files: {err.decode()[:300]}")
            return None

        # Build mp4decrypt key string
        keys_str = " ".join(f"--key {k}" for k in keys)

        video_dec = os.path.join(work_dir, "video.mp4")
        audio_dec = os.path.join(work_dir, "audio.m4a")

        for f in files_in_dir:
            if f.name.endswith(".mp4") and "video" not in f.name:
                os.system(f'mp4decrypt {keys_str} --show-progress "{f.path}" "{video_dec}"')
                os.remove(f.path)
            elif f.name.endswith(".m4a"):
                os.system(f'mp4decrypt {keys_str} --show-progress "{f.path}" "{audio_dec}"')
                os.remove(f.path)

        if not os.path.exists(video_dec):
            LOGGER.error("DRM: video decryption failed")
            return None

        # Merge
        merge_cmd = f'ffmpeg -y -i "{video_dec}" -i "{audio_dec}" -c copy "{output_path}" -loglevel warning'
        proc2 = await asyncio.create_subprocess_shell(
            merge_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc2.communicate()

        shutil.rmtree(work_dir, ignore_errors=True)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            LOGGER.info(f"DRM download+decrypt OK: {output_path}")
            return output_path

        return None

    except Exception as e:
        LOGGER.error(f"download_drm error: {e}")
        shutil.rmtree(work_dir, ignore_errors=True)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Thumbnail
# ──────────────────────────────────────────────────────────────────────────────
async def generate_thumbnail(video_path):
    try:
        thumb = f"{video_path}_thumb.jpg"
        proc = await asyncio.create_subprocess_shell(
            f'ffmpeg -i "{video_path}" -ss 00:00:05 -vframes 1 "{thumb}" -y -loglevel error',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return thumb if os.path.exists(thumb) else None
    except Exception:
        return None


async def download_thumbnail(url):
    try:
        thumb = f"thumb_{int(time.time())}.jpg"
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            r = await client.get(url, follow_redirects=True)
            if r.status_code == 200:
                with open(thumb, "wb") as f:
                    f.write(r.content)
                if os.path.getsize(thumb) > 0:
                    return thumb
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Telegram send functions
# ──────────────────────────────────────────────────────────────────────────────
async def send_vid(bot, url, caption, filename, name, chat_id, forum_id=None, thumb_url=None):
    thumb = None
    try:
        if thumb_url and thumb_url.startswith("http"):
            thumb = await download_thumbnail(thumb_url)
        if not thumb:
            thumb = await generate_thumbnail(filename)

        dur = await duration(filename)
        safe_name = await sanitize_name(name)

        kwargs = {
            "chat_id": int(chat_id),
            "video": filename,
            "caption": caption,
            "duration": dur,
            "thumb": thumb,
            "file_name": f"{safe_name}.mkv",
            "supports_streaming": True,
        }
        if forum_id:
            kwargs["message_thread_id"] = forum_id

        reply = await bot.send_video(**kwargs)
        await db_instance.save_msg_id(url, reply.id)
        try:
            await reply.copy(int(Config.LOG_CHANNEL))
        except Exception as e:
            LOGGER.error(f"Log copy failed: {e}")
        return reply

    except Exception as e:
        LOGGER.error(f"send_vid error: {e}")
        return None
    finally:
        for f in [thumb, filename]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


async def send_pdf(bot, url, caption, filename, name, chat_id, forum_id=None):
    try:
        safe_name = await sanitize_name(name)
        kwargs = {
            "chat_id": int(chat_id),
            "document": filename,
            "caption": caption,
            "file_name": f"{safe_name}.pdf",
        }
        if forum_id:
            kwargs["message_thread_id"] = forum_id

        reply = await bot.send_document(**kwargs)
        await db_instance.save_msg_id(url, reply.id)
        try:
            await reply.copy(int(Config.LOG_CHANNEL))
        except Exception:
            pass
        return reply

    except Exception as e:
        LOGGER.error(f"send_pdf error: {e}")
        return None
    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass
