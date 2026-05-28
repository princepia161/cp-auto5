"""
modules/cpdata.py
FINAL FIX — Root cause was double URL encoding:
  params={"url": video_url} → httpx encodes → ?url=https%3A%2F%2F... (WRONG)
  f"?url={video_url}" → raw URL in string → ?url=https://media-cdn... (CORRECT)

Also: response check must be response.get('status') == 'ok' AND response.get('url')
"""
import asyncio
import re
import requests
import httpx
from logger import LOGGER

CP_API = "https://api.classplusapp.com"
semaphore = asyncio.Semaphore(5)
DEVICE_ID = "39F093FF35F201D9"

class _HttpxClient:
    def __init__(self):
        self._client = None

    async def get(self, url, **kwargs):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(verify=False, timeout=30.0)
        for attempt in range(2):
            try:
                return await self._client.get(url, **kwargs)
            except Exception as e:
                if attempt == 1:
                    raise
                await asyncio.sleep(1)

scraper = _HttpxClient()


def _signing_headers(token):
    """Exact headers from working bot_v2/classplus.py."""
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip",
        "accept-language": "EN",
        "api-version": "35",
        "app-version": "1.4.73.2",
        "build-number": "35",
        "connection": "Keep-Alive",
        "content-type": "application/json",
        "device-details": "Xiaomi_Redmi 7_SDK-32",
        "device-id": DEVICE_ID,
        "host": "api.classplusapp.com",
        "region": "IN",
        "user-agent": "Mobile-Android",
        "x-access-token": token,
        "webengage-luid": "00000187-6fe4-5d41-a530-26186858be4c",
    }

def _signing_headers_v2(token):
    return {
        "Host": "api.classplusapp.com",
        "x-access-token": token,
        "user-agent": "Mobile-Android",
        "app-version": "1.4.65.3",
        "api-version": "18",
        "device-id": DEVICE_ID,
        "device-details": "2848b866799971ca_2848b8667a33216c_SDK-30",
        "accept-encoding": "gzip",
        "region": "IN",
        "X-CDN-Tag": "empty",
    }

def _signing_headers_v3(token):
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip",
        "accept-language": "en",
        "api-version": "52",
        "app-version": "1.4.73.2",
        "device-id": DEVICE_ID,
        "region": "IN",
        "user-agent": "Mobile-Android",
        "x-access-token": token,
        "X-CDN-Tag": "empty",
    }


async def get_signed_video_url(video_url: str, token: str) -> dict:
    """
    THE KEY FIX: Pass URL directly in query string (f"?url={video_url}"),
    NOT via params= dict which causes double URL-encoding.
    
    Working repos (bot_v2, classplus.py) all use:
      requests.get(f'...jw-signed-url?url={url}', headers=headers)
    NOT:
      requests.get('...jw-signed-url', params={'url': url}, headers=headers)
    """
    LOGGER.info(f"Resolving: {video_url[:80]}")

    # Build endpoint URLs with raw URL appended directly
    endpoints_and_headers = [
        # (endpoint_with_url, headers, label)
        (
            f"{CP_API}/cams/uploader/video/jw-signed-url?url={video_url}",
            _signing_headers(token),
            "cams/api35"
        ),
        (
            f"{CP_API}/cams/uploader/video/jw-signed-url?url={video_url}",
            _signing_headers_v2(token),
            "cams/api18"
        ),
        (
            f"{CP_API}/cams/uploader/video/jw-signed-url?url={video_url}",
            _signing_headers_v3(token),
            "cams/api52"
        ),
    ]

    for attempt_idx, (endpoint, hdrs, label) in enumerate(endpoints_and_headers):
        try:
            r = await scraper.get(endpoint, headers=hdrs, follow_redirects=True)
            status = r.status_code
            LOGGER.info(f"jw-signed-url [{label}] attempt={attempt_idx+1} status={status}")

            if status == 200:
                try:
                    data = r.json()
                except Exception:
                    LOGGER.warning("200 but JSON parse failed")
                    continue

                LOGGER.info(f"Response keys: {list(data.keys())}")

                # Check status == 'ok' and url (bot_v2 pattern)
                if data.get("status") == "ok" and data.get("url"):
                    LOGGER.info(f"Got signed URL (status=ok): {data['url'][:80]}")
                    return {"url": data["url"], "token": token}

                # Direct url key
                if data.get("url"):
                    LOGGER.info(f"Got signed URL (url key): {data['url'][:80]}")
                    return {"url": data["url"], "token": token}

                # Nested data.url
                nested_url = (data.get("data") or {}).get("url")
                if nested_url:
                    LOGGER.info(f"Got signed URL (data.url): {nested_url[:80]}")
                    return {"url": nested_url, "token": token}

                # DRM response
                drm = data.get("drmUrls") or (data.get("data") or {}).get("drmUrls")
                if drm:
                    mpd_url = drm.get("manifestUrl", "")
                    lic_url = drm.get("licenseUrl", "")
                    if mpd_url:
                        LOGGER.info(f"DRM detected: {mpd_url[:80]}")
                        keys = await _get_drm_keys(mpd_url, lic_url, token)
                        return {"mpd": mpd_url, "keys": keys, "license_url": lic_url}

                # Error response
                err = data.get("error") or data.get("message") or str(data)
                LOGGER.warning(f"200 but no URL. Error: {err}")

                # Token invalid for this video — try next header variant
                if "Invalid token" in str(err) or "unauthorized" in str(err).lower():
                    LOGGER.warning("Token invalid for this video")
                    continue

            elif status == 500:
                LOGGER.warning(f"jw-signed-url 500 (API overloaded)")
                await asyncio.sleep(1)
                continue

            elif status == 404:
                LOGGER.warning(f"jw-signed-url 404 — endpoint not found")
                # Don't retry this endpoint, try next
                continue

            elif status == 403:
                LOGGER.warning(f"jw-signed-url 403 — access denied")
                continue

        except Exception as e:
            LOGGER.warning(f"jw-signed-url attempt={attempt_idx+1} error: {e}")
            await asyncio.sleep(1)

    # All signing attempts failed
    is_cdn = any(x in video_url for x in [
        "media-cdn.classplusapp", "media-cdn-alisg.classplusapp",
        "media-cdn-a.classplusapp", "tencdn.classplusapp", "videos.classplusapp"
    ])

    if is_cdn:
        LOGGER.info("CDN URL — all signing failed, returning for direct CDN attempt")
        return {"url": video_url, "token": token, "direct_cdn": True}

    LOGGER.warning(f"All resolution failed: {video_url[:80]}")
    return {"url": video_url, "token": token}


