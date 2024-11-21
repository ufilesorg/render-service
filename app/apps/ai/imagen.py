from typing import Literal

import google.generativeai as genai
import google.generativeai.vision_models as genaiaa
from metisai.metistypes import TaskResult

from server.config import Settings

from .engine import Engine, EnginesDetails
from .schemas import ImaginationStatus


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

    def validate(self, data):
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
