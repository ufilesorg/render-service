from enum import Enum
from typing import Any, Literal

from fastapi_mongo_base.schemas import OwnedEntitySchema
from fastapi_mongo_base.tasks import TaskMixin, TaskStatusEnum
from pydantic import BaseModel, field_validator, model_validator


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
    flux = "flux"
    dalle = "dalle"
    leonardo = "leonardo"

    @property
    def metis_bot_id(self):
        return {
            ImaginationEngines.midjourney: "1fff8298-4f56-4912-89b4-3529106c5a0a",
            ImaginationEngines.flux: "68ec6038-6701-4f9b-a3f5-0c674b106f0e",
            ImaginationEngines.dalle: "59631f67-3199-4e47-af7f-18eb44f69ea2",
            ImaginationEngines.leonardo: "4b69d78d-e454-4f4b-93ed-427b46368977",
        }[self]

    def get_class(self, imagination: Any):
        from utils.ai import Midjourney, Replicate, Dalle
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
        return "https://cdn.metisai.com/images/engines/{}.png".format(self.value)

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


class ImagineCreateSchema(BaseModel):
    prompt: str | None = None
    engine: ImaginationEngines = ImaginationEngines.midjourney
    aspect_ratio: str | None = '1:1'
    delineation: str | None = None
    context: list[dict[str, Any]] | None = None
    enhance_prompt: bool = False
    number: int = 1

    @model_validator(mode="after")
    def validate_aspect_ratio(cls, values):
        aspect_ratio = values.aspect_ratio
        engine = values.engine
        validated, message = engine.get_class(None).validate_ratio(aspect_ratio)
        
        if not validated:
            raise ValueError(f"Aspect ratio: {message}")
        return values



class ImagineResponse(BaseModel):
    url: str
    width: int
    height: int


class ImagineSchema(TaskMixin, OwnedEntitySchema):
    prompt: str | None = None
    delineation: str | None = None
    aspect_ratio: str | None = None
    context: list[dict[str, Any]] | None = None
    engine: ImaginationEngines = ImaginationEngines.midjourney
    mode: Literal["imagine"] = "imagine"
    status: ImaginationStatus = ImaginationStatus.draft
    results: list[ImagineResponse] | None = None


class ImagineWebhookData(BaseModel):
    prompt: str
    status: ImaginationStatus
    percentage: int
    result: dict[str, Any] | None = None
    error: Any | None = None

    @field_validator("percentage", mode="before")
    def validate_percentage(cls, value):
        if value is None:
            return -1
        if isinstance(value, str):
            return int(value.replace("%", ""))
        if value < -1:
            return -1
        if value > 100:
            return 100
        return value
