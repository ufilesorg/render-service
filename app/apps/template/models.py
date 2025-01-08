import asyncio
import uuid

from fastapi_mongo_base.models import BaseEntity
from pymongo import ASCENDING, IndexModel

from .schemas import TemplateGroupSchema, TemplateSchema


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


class TemplateGroup(TemplateGroupSchema, BaseEntity):
    class Settings:
        indexes = BaseEntity.Settings.indexes + [
            IndexModel([("name", ASCENDING)], unique=True),
        ]

    @classmethod
    async def get_by_name(cls, name: str) -> "TemplateGroup":
        return await cls.find_one({"name": name})

    async def get_templates(self) -> list[Template]:
        return await asyncio.gather(
            *[Template.get_by_name(name) for name in self.template_names]
        )

    async def get_fields(self) -> list[str]:
        templates = await self.get_templates()
        return list({field for template in templates for field in template.fields})
