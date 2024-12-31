import uuid

from fastapi_mongo_base.models import BaseEntity
from pymongo import ASCENDING, IndexModel

from .schemas import TemplateSchema


class Template(TemplateSchema, BaseEntity):
    creator_id: uuid.UUID | None = None

    class Settings:
        indexes = BaseEntity.Settings.indexes + [
            IndexModel([("name", ASCENDING)], unique=True),
        ]

    @classmethod
    async def get_by_name(cls, name: str) -> "Template":
        return await cls.find_one({"name": name})

    @classmethod
    async def get_by_ad_type(cls, ad_type: str) -> "Template":
        return await cls.find_one({"ad_type": ad_type})
