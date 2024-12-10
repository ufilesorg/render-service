from enum import Enum
from typing import Any

from fastapi_mongo_base.schemas import OwnedEntitySchema
from fastapi_mongo_base.tasks import TaskMixin
from pydantic import BaseModel, field_validator

from apps.imagination.schemas import ImaginationStatus, ImagineResponse


class BackgroundRemovalEngines(str, Enum):
    cjwbw = "cjwbw"
    lucataco = "lucataco"
    pollinations = "pollinations"

    def get_class(self, background_removal: Any):
        from .ai import ReplicateBackgroundRemoval

        return {
            BackgroundRemovalEngines.cjwbw: lambda: ReplicateBackgroundRemoval(
                background_removal, self.value
            ),
            BackgroundRemovalEngines.lucataco: lambda: ReplicateBackgroundRemoval(
                background_removal, self.value
            ),
            BackgroundRemovalEngines.pollinations: lambda: ReplicateBackgroundRemoval(
                background_removal, self.value
            ),
        }[self]()

    @property
    def thumbnail_url(self):
        return {
            BackgroundRemovalEngines.cjwbw: "https://media.pixiee.io/v1/f/c3044ffe-8fb5-410c-b5e2-3939a9140266/cjwbw-icon.png",
            BackgroundRemovalEngines.lucataco: "https://media.pixiee.io/v1/f/2a6a6b6d-45ac-486b-861d-e00477d52ac4/lucataco-icon.png",
            BackgroundRemovalEngines.pollinations: "https://media.pixiee.io/v1/f/aa6f73c6-ab73-48bf-8b96-1a83aa238a1c/pollinations-icon.png",
        }[self]

    @property
    def price(self):
        return 0.1


class BackgroundRemovalEnginesSchema(BaseModel):
    engine: BackgroundRemovalEngines = BackgroundRemovalEngines.cjwbw
    thumbnail_url: str
    price: float

    @classmethod
    def from_model(cls, model: BackgroundRemovalEngines):
        return cls(engine=model, thumbnail_url=model.thumbnail_url, price=model.price)


class BackgroundRemovalCreateSchema(BaseModel):
    # engine: BackgroundRemovalEngines = BackgroundRemovalEngines.cjwbw
    image_url: str


class BackgroundRemovalSchema(TaskMixin, OwnedEntitySchema):
    engine: BackgroundRemovalEngines = BackgroundRemovalEngines.cjwbw
    image_url: str | None = None
    status: ImaginationStatus = ImaginationStatus.draft
    result: ImagineResponse | None = None


class BackgroundRemovalWebhookData(BaseModel):
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
