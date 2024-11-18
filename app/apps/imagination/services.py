import asyncio
import json
import logging
import re
import uuid

import aiohttp
from apps.imagination.models import Imagination
from apps.imagination.schemas import (
    ImaginationEngines,
    ImaginationStatus,
    ImagineResponse,
    ImagineWebhookData,
)
from fastapi_mongo_base._utils.basic import delay_execution, try_except_wrapper
from metisai.async_metis import AsyncMetisBot
from PIL import Image
from server.config import Settings
from usso.async_session import AsyncUssoSession
from utils import ai, aionetwork, imagetools, ufiles


def sanitize_filename(prompt: str):
    # Remove invalid characters and replace spaces with underscores
    # Valid characters: alphanumeric, underscores, and periods
    prompt_parts = prompt.split(",")
    prompt = prompt_parts[1] if len(prompt_parts) > 1 else prompt
    prompt = prompt.strip()
    position = prompt.find(" ", 80)
    if position > 120 or position == -1:
        position = 100
    sanitized = re.sub(r"[^a-zA-Z0-9_. ]", "", prompt)
    sanitized = sanitized.replace(" ", "_")  # Replace spaces with underscores
    return sanitized[:position]  # Limit to 100 characters


async def upload_image(
    client: AsyncUssoSession | aiohttp.ClientSession,
    image: Image.Image,
    image_name: str,
    user_id: uuid.UUID,
    prompt: str,
    engine: ImaginationEngines = ImaginationEngines.midjourney,
    file_upload_dir: str = "imaginations",
):
    image_bytes = imagetools.convert_to_webp_bytes(image)
    image_bytes.name = f"{image_name}.webp"
    return await ufiles.AsyncUFiles().upload_bytes_session(
        client,
        image_bytes,
        filename=f"{file_upload_dir}/{image_bytes.name}",
        public_permission=json.dumps({"permission": ufiles.PermissionEnum.READ}),
        user_id=str(user_id),
        meta_data={
            "prompt": prompt,
            "engine": engine.value,
        },
    )


async def upload_images(
    images: list[Image.Image],
    user_id: uuid.UUID,
    prompt: str,
    engine: ImaginationEngines = ImaginationEngines.midjourney,
    file_upload_dir="imaginations",
):
    image_name = sanitize_filename(prompt)

    async with AsyncUssoSession(
        ufiles.AsyncUFiles().refresh_url,
        ufiles.AsyncUFiles().refresh_token,
    ) as client:
        uploaded_items = [
            await upload_image(
                client,
                images[0],
                image_name=f"{image_name}_{1}",
                user_id=user_id,
                prompt=prompt,
                engine=engine,
                file_upload_dir=file_upload_dir,
            )
        ]
        uploaded_items += await asyncio.gather(
            *[
                upload_image(
                    client,
                    image,
                    image_name=f"{image_name}_{i+2}",
                    user_id=user_id,
                    prompt=prompt,
                    engine=engine,
                    file_upload_dir=file_upload_dir,
                )
                for i, image in enumerate(images[1:])
            ]
        )
        # uploaded_items = await asyncio.gather(
        #     *[
        #         upload_image(
        #             client,
        #             image,
        #             image_name=f"{image_name}_{i+1}",
        #             user_id=user_id,
        #             prompt=prompt,
        #             engine=engine,
        #             file_upload_dir=file_upload_dir,
        #         )
        #         for i, image in enumerate(images)
        #     ]
        # )
    return uploaded_items


async def process_result(imagination: Imagination, generated_url: str):
    try:
        # Download the image
        image_bytes = await aionetwork.aio_request_binary(url=generated_url)
        image = Image.open(image_bytes)
        file_upload_dir = "imaginations"

        # Crop the image into 4 sections
        cropped_images = imagetools.crop_image(image, sections=(2, 2))
        uploaded_items = await upload_images(
            images=cropped_images,
            user_id=imagination.user_id,
            prompt=imagination.prompt,
            engine=imagination.engine,
            file_upload_dir=file_upload_dir,
        )

        imagination.results = [
            ImagineResponse(url=uploaded.url, width=image.width, height=image.height)
            for uploaded, image in zip(uploaded_items, cropped_images)
        ]

    except Exception as e:
        import traceback

        traceback_str = "".join(traceback.format_tb(e.__traceback__))
        logging.error(f"Error processing image: {e}\n{traceback_str}")

    return


async def process_imagine_webhook(imagination: Imagination, data: ImagineWebhookData):
    if data.status == "error":
        await imagination.retry(data.error)
        return

    if data.status == "completed":
        result_url = (data.result or {}).get("uri")
        await process_result(imagination, result_url)

    imagination.task_progress = data.percentage
    imagination.status = ImaginationStatus.from_midjourney(data.status)
    imagination.task_status = imagination.status.task_status

    report = (
        f"Midjourney completed."
        if data.status == "completed"
        else f"Midjourney update. {imagination.status}"
    )

    await imagination.save_report(report)


async def request_imagine_metis(
    imagination: Imagination,
    engine: ImaginationEngines = ImaginationEngines.midjourney,
):
    bot = AsyncMetisBot(Settings.METIS_API_KEY, engine.metis_bot_id)
    session = await bot.create_session()
    await bot.send_message_async(session, f"/imagine {imagination.prompt}")


async def create_prompt(imagination: Imagination, enhance: bool = False):
    async def get_prompt_row(item: dict):
        return f'{item.get("topic", "")} {await ai.translate(item.get("value", ""))}'

    prompt = await ai.translate(imagination.prompt or imagination.delineation or "")
    context = await asyncio.gather(
        *[get_prompt_row(item) for item in imagination.context or []]
    )
    prompt += ", " + ", ".join(context)
    prompt = prompt.strip(",").strip()

    if enhance:
        # TODO: Enhance the prompt
        pass

    return prompt


@try_except_wrapper
async def imagine_request(imagination: Imagination):
    prompt = await create_prompt(imagination)
    if imagination.mode != "imagine":
        return

    if imagination.engine != ImaginationEngines.midjourney:
        raise NotImplementedError("Only Midjourney engine is supported")

    imagination.prompt = prompt
    mid_request = await ai.Midjourney().imagine(
        prompt, callback=imagination.webhook_url
    )

    imagination.meta_data = (imagination.meta_data or {}) | mid_request.model_dump()
    await imagination.save_report(f"Midjourney has been requested.")
    new_task = asyncio.create_task(imagine_update(imagination))
    return new_task


@try_except_wrapper
@delay_execution(Settings.update_time)
async def imagine_update(imagination: Imagination, i=0):
    # logging.info(f"Updating imagination {i} {imagination}")
    if imagination.statuhas.is_done:
        return

    if imagination.engine != ImaginationEngines.midjourney:
        raise NotImplementedError("Only Midjourney engine is supported")

    if (imagination.meta_data or {}).get("uuid") is None:
        raise ValueError("Missing Midjourney task id")

    task_id = imagination.meta_data.get("uuid")
    mid_result = await ai.Midjourney().get_result(task_id)
    mid_result.result = (mid_result.result or {}) | {"uri": mid_result.uri}

    await process_imagine_webhook(
        imagination, ImagineWebhookData(**mid_result.model_dump())
    )
    return asyncio.create_task(imagine_update(imagination, i + 1))
