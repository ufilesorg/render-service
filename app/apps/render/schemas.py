from fastapi_mongo_base.schemas import OwnedEntitySchema
from pydantic import BaseModel, model_validator


class RenderCreateSchema(BaseModel):
    template_name: str
    texts: dict[str, str] = {}
    fonts: list[str] | str = "Vazirmatn"
    images: dict[str, str] = {}
    logo: str | None = None
    colors: list[str] = []
    meta_data: dict | None = None

    @model_validator(mode="after")
    def validate_fonts(cls, item: "RenderCreateSchema"):
        if isinstance(item.fonts, str):
            item.fonts = [item.fonts] * len(item.texts)
        return item


class RenderResult(BaseModel):
    url: str
    width: int
    height: int


class RenderSchema(RenderCreateSchema, OwnedEntitySchema):
    results: list[RenderResult] = []
