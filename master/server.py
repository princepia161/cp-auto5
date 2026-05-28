import asyncio
import httpx


class HttpxClient:
    def __init__(self, verify_ssl=True):
        self.verify_ssl = verify_ssl
        self._client = None

    async def _get_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(verify=self.verify_ssl, timeout=60.0)
        return self._client

    async def get(self, url, params=None, headers=None, cookies=None, retry=(3, 2, 500), attempt=0):
        try:
            max_retries, backoff, retry_code = retry
            client = await self._get_client()
            response = await client.get(url, params=params, headers=headers, cookies=cookies)
            if retry_code and response.status_code == retry_code and attempt < max_retries:
                await asyncio.sleep(backoff)
                return await self.get(url, params=params, headers=headers, cookies=cookies, retry=retry, attempt=attempt + 1)
            return response
        except Exception as e:
            max_retries = retry[0] if isinstance(retry, tuple) else retry
            if attempt < max_retries:
                await asyncio.sleep(2)
                return await self.get(url, params=params, headers=headers, cookies=cookies, retry=retry, attempt=attempt + 1)
            raise e

    async def post(self, url, json=None, data=None, params=None, headers=None, cookies=None, retry=(3, 2, 500), attempt=0):
        try:
            max_retries, backoff, retry_code = retry
            client = await self._get_client()
            response = await client.post(url, json=json, data=data, params=params, headers=headers, cookies=cookies)
            if retry_code and response.status_code == retry_code and attempt < max_retries:
                await asyncio.sleep(backoff)
                return await self.post(url, json=json, data=data, params=params, headers=headers, cookies=cookies, retry=retry, attempt=attempt + 1)
            return response
        except Exception as e:
            max_retries = retry[0] if isinstance(retry, tuple) else retry
            if attempt < max_retries:
                await asyncio.sleep(2)
                return await self.post(url, json=json, data=data, params=params, headers=headers, cookies=cookies, retry=retry, attempt=attempt + 1)
            raise e

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


scraper = HttpxClient(verify_ssl=False)