async def _get_drm_keys(mpd_url, lic_url, token):
    try:
        from xml.etree import ElementTree as ET
        import glob

        r = requests.get(mpd_url, timeout=15, verify=False)
        if r.status_code != 200:
            return []

        pssh_b64 = None
        try:
            root = ET.fromstring(r.content)
        except ET.ParseError:
            return []

        for elem in root.iter():
            if "ContentProtection" in elem.tag:
                if "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed" in elem.get("schemeIdUri", "").lower():
                    for child in elem:
                        if "pssh" in child.tag.lower() and child.text:
                            pssh_b64 = child.text.strip()
                            break
            if pssh_b64:
                break

        if not pssh_b64:
            return []

        from pywidevine.pssh import PSSH
        from pywidevine.cdm import Cdm
        from pywidevine.device import Device

        wvd_files = glob.glob("WVDs/*.wvd") + glob.glob("./WVDs/*.wvd")
        if not wvd_files:
            return []

        ipssh = PSSH(pssh_b64)
        device = Device.load(wvd_files[0])
        cdm = Cdm.from_device(device)
        sid = cdm.open()
        challenge = cdm.get_license_challenge(sid, ipssh)
        lic_resp = requests.post(
            lic_url, data=challenge,
            headers={"user-agent": "okhttp/4.9.3",
                     "content-type": "application/octet-stream",
                     "x-access-token": token},
            timeout=15
        )
        if lic_resp.status_code != 200:
            cdm.close(sid)
            return []
        cdm.parse_license(sid, lic_resp.content)
        keys = [f"{k.kid.hex}:{k.key.hex()}" for k in cdm.get_keys(sid) if k.type == "CONTENT"]
        cdm.close(sid)
        return keys
    except Exception as e:
        LOGGER.error(f"DRM key error: {e}")
        return []


async def verify_token(token):
    headers = {
        "x-access-token": token, "user-agent": "Mobile-Android",
        "api-version": "29", "device-id": DEVICE_ID, "region": "IN",
    }
    for url in [f"{CP_API}/v2/batches/details?limit=1&offset=0", f"{CP_API}/v2/profile"]:
        try:
            r = await scraper.get(url, headers=headers)
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def classify_url(url, name=""):
    if not url:
        return "unknown"
    ul = url.lower()
    if "youtube.com" in ul or "youtu.be" in ul:
        return "youtube"
    if ".pdf" in ul or "pdf" in name.lower():
        return "pdf"
    return "video"


