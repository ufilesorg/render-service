import asyncio
import json
import logging
import uuid

import httpx
import ufiles
from apps.template.models import Template
import jinja2
from PIL import Image
from server.config import Settings
from utils import imagetools

from .models import Render
from .schemas import RenderResult


async def upload_image(
    image: Image.Image,
    image_name: str,
    user_id: uuid.UUID,
    file_upload_dir: str = "renders",
):
    ufiles_client = ufiles.AsyncUFiles(
        ufiles_base_url=Settings.UFILES_BASE_URL,
        usso_base_url=Settings.USSO_BASE_URL,
        api_key=Settings.UFILES_API_KEY,
    )
    image_bytes = imagetools.convert_to_jpg_bytes(image)
    base_name = (
        ".".join(image_name.split(".")[:-1]) if "." in image_name else image_name
    )
    image_bytes.name = f"{base_name}.jpg"
    return await ufiles_client.upload_bytes(
        image_bytes,
        filename=f"{file_upload_dir}/{image_bytes.name}",
        public_permission=json.dumps({"permission": ufiles.PermissionEnum.READ}),
        user_id=str(user_id),
        # meta_data={},
    )


async def render_mwj(mwj: dict) -> Image.Image:
    # logging.info(f"Rendering mwj: {mwj}")
    with open("logs/mwj.json", "w") as f:
        json.dump(mwj, f, indent=4, ensure_ascii=False)
    
    async with httpx.AsyncClient() as client:
        r = await client.post(
            Settings.MWJ_RENDER_URL,
            json=mwj,
            headers={"x-api-key": Settings.RENDER_API_KEY},
        )
        r.raise_for_status()

    base64_str = r.json().get("result")
    logging.info(base64_str)
    return imagetools.base64_to_image(base64_str)


async def fill_render_template_data(template_data: str, data: dict) -> dict:
    jinja_template = jinja2.Template(template_data)
    text = jinja_template.render(**data)
    result = json.loads(text)
    return result


async def get_template_data(template_name: str) -> dict:
    template = await Template.get_by_name(template_name)
    async with httpx.AsyncClient() as client:
        r = await client.get(template.url)
        r.raise_for_status()

    return r.text


async def process_render(render: Render) -> str:
    template_data = await get_template_data(render.template_name)
    # template_data =
    data = render.texts.copy()
    tasks = []
    for value in render.images.values():
        tasks.append(imagetools.get_image_base64(value))

    images = await asyncio.gather(*tasks)
    for key, image in zip(render.images.keys(), images):
        data[key] = image

    mwj = await fill_render_template_data(template_data, data)

    result_image = await render_mwj(mwj)
    image_ufile = await upload_image(
        result_image,
        image_name=f"{render.id}.png",
        user_id=render.user_id,
        file_upload_dir="renders",
    )
    render.results.append(
        RenderResult(
            url=image_ufile.url, width=result_image.width, height=result_image.height
        )
    )
    await render.save()
    return render
