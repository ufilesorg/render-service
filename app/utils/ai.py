import json
import logging
import os

from metisai.async_metis import AsyncMetisBot
from usso.async_session import AsyncUssoSession

from server.config import Settings
from utils.texttools import backtick_formatter

metis_client = AsyncMetisBot(
    api_key=Settings.METIS_API_KEY, bot_id=Settings.METIS_BOT_ID
)


async def metis_chat(messages: dict, **kwargs):
    user_id = kwargs.get("user_id")
    session = await metis_client.create_session(user_id)
    prompt = "\n\n".join([message["content"] for message in messages])
    response = await metis_client.send_message(session, prompt)
    await metis_client.delete_session(session)
    resp_text = backtick_formatter(response.content)
    return resp_text


async def answer_messages(messages: dict, **kwargs):
    # resp_text = await openai_chat(messages, **kwargs)
    resp_text = await metis_chat(messages, **kwargs)
    try:
        return json.loads(resp_text)
    except json.JSONDecodeError:
        return {"answer": resp_text}


async def answer_with_ai(key, **kwargs) -> dict:
    kwargs["source_language"] = kwargs.get("lang", "Persian")
    kwargs["target_language"] = kwargs.get("target_language", "English")
    try:
        async with AsyncUssoSession(
            sso_refresh_url=os.getenv("USSO_REFRESH_URL"),
            refresh_token=os.getenv("USSO_REFRESH_TOKEN"),
        ) as session:
            async with session.post(
                f'{os.getenv("PROMPTLY_URL")}/{key}', json=kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()

        return await answer_messages(messages, **kwargs)
    except Exception as e:
        logging.error(f"AI request failed for {key}, {e}")
        raise e


async def translate(text: str) -> str:
    resp: dict = await answer_with_ai("graphic_translate", text=text)
    return resp.get("translated_text")
