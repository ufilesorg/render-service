import asyncio
from datetime import datetime, timedelta

from .models import Imagination
from .schemas import ImaginationEngines, ImaginationStatus
from .services import update_imagination_status


async def update_imagination():
    data: list[Imagination] = (
        await Imagination.get_query()
        .find(
            {
                "created_at": {"$lte": datetime.now() - timedelta(minutes=3)},
                "status": {"$nin": ImaginationStatus.done_statuses()},
                "engine": {"$in": ImaginationEngines},
            }
        )
        .to_list()
    )
    for imagination in data:
        asyncio.create_task(update_imagination_status(imagination))
