import json
import logging
import os
import replicate
import google.generativeai as genai
import google.generativeai.vision_models as genaiaa
import aiohttp
import langdetect
import singleton

from datetime import datetime
from typing import Literal, Any
from metisai.async_metis import AsyncMetisBot
from pydantic import BaseModel, field_validator
from utils.texttools import backtick_formatter
from server.config import Settings
from metisai.metistypes import TaskResult
from apps.imagination.schemas import (
    ImaginationStatus,
    ImaginationEngines,
    ImagineCreateSchema,
)
from apps.imagination.models import Engine, EnginesDetails

metis_client = AsyncMetisBot(
    api_key=os.getenv("METIS_API_KEY"), bot_id=os.getenv("METIS_BOT_ID")
)


async def metis_chat(messages: dict, **kwargs):
    user_id = kwargs.get("user_id")
    session = await metis_client.create_session(user_id)
    prompt = "\n\n".join([message["content"] for message in messages])
    response = await metis_client.send_message(session, prompt)
    await metis_client.delete_session(session)
    resp_text = backtick_formatter(response.content)
    return resp_text


async def answer_messages(messages: dict, **kwargs):
    # resp_text = await openai_chat(messages, **kwargs)
    resp_text = await metis_chat(messages, **kwargs)
    try:
        return json.loads(resp_text)
    except json.JSONDecodeError:
        return {"answer": resp_text}


async def translate(query: str, to: str = "en"):
    try:
        lang = langdetect.detect(query)
    except:
        lang = "en"

    if lang == to:
        return query

    languages = {
        "en": "English",
        "fa": "Persian",
    }
    if not languages.get(to):
        to = "en"
    prompt = "\n".join(
        [
            f"You are perfect translator to {to} language.",
            f"Just reply the answer in json format like",
            f'`{{"answer": "Your translated text"}}`',
            f"",
            f"Translate the following text to '{to}': \"{query}\".",
        ]
    )

    messages = [{"content": prompt}]
    response = await answer_messages(messages)
    logging.info(f"process_task {query} {response}")
    return response["answer"]

    session = await metis_client.create_session()
    response = await metis_client.send_message(session, prompt)
    await metis_client.delete_session(session)
    resp_text = backtick_formatter(response.content)
    return resp_text


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


class Midjourney(Engine, metaclass=singleton.Singleton):
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


class ReplicateDetails(EnginesDetails):
    input: dict[str, Any]
    model: Literal[
        "ideogram-ai/ideogram-v2-turbo",
        "black-forest-labs/flux-schnell",
        "black-forest-labs/flux-1.1-pro",
        "stability-ai/stable-diffusion-3",
        "cjwbw/rembg",
        "lucataco/remove-bg",
        "pollinations/modnet",
    ] = "ideogram-ai/ideogram-v2-turbo"


class Replicate(Engine):
    def __init__(self, item, name) -> None:
        super().__init__(item)
        self.application_name = {
            "ideogram": "ideogram-ai/ideogram-v2-turbo",
            "flux_schnell": "black-forest-labs/flux-schnell",
            "flux_1.1": "black-forest-labs/flux-1.1-pro",
            "stability": "stability-ai/stable-diffusion-3",
        }[name]

    async def result(self, **kwargs) -> ReplicateDetails:
        id = self._get_data("id")
        prediction = await replicate.predictions.async_get(id)
        return await self._result_to_details(prediction)

    async def _request(self, **kwargs) -> ReplicateDetails:
        prediction = replicate.predictions.create(
            model=self.application_name,
            input={"prompt": self.item.prompt, "aspect_ratio": self.item.aspect_ratio},
            webhook=self.item.webhook_url,
            webhook_events_filter=["completed"],
        )
        return await self._result_to_details(prediction)

    def validate(self, data: ImagineCreateSchema):
        aspect_ratios = {
            "ideogram-ai/ideogram-v2-turbo": {
                "1:1",
                "16:9",
                "9:16",
                "4:3",
                "3:4",
                "3:2",
                "2:3",
                "16:10",
                "10:16",
                "3:1",
                "1:3",
            },
            "black-forest-labs/flux-schnell": {
                "1:1",
                "16:9",
                "21:9",
                "3:2",
                "2:3",
                "4:5",
                "5:4",
                "3:4",
                "4:3",
                "9:16",
                "9:21",
            },
            "black-forest-labs/flux-1.1-pro": {
                "1:1",
                "16:9",
                "2:3",
                "3:2",
                "4:5",
                "5:4",
                "9:16",
                "3:4",
                "4:3",
            },
            "stability-ai/stable-diffusion-3": {
                "1:1",
                "16:9",
                "21:9",
                "3:2",
                "2:3",
                "4:5",
                "5:4",
                "9:16",
                "9:21",
            },
        }[self.application_name]

        aspect_ratio_valid = data.aspect_ratio in aspect_ratios
        message = (
            f"aspect_ratio must be one of them {aspect_ratios}"
            if not aspect_ratio_valid
            else None
        )
        return aspect_ratio_valid, message

    def _status(
        self,
        status: Literal["starting", "processing", "succeeded", "failed", "canceled"],
    ):
        return {
            "starting": ImaginationStatus.init,
            "canceled": ImaginationStatus.cancelled,
            "processing": ImaginationStatus.processing,
            "succeeded": ImaginationStatus.completed,
            "failed": ImaginationStatus.error,
        }.get(status, ImaginationStatus.error)

    async def _result_to_details(self, prediction: replicate.prediction.Prediction):
        prediction_data = prediction.__dict__.copy()
        prediction_data.pop("status", None)
        prediction_data.pop("model", None)
        return ReplicateDetails(
            **prediction_data,
            prompt=prediction.input["prompt"],
            status=self._status(prediction.status),
            model=self.application_name,
            result={"uri": prediction.output[0]} if prediction.output else None,
            percentage=100,
        )


