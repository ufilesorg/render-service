from datetime import datetime
from uuid import UUID

from fastapi import Query, Request
from fastapi_mongo_base.routes import AbstractBaseRouter
from fastapi_mongo_base.schemas import PaginatedResponse
from server.config import Settings
from usso import UserData
from usso.fastapi import jwt_access_security

from .models import Template, TemplateGroup
from .schemas import (
    TemplateCreateSchema,
    TemplateGroupCreateSchema,
    TemplateGroupDetailSchema,
    TemplateSchema,
)


class TemplateRouter(AbstractBaseRouter[Template, TemplateSchema]):
    def __init__(self):
        super().__init__(model=Template, schema=TemplateSchema, user_dependency=None)

    async def get_user(self, request: Request, *args, **kwargs) -> UserData | None:
        if request.method in ["GET", "OPTIONS"]:
            return None
        return jwt_access_security(request)

    async def create_item(
        self, request: Request, data: TemplateCreateSchema
    ) -> Template:
        return await super().create_item(request, data.model_dump())


class TemplateGroupRouter(AbstractBaseRouter):
    def __init__(self):
        super().__init__(
            model=TemplateGroup,
            schema=TemplateGroupDetailSchema,
            user_dependency=None,
            tags=["Template"],
            prefix="/templates/groups",
        )

    async def get_user(self, request: Request, *args, **kwargs) -> UserData | None:
        if request.method in ["GET", "OPTIONS"]:
            return None
        return jwt_access_security(request)

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=Settings.page_max_limit),
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ):
        user_id = await self.get_user_id(request)
        limit = max(1, min(limit, Settings.page_max_limit))

        items, total = await self.model.list_total_combined(
            user_id=user_id,
            offset=offset,
            limit=limit,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )
        items_in_schema = [
            self.list_item_schema(**item.model_dump(), fields=await item.get_fields())
            for item in items
        ]

        return PaginatedResponse(
            items=items_in_schema,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def retrieve_item(self, request: Request, uid: UUID):
        item = await super().retrieve_item(request, uid)
        return TemplateGroupDetailSchema(
            **item.model_dump(), fields=await item.get_fields()
        )

    async def create_item(
        self, request: Request, data: TemplateGroupCreateSchema
    ) -> TemplateGroupDetailSchema:
        template_group: TemplateGroup = await super().create_item(
            request, data.model_dump()
        )
        return TemplateGroupDetailSchema(
            **template_group.model_dump(), fields=await template_group.get_fields()
        )


router = TemplateRouter().router
router_group = TemplateGroupRouter().router
