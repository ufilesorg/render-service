import json
import os
from datetime import datetime
from typing import Any, Literal

import aiohttp
from pydantic import BaseModel

from .engine import Engine, EnginesDetails
from .schemas import ImaginationStatus


class MidjourneyDetails(EnginesDetails, BaseModel):
    deleted: bool = False
    active: bool = True
    createdBy: str | None = None
    user: str | None = None
    command: str
    callback_url: str | None = None
    free: bool = False
    temp_uri: list[str] = []
    createdAt: datetime
    updatedAt: datetime
    turn: int = 0
    account: str | None = None
    uri: str | None = None

    error: dict | str | None = None
    message: str | None = None
    sender_data: dict | None = None


class Midjourney(Engine):
    def __init__(self, item) -> None:
        super().__init__(item)
        self.api_url = "https://mid.aision.io/task"
        self.token = os.getenv("MIDAPI_TOKEN")

        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    async def result(self, **kwargs) -> MidjourneyDetails:
        id = self._get_data("id")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/{id}", headers=self.headers
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return await self._result_to_details(result)

    async def _request(self, **kwargs) -> MidjourneyDetails:
        payload = json.dumps(
            {
                "prompt": self.item.prompt,
                "command": "imagine",
                "callback": kwargs.get("callback", None),
            }
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.api_url, headers=self.headers, data=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return await self._result_to_details(result)

    def _status(
        self,
        status: Literal[
            "initialized", "queue", "waiting", "running", "completed", "error"
        ] = "initialized",
    ):
        return {
            "initialized": ImaginationStatus.init,
            "queue": ImaginationStatus.queue,
            "waiting": ImaginationStatus.waiting,
            "running": ImaginationStatus.processing,
            "completed": ImaginationStatus.completed,
            "error": ImaginationStatus.error,
        }.get(status, ImaginationStatus.error)

    async def _result_to_details(self, result: dict[str, Any], **kwargs):
        status = self._status(result["status"])
        result.pop("status", None)
        return MidjourneyDetails(
            **result,
            id=result.get("uuid"),
            status=status,
            result={"uri": result["uri"]} if result["uri"] else None,
        )