def _normalize_batch(item):
    b_id = str(item.get("id") or item.get("batchId") or item.get("courseId") or item.get("_id") or "")
    b_name = item.get("name") or item.get("batchName") or item.get("courseName") or item.get("title") or "Unknown"
    return {**item, "id": b_id, "name": b_name}


async def _try_endpoint(headers, url, params, label):
    try:
        r = await scraper.get(url, params=params, headers=headers)
        if r.status_code != 200:
            return []
        data = r.json()
        inner = data.get("data", {}) or {}
        for key in ("list","courses","batches","batchList","courseList",
                    "enrolledCourses","items","result","totalBatches","data"):
            val = inner.get(key)
            if isinstance(val, list) and val:
                return [_normalize_batch(x) for x in val]
        for v in inner.values():
            if isinstance(v, list) and v:
                return [_normalize_batch(x) for x in v]
        return []
    except Exception as e:
        LOGGER.error(f"[{label}] error: {e}")
        return []


async def get_batch_list(token):
    headers = {"x-access-token": token, "user-agent": "Mobile-Android",
               "api-version": "29", "device-id": DEVICE_ID, "region": "IN"}
    for url, params, label in [
        (f"{CP_API}/v2/batches/details", {"limit":"50","offset":"0","sortBy":"createdAt"}, "batches"),
        (f"{CP_API}/v2/courses",          {"limit":"50","offset":"0"}, "courses"),
        (f"{CP_API}/v2/student/courses",  {"limit":"50","offset":"0"}, "student-courses"),
        (f"{CP_API}/v2/course/list",      {"limit":"50","offset":"0"}, "course-list"),
    ]:
        result = await _try_endpoint(headers, url, params, label)
        if result:
            return result
    return []


async def fetch_folder_content(batch_id, folder_id, token, subject_name, topic_name, depth=0):
    if depth > 5:
        return []
    all_items = []
    headers = {"x-access-token": token, "user-agent": "Mobile-Android",
               "api-version": "29", "device-id": DEVICE_ID, "region": "IN"}
    try:
        async with semaphore:
            params = {"courseId": str(batch_id)}
            if folder_id:
                params["folderId"] = str(folder_id)
            r = await scraper.get(f"{CP_API}/v2/course/content/get", params=params, headers=headers)
        if r.status_code != 200:
            return []
        data = (r.json().get("data") or {}).get("courseContent") or []
        for item in data:
            item_id = item.get("id", "")
            item_name = item.get("name", "Untitled")
            item_url = item.get("url", "")
            content_type = item.get("contentType", 2)
            if content_type == 1:
                sub = await fetch_folder_content(batch_id, item_id, token, item_name, topic_name, depth+1)
                all_items.extend(sub)
            else:
                if not item_url:
                    continue
                all_items.append({
                    "id": str(item_id), "name": item_name, "url": item_url,
                    "description": item.get("description", ""),
                    "type": classify_url(item_url, item_name),
                    "subjectName": subject_name, "topicName": topic_name,
                    "contentType": content_type,
                    "timestamp": item.get("createdAt", item.get("updatedAt", "")),
                })
    except Exception as e:
        LOGGER.error(f"fetch_folder_content error: {e}")
    return all_items


async def collect_data(batch_id, token):
    LOGGER.info(f"Collecting data for batch: {batch_id}")
    all_items = []
    try:
        headers = {"x-access-token": token, "user-agent": "Mobile-Android",
                   "api-version": "29", "device-id": DEVICE_ID, "region": "IN"}
        async with semaphore:
            r = await scraper.get(f"{CP_API}/v2/course/content/get",
                                  params={"courseId": str(batch_id)}, headers=headers)
        if r.status_code != 200:
            return []
        top_folders = (r.json().get("data") or {}).get("courseContent") or []
        LOGGER.info(f"Found {len(top_folders)} top-level items")
        tasks = []
        for folder in top_folders:
            folder_id = folder.get("id", "")
            folder_name = folder.get("name", "General")
            if folder.get("contentType", 1) == 1:
                tasks.append(fetch_folder_content(batch_id, folder_id, token, folder_name, folder_name))
            else:
                item_url = folder.get("url", "")
                if item_url:
                    all_items.append({
                        "id": str(folder_id), "name": folder_name, "url": item_url,
                        "description": folder.get("description", ""),
                        "type": classify_url(item_url, folder_name),
                        "subjectName": "General", "topicName": "General",
                        "contentType": folder.get("contentType", 2),
                        "timestamp": folder.get("createdAt", ""),
                    })
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_items.extend(res)
        LOGGER.info(f"Total items: {len(all_items)}")
    except Exception as e:
        LOGGER.error(f"collect_data error: {e}")
    return all_items
