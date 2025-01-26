import asyncio
import json
import uuid

import httpx
import jinja2
from apps.template.models import Template, TemplateGroup
from apps.template.schemas import FieldType
from fastapi_mongo_base.utils import basic, texttools
from PIL import Image
from server.config import Settings
from utils import imagetools

import ufiles

from .models import Render, RenderGroup
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
    image_bytes = imagetools.convert_image_bytes(image, "JPEG", 90)
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


async def fill_render_template_data(template_data: str, data: dict) -> dict:
    jinja_template = jinja2.Template(template_data)
    text = jinja_template.render(**data)
    result = json.loads(text)
    return result


async def get_template_data(template_name: str) -> str:
    template = await Template.get_by_name(template_name)
    async with httpx.AsyncClient() as client:
        r = await client.get(template.url)
        r.raise_for_status()

    return r.text


async def rendering_template_data(
    template_name: str, render: Render | RenderGroup
) -> dict:

    def get_text_dict(texts: dict | list[str], template: Template) -> dict[str, str]:
        if isinstance(texts, dict):
            return texts.copy()

        result = {}
        for i, field in enumerate(template.fields):
            if field.type != FieldType.text:
                continue
            result[field.name] = texts[i] if len(texts) > i else field.default
        return result

    async def get_image_dict(
        images: dict | list[str], template: Template
    ) -> dict[str, str]:
        if isinstance(images, dict):
            downloaded_images = await asyncio.gather(
                *[imagetools.download_image_base64(value) for value in images.values()]
            )
            return dict(zip(images.keys(), downloaded_images))

        result = {}
        for i, field in enumerate(template.fields):
            if field.type != FieldType.image:
                continue
            result[field.name] = images[i] if len(images) > i else field.default
        return result

    def get_font_dict(fonts: list[str] | str, template: Template) -> dict[str, str]:
        if isinstance(fonts, str):
            fonts = [fonts] * len(template.fonts)
        template_font = template.fonts[0] if len(template.fonts) > 0 else "Vazirmatn"
        data = {"font": fonts[0] if len(fonts) > 0 else template_font}
        for i, font in enumerate(template.fonts):
            data[f"font{i+1}"] = fonts[i] if len(fonts) > i else font
        return data

    def get_color_dict(colors: list[str], template: Template) -> dict[str, str]:
        template_color = template.colors[0] if len(template.colors) > 0 else "#000000"
        data = {"color": colors[0] if len(colors) > 0 else template_color}
        for i, color in enumerate(template.colors):
            data[f"color{i+1}"] = colors[i] if len(colors) > i else color
        return data

    template_data = await get_template_data(template_name)
    template = await Template.get_by_name(template_name)

    data = (
        get_text_dict(render.texts, template)
        | get_font_dict(render.fonts, template)
        | get_color_dict(render.colors, template)
        | await get_image_dict(render.images, template)
        | {
            "logo": (
                await imagetools.download_image_base64(render.logo)
                if render.logo
                else None
            )
        }
    )

    mwj = await fill_render_template_data(template_data, data)
    return mwj


@basic.retry_execution(attempts=3, delay=1)
async def render_mwj(mwj: dict) -> Image.Image:
    # logging.info(f"Rendering mwj: {mwj}")
    with open("logs/mwj.json", "w") as f:
        json.dump(mwj, f, indent=4, ensure_ascii=False)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            Settings.MWJ_RENDER_URL,
            json={"template": mwj},
            headers={"x-api-key": Settings.RENDER_API_KEY},
        )
        r.raise_for_status()

    base64_str = r.json().get("result")
    # logging.info(base64_str)
    return imagetools.load_from_base64(base64_str)


async def process_render(render: Render) -> Render:
    mwj = await rendering_template_data(render.template_name, render)

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


async def render_bulk(data: list[dict]) -> list[Image.Image]:
    with open("logs/mwj.json", "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{Settings.MWJ_RENDER_URL}/bulk",
            json={"templates": data, "data": {"name": "test"}},
            headers={"x-api-key": Settings.RENDER_API_KEY},
        )
        r.raise_for_status()
    renders = r.json().get("results")
    output = []
    for render in renders:
        output.append(imagetools.load_from_base64(render))
    return output


async def upload_image_result(
    result_image: Image.Image, basename: str, user_id: uuid.UUID
):
    width, height = result_image.size
    image_ufile = await upload_image(
        result_image,
        image_name=f"{basename}_{width}x{height}.png",
        user_id=user_id,
        file_upload_dir="renders",
    )
    return RenderResult(
        url=image_ufile.url,
        width=width,
        height=height,
    )


async def process_render_bulk(render_group: RenderGroup) -> RenderGroup:
    template_group = await TemplateGroup.get_by_name(render_group.group_name)
    render_requests = [
        Render(**render_group.model_dump(), template_name=template_name)
        for template_name in template_group.template_names
    ]
    # renders: list[Render] = []
    for render_request in render_requests:
        render = await process_render(render_request)
        render_group.results.extend(render.results)
        render_group.render_ids.append(render.uid)
        # renders.append(render)
        await asyncio.sleep(0.1)

    await render_group.save()
    return render_group


async def _process_render_bulk(render_group: RenderGroup) -> RenderGroup:
    template_group = await TemplateGroup.get_by_name(render_group.group_name)

    rendering_templates = await asyncio.gather(
        *[
            rendering_template_data(template_name, render_group)
            for template_name in template_group.template_names
        ]
    )

    result_images = await render_bulk(rendering_templates)

    texts = (
        list(render_group.texts.values())
        if isinstance(render_group.texts, dict)
        else render_group.texts
    )
    basename = texttools.sanitize_filename(texts[0] if texts else "")

    render_group.results.append(
        await upload_image_result(result_images[0], basename, render_group.user_id)
    )
    others = await asyncio.gather(
        *[
            upload_image_result(result_image, basename, render_group.user_id)
            for result_image in result_images[1:]
        ]
    )
    render_group.results.extend(others)
    await render_group.save()
    return render_group
