from enum import Enum
from typing import Literal

from fastapi_mongo_base.schemas import BaseEntitySchema
from pydantic import BaseModel, model_validator


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


class FieldSchema(BaseModel):
    name: str
    label: str
    label_fa: str | None = None
    placeholder: str | None = None
    type: FieldType = FieldType.text
    values: list[str] | None = None
    validation: str | None = None  # regex
    page: Literal["content", "image", "brand"] = "content"
    default: str | None = None

    @model_validator(mode="before")
    def validate_label(cls, values: dict):
        if not values.get("label"):
            values["label"] = values.get("name")
        return values

    def __hash__(self):
        return hash(self.name)


class TemplateCreateSchema(BaseModel):
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

    colors: list[str] = []
    fonts: list[str] = []

    fields: list[FieldSchema] = []

    meta_data: dict | None = None


class TemplateSchema(TemplateCreateSchema, BaseEntitySchema):
    preview_template_name: str | None = None
    render_template_name: str | None = None
    render_template_name: str | None = None
    fields: list[FieldSchema] = []
    assist_data: dict | None = None


class TemplateGroupCreateSchema(BaseModel):
    name: str
    thumbnail: str
    template_names: list[str] = []
    description: str | None = None
    category: str = "general"

    meta_data: dict | None = None


class TemplateGroupSchema(TemplateGroupCreateSchema, BaseEntitySchema):
    # fields: list[FieldSchema] = []
    pass


class TemplateGroupDetailSchema(TemplateGroupSchema):
    fields: list[FieldSchema] = []
