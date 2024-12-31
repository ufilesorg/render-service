from fastapi_mongo_base.models import OwnedEntity

from .schemas import RenderSchema


class Render(RenderSchema, OwnedEntity):
    class Settings:
        indexes = OwnedEntity.Settings.indexes
