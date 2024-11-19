import asyncio
import logging

from fastapi_mongo_base.models import OwnedEntity
from pydantic import BaseModel, field_validator
from server.config import Settings

from .schemas import ImagineSchema, ImaginationStatus, ImagineCreateSchema


class Imagination(ImagineSchema, OwnedEntity):
    class Settings:
        indexes = OwnedEntity.Settings.indexes

    @property
    def item_url(self):
        # TODO: Change to use the business url
        return f"https://{Settings.root_url}/v1/apps/imagine/imagination/{self.uid}"

    @property
    def webhook_url(self):
        return f"{self.item_url}/webhook"

    async def start_processing(self):
        from .services import imagine_request

        await imagine_request(self)

    async def retry(self, message: str, max_retries: int = 5):
        self.meta_data = self.meta_data or {}
        retry_count = self.meta_data.get("retry_count", 0)

        if retry_count < max_retries:
            self.meta_data["retry_count"] = retry_count + 1
            await self.save_report(
                f"Retry {self.uid} {self.meta_data.get('retry_count')}", emit=False
            )
            await self.save_and_emit()
            asyncio.create_task(self.start_processing())
            logging.info(f"Retry {retry_count} {self.uid}")
            return retry_count + 1

        await self.fail(message)
        return -1

    async def fail(self, message: str):
        self.task_status = "error"
        self.status = "error"
        await self.save_report(f"Image failed after retries, {message}", emit=False)
        await self.save_and_emit()

    @classmethod
    async def get_item(cls, uid, user_id, *args, **kwargs) -> "Imagination":
        # if user_id == None:
        #     raise ValueError("user_id is required")
        return await super(OwnedEntity, cls).get_item(
            uid, user_id=user_id, *args, **kwargs
        )


# Required data
class EnginesDetails(BaseModel):
    id: str
    prompt: str
    status: ImaginationStatus
    percentage: int | None = None
    result: dict | None = None

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


class Engine:
    def __init__(self, item) -> None:
        self.item = item

    # Get Result from service(client / API)
    async def result(self, **kwargs):
        pass

    # Validate schema
    async def validate(self, data: ImagineCreateSchema) -> tuple[bool, str | None]:
        pass

    # Send request to service(client / API)
    async def _request(self, **kwargs) -> EnginesDetails:
        pass

    # Get property from item meta_data
    # item.meta_data: It is a response sent from the service
    def _get_data(self, name: str, **kwargs):
        value = (self.item.meta_data or {}).get(name, None)
        if value is None:
            raise ValueError(f"Missing value {name}")
        return value

    # Get current request service(Convert service status to ImaginationStatus)
    def _status(self, status: str) -> ImaginationStatus:
        pass

    async def imagine(self, **kwargs):
        response = await self._request(**kwargs)
        return response

    # Convert service response to EnginesDetails
    async def _result_to_details(self, res) -> EnginesDetails:
        pass
