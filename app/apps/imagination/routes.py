import logging
import uuid

import fastapi
from fastapi import BackgroundTasks
from fastapi_mongo_base.routes import AbstractBaseRouter
from fastapi_mongo_base.tasks import TaskStatusEnum
from usso.fastapi import jwt_access_security

from apps.ai.schemas import ImaginationEngines, ImaginationEnginesSchema
from core.exceptions import BaseHTTPException

from .models import Imagination, ImaginationBulk
from .schemas import (
    ImagineBulkSchema,
    ImagineCreateBulkSchema,
    ImagineCreateSchema,
    ImagineSchema,
    ImagineWebhookData,
)
from .services import process_imagine_webhook


class ImaginationRouter(AbstractBaseRouter[Imagination, ImagineSchema]):
    def __init__(self):
        super().__init__(
            model=Imagination,
            schema=ImagineSchema,
            user_dependency=jwt_access_security,
            tags=["Imagination"],
            prefix="",
        )

    def config_routes(self, **kwargs):
        self.router.add_api_route(
            "/imagination",
            self.list_items,
            methods=["GET"],
            response_model=self.list_response_schema,
            status_code=200,
        )
        self.router.add_api_route(
            "/imagination/",
            self.create_item,
            methods=["POST"],
            response_model=self.create_response_schema,
            status_code=201,
        )
        self.router.add_api_route(
            "/imagination/{uid:uuid}",
            self.retrieve_item,
            methods=["GET"],
            response_model=self.retrieve_response_schema,
            status_code=200,
        )
        self.router.add_api_route(
            "/imagination/{uid:uuid}",
            self.delete_item,
            methods=["DELETE"],
            # status_code=204,
            response_model=self.delete_response_schema,
        )
        self.router.add_api_route(
            "/imagination/{uid:uuid}/webhook",
            self.webhook,
            methods=["POST"],
            status_code=200,
        )
        self.router.add_api_route(
            "/imagination/bulk",
            self.create_bulk_item,
            methods=["POST"],
            response_model=ImagineBulkSchema,
            status_code=201,
        )
        self.router.add_api_route(
            "/imagination/bulk/{uid:uuid}",
            self.retrieve_bulk_item,
            methods=["GET"],
            response_model=ImagineBulkSchema,
        )

    async def create_item(
        self,
        request: fastapi.Request,
        data: ImagineCreateSchema,
        background_tasks: BackgroundTasks,
    ):
        item: Imagination = await super().create_item(request, data.model_dump())
        item.task_status = "init"
        if data.sync:
            await item.start_processing()
        else:
            background_tasks.add_task(item.start_processing)
        return item

    async def webhook(
        self, request: fastapi.Request, uid: uuid.UUID, data: ImagineWebhookData
    ):
        # logging.info(f"Webhook received: {await request.json()}")
        item: Imagination = await self.get_item(uid, user_id=None)
        if item.status == "cancelled":
            return {"message": "Imagination has been cancelled."}
        await process_imagine_webhook(item, data)
        return {}

    async def create_bulk_item(
        self,
        request: fastapi.Request,
        data: ImagineCreateBulkSchema,
        background_tasks: BackgroundTasks,
    ):
        user_id = await self.get_user_id(request)
        item: ImaginationBulk = await ImaginationBulk.create_item(
            {
                "user_id": user_id,
                "task_status": TaskStatusEnum.init,
                **data.model_dump(),
                "total_tasks": len(data.engines),
            }
        )
        background_tasks.add_task(item.start_processing)
        return item

    async def retrieve_bulk_item(
        self,
        request: fastapi.Request,
        uid: uuid.UUID,
        background_tasks: BackgroundTasks,
    ):
        user_id = await self.get_user_id(request)
        item = await ImaginationBulk.get_item(uid, user_id=user_id)
        if item is None:
            raise BaseHTTPException(
                status_code=404,
                error="item_not_found",
                message=f"{ImaginationBulk.__name__.capitalize()} not found",
            )
        return item

    async def webhook_bulk(self, request: fastapi.Request, uid: uuid.UUID, data: dict):
        logging.info(f"Webhook received: {await request.json()}")
        return {}
        item: Imagination = await self.get_item(uid, user_id=None)
        if item.status == "cancelled":
            return {"message": "Imagination has been cancelled."}
        await process_imagine_webhook(item, data)
        return {}


router = ImaginationRouter().router


@router.get("/engines")
async def engines():
    engines = [
        ImaginationEnginesSchema.from_model(engine) for engine in ImaginationEngines
    ]
    return engines