class DalleDetails(EnginesDetails):
    session_id: str


class Dalle(Engine):
    def __init__(self, item) -> None:
        super().__init__(item)
        if item:
            self.client = AsyncMetisBot(
                api_key=Settings.METIS_API_KEY,
                bot_id=ImaginationEngines.dalle.metis_bot_id,
            )

    async def result(self, **kwargs) -> DalleDetails:
        id = self._get_data("id")
        session_id = self._get_data("session_id")
        task = await self.client.retrieve_async_task(session_id, id)
        return await self._result_to_details(task, task_id=id, session_id=session_id)

    async def _request(self, **kwargs) -> DalleDetails:
        self.item.prompt += f", in a {self.item.aspect_ratio} aspect ratio"
        session = await self.client.create_session()
        res = await self.client.send_message_async(
            session, f"/imagine {self.item.prompt}"
        )
        task = await self.client.retrieve_async_task(session, res)
        return await self._result_to_details(
            task, task_id=res.taskId, session_id=session.id
        )

    def _status(self, status: Literal["RUNNING", "FINISHED", "FAILED"]):
        return {
            "RUNNING": ImaginationStatus.processing,
            "FINISHED": ImaginationStatus.completed,
            "FAILED": ImaginationStatus.error,
        }.get(status, ImaginationStatus.error)

    def validate(self, data: ImagineCreateSchema):
        aspect_ratio_valid = data.aspect_ratio in {
            "16:9",
            "9:16",
            "1:1",
        }
        message = (
            "aspect_ratio must be one of them 16:9 or 9:16 or 1:1"
            if not aspect_ratio_valid
            else None
        )
        return aspect_ratio_valid, message

    async def _result_to_details(self, task: TaskResult, **kwargs):
        task_data = task.__dict__.copy()
        session_id = kwargs.get("session_id")
        task_id = kwargs.get("task_id")
        status = self._status(task.status)
        task_data.pop("status", None)
        return DalleDetails(
            **task_data,
            id=task_id,
            session_id=session_id,
            status=status,
            prompt=self.item.prompt,
            result=(
                {"uri": task.message.attachments[0].content} if task.message else None
            ),
        )


class ImagenDetails(EnginesDetails):
    session_id: str


class Imagen(Engine):
    def __init__(self, item) -> None:
        super().__init__(item)
        if item:
            genai.configure(api_key=Settings.imagen_apikey)
            self.imagen = genaiaa.ImageGenerationModel("imagen-3.0-generate-001")

    async def result(self, **kwargs) -> ImagenDetails:
        id = self._get_data("id")
        session_id = self._get_data("session_id")
        task = await self.client.retrieve_async_task(session_id, id)
        return await self._result_to_details(task, task_id=id, session_id=session_id)

    async def _request(self, **kwargs) -> ImagenDetails:
        result = self.imagen.generate_images(
            prompt=self.item.prompt,
            number_of_images=1,
            person_generation="allow_adult",
            aspect_ratio=self.item.aspect_ratio,
            # safety_filter_level="block_only_high",
            # negative_prompt="Outside",
        )
        return await self._result_to_details(
            task, task_id=res.taskId, session_id=session.id
        )

    def _status(self, status: Literal["RUNNING", "FINISHED", "FAILED"]):
        return {
            "RUNNING": ImaginationStatus.processing,
            "FINISHED": ImaginationStatus.completed,
            "FAILED": ImaginationStatus.error,
        }.get(status, ImaginationStatus.error)

    def validate(self, data: ImagineCreateSchema):
        aspect_ratio_valid = data.aspect_ratio in {
            "1:1",
            "3:4",
            "4:3",
            "9:16",
            "16:9",
        }
        message = (
            "aspect_ratio must be one of them 1:1, 3:4, 4:3, 9:16 and 16:9"
            if not aspect_ratio_valid
            else None
        )
        return aspect_ratio_valid, message

    async def _result_to_details(self, task: TaskResult, **kwargs):
        task_data = task.__dict__.copy()
        session_id = kwargs.get("session_id")
        task_id = kwargs.get("task_id")
        status = self._status(task.status)
        task_data.pop("status", None)
        return ImagenDetails(
            **task_data,
            id=task_id,
            session_id=session_id,
            status=status,
            prompt=self.item.prompt,
            result=(
                {"uri": task.message.attachments[0].content} if task.message else None
            ),
        )
