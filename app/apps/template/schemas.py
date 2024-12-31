from enum import Enum
from typing import Literal

from fastapi_mongo_base.schemas import BaseEntitySchema
from pydantic import BaseModel


class FieldType(str, Enum):
    text = "text"
    number = "number"
    email = "email"
    password = "password"
    textarea = "textarea"
    select = "select"
    radio = "radio"
    checkbox = "checkbox"
    date = "date"
    time = "time"
    datetime = "datetime"
    file = "file"
    image = "image"
    color = "color"
    range = "range"
    url = "url"
    tel = "tel"
    hidden = "hidden"


class FieldSchema(BaseEntitySchema):
    name: str
    label: str
    placeholder: str | None = None
    type: FieldType = FieldType.text
    values: list[str] | None = None
    validation: str | None = None  # regex
    page: Literal["content", "image", "brand"] = "content"


class TemplateCreateSchema(BaseModel):
    meta_data: dict | None = None
    model: Literal["mwj", "psd"] = "mwj"

    name: str
    description: str | None = None

    url: str
    thumbnail: str
    design: str | None = None
    width: int = 600
    height: int = 400

    tags: list[str] = []
    category: str = "general"

    license: Literal["free", "paid"] = "free"


class TemplateSchema(TemplateCreateSchema, BaseEntitySchema):
    preview_template_name: str | None = None
    render_template_name: str | None = None
    render_template_name: str | None = None
    form_fields: list[FieldSchema] = []
    assist_data: dict | None = None
