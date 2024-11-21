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
        from utils.background_removal import ReplicateBackgroundRemoval

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
        return "https://cdn.metisai.com/images/engines/{}.png".format(self.value)

    @property
    def price(self):
        return 0.1


class BackgroundRemovalCreateSchema(BaseModel):
    engine: BackgroundRemovalEngines = BackgroundRemovalEngines.cjwbw
    image: str


class BackgroundRemovalSchema(TaskMixin, OwnedEntitySchema):
    engine: BackgroundRemovalEngines = BackgroundRemovalEngines.cjwbw
    image: str | None = None
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
