from fastapi_mongo_base.schemas import OwnedEntitySchema
from pydantic import BaseModel


class RenderCreateSchema(BaseModel):
    template_name: str
    texts: dict[str, str] | list[str] = {}
    fonts: list[str] | str = ["Vazirmatn"]
    images: dict[str, str] | list[str] = {}
    logo: str | None = None
    colors: list[str] = []
    meta_data: dict | None = None


class RenderResult(BaseModel):
    url: str
    width: int
    height: int


class RenderSchema(RenderCreateSchema, OwnedEntitySchema):
    results: list[RenderResult] = []


class RenderGroupCreateSchema(BaseModel):
    group_name: str
    texts: dict[str, str] | list[str] = {}
    fonts: list[str] | str = ["Vazirmatn"]
    images: dict[str, str] | list[str] = {}
    logo: str | None = None
    colors: list[str] = []
    meta_data: dict | None = None


class RenderGroupSchema(RenderGroupCreateSchema, OwnedEntitySchema):
    results: list[RenderResult] = []
