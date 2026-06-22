import aiohttp
from typing import Any

class NotionResponse:
    """
    Класс-обертка для HTTP-ответа от Notion API.
    Позволяет безопасно считывать статус и JSON-данные.
    """
    def __init__(self, status: int, data: Any, text_content: str = ""):
        self.status = status
        self._data = data
        self._text_content = text_content

    async def json(self) -> Any:
        return self._data

    async def text(self) -> str:
        return self._text_content


class NotionClient:
    """
    Клиент для работы с Notion API.
    Инкапсулирует логику HTTP-запросов и заголовков.
    """
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2025-09-03"
        }
        self._base_url = "https://api.notion.com"

    async def get(self, path: str, **kwargs: Any) -> NotionResponse:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> NotionResponse:
        return await self._request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> NotionResponse:
        return await self._request("PATCH", path, **kwargs)

    async def _request(self, method: str, path: str, **kwargs: Any) -> NotionResponse:
        url = f"{self._base_url}{path}" if not path.startswith("http") else path
        headers = {
            "Content-Type": "application/json",
            **self._headers,
            **kwargs.pop("headers", {})
        }
        
        session = kwargs.pop("session", None)
        if session:
            async with session.request(method, url, headers=headers, **kwargs) as resp:
                try:
                    data = await resp.json()
                except Exception:
                    data = {}
                try:
                    text_content = await resp.text()
                except Exception:
                    text_content = ""
                return NotionResponse(resp.status, data, text_content)
        else:
            async with aiohttp.ClientSession() as sess:
                async with sess.request(method, url, headers=headers, **kwargs) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    try:
                        text_content = await resp.text()
                    except Exception:
                        text_content = ""
                    return NotionResponse(resp.status, data, text_content)
