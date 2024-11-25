from enum import Enum
from typing import Any

from fastapi_mongo_base.tasks import TaskStatusEnum
from pydantic import BaseModel
from server.config import Settings


class ImaginationStatus(str, Enum):
    none = "none"
    draft = "draft"
    init = "init"
    queue = "queue"
    waiting = "waiting"
    running = "running"
    processing = "processing"
    done = "done"
    completed = "completed"
    error = "error"
    cancelled = "cancelled"

    @classmethod
    def from_midjourney(cls, status: str):
        return {
            "initialized": ImaginationStatus.init,
            "queue": ImaginationStatus.queue,
            "waiting": ImaginationStatus.waiting,
            "running": ImaginationStatus.processing,
            "completed": ImaginationStatus.completed,
            "error": ImaginationStatus.error,
        }.get(status, ImaginationStatus.error)

    @property
    def task_status(self):
        return {
            ImaginationStatus.none: TaskStatusEnum.none,
            ImaginationStatus.draft: TaskStatusEnum.draft,
            ImaginationStatus.init: TaskStatusEnum.init,
            ImaginationStatus.queue: TaskStatusEnum.processing,
            ImaginationStatus.waiting: TaskStatusEnum.processing,
            ImaginationStatus.running: TaskStatusEnum.processing,
            ImaginationStatus.processing: TaskStatusEnum.processing,
            ImaginationStatus.done: TaskStatusEnum.completed,
            ImaginationStatus.completed: TaskStatusEnum.completed,
            ImaginationStatus.error: TaskStatusEnum.error,
            ImaginationStatus.cancelled: TaskStatusEnum.completed,
        }[self]

    @property
    def is_done(self):
        return self in (
            ImaginationStatus.done,
            ImaginationStatus.completed,
            ImaginationStatus.error,
            ImaginationStatus.cancelled,
        )


class ImaginationEngines(str, Enum):
    midjourney = "midjourney"
    ideogram = "ideogram"
    flux_schnell = "flux_schnell"
    stability = "stability"
    flux_1_1 = "flux_1.1"
    dalle = "dalle"
    # flux = "flux"
    # leonardo = "leonardo"

    @property
    def metis_bot_id(self):
        return {
            # ImaginationEngines.midjourney: "1fff8298-4f56-4912-89b4-3529106c5a0a",
            # ImaginationEngines.flux: "68ec6038-6701-4f9b-a3f5-0c674b106f0e",
            ImaginationEngines.dalle: Settings.METIS_DALLE_BOT_ID,
            # ImaginationEngines.leonardo: "4b69d78d-e454-4f4b-93ed-427b46368977",
        }[self]

    def get_class(self, imagination: Any):
        from .dalle import Dalle
        from .midjourney import Midjourney
        from .replicate_engine import Replicate

        return {
            ImaginationEngines.dalle: lambda: Dalle(imagination),
            ImaginationEngines.midjourney: lambda: Midjourney(imagination),
            ImaginationEngines.ideogram: lambda: Replicate(imagination, self.value),
            ImaginationEngines.flux_schnell: lambda: Replicate(imagination, self.value),
            ImaginationEngines.stability: lambda: Replicate(imagination, self.value),
            ImaginationEngines.flux_1_1: lambda: Replicate(imagination, self.value),
        }[self]()

    @property
    def thumbnail_url(self):
        return {
            ImaginationEngines.dalle: "https://media.pixiee.io/v1/f/41af8b03-b4df-4b2f-ba52-ea638d10b5f3/dalle-icon.png",
            ImaginationEngines.midjourney: "https://media.pixiee.io/v1/f/4a0980aa-8d97-4493-bdb1-fb3d67d891e3/midjourney-icon.png",
            ImaginationEngines.ideogram: "https://media.pixiee.io/v1/f/19d4df43-ea1e-4562-a8e1-8ee301bd0a88/ideogram-icon.png",
            ImaginationEngines.flux_schnell: "https://media.pixiee.io/v1/f/cf21c500-6e84-4915-a5d1-19b8f325a382/flux-icon.png",
            ImaginationEngines.stability: "https://media.pixiee.io/v1/f/6d0a2e82-7667-46ec-af33-0e557f16e356/stability-icon.png",
            ImaginationEngines.flux_1_1: "https://media.pixiee.io/v1/f/cf21c500-6e84-4915-a5d1-19b8f325a382/flux-icon.png",
        }[self]

    @property
    def price(self):
        return 0.1


class ImaginationEnginesSchema(BaseModel):
    engine: ImaginationEngines = ImaginationEngines.midjourney
    thumbnail_url: str
    price: float

    @classmethod
    def from_model(cls, model: ImaginationEngines):
        return cls(engine=model, thumbnail_url=model.thumbnail_url, price=model.price)
