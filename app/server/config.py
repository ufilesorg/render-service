"""FastAPI server configuration."""

import dataclasses
import os
from pathlib import Path

import dotenv
from fastapi_mongo_base.core.config import Settings as BaseSettings

dotenv.load_dotenv()


@dataclasses.dataclass
class Settings(BaseSettings):
    """Server config settings."""

    base_dir: Path = Path(__file__).resolve().parent.parent
    base_path: str = "/v1/apps/render"
    update_time: int = 10

    UFILES_API_KEY: str = os.getenv("UFILES_API_KEY")
    UFILES_BASE_URL: str = os.getenv("UFILES_URL")
    USSO_BASE_URL: str = os.getenv("USSO_URL")

    MWJ_RENDER_URL: str = os.getenv("MWJ_RENDER_URL", "https://render.pixiee.io/render")
    RENDER_API_KEY: str = os.getenv("RENDER_API_KEY")
