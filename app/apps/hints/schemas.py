from enum import Enum

from pydantic import BaseModel


class InputType(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"
    select = "select"
    multi_select = "multi_select"
    date = "date"
    checkbox = "checkbox"
    radio = "radio"


class Choice(BaseModel):
    value: str
    label: dict[str, str]
    children: list["Choice"] | None = None
    image: str | None = None


class PromptBuilderItem(BaseModel):
    topic: str
    options: list[Choice]
    ai_attr: list[Choice] | None = None
    limited: bool = False
    type: InputType = InputType.text
