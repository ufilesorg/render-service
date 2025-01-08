import uuid

from fastapi_mongo_base.models import OwnedEntity

from .schemas import RenderGroupSchema, RenderSchema


class Render(RenderSchema, OwnedEntity):
    class Settings:
        indexes = OwnedEntity.Settings.indexes


class RenderGroup(RenderGroupSchema, OwnedEntity):
    render_ids: list[uuid.UUID] = []

    class Settings:
        indexes = OwnedEntity.Settings.indexes
