import fastapi
from fastapi_mongo_base.routes import AbstractBaseRouter
from usso.fastapi import jwt_access_security

from .models import Render, RenderGroup
from .schemas import (
    RenderCreateSchema,
    RenderGroupCreateSchema,
    RenderGroupSchema,
    RenderSchema,
)
from .services import process_render, process_render_bulk


class RenderRouter(AbstractBaseRouter[Render, RenderSchema]):
    def __init__(self):
        super().__init__(
            model=Render,
            schema=RenderSchema,
            user_dependency=jwt_access_security,
            # tags=["Render"],
            # prefix="",
        )

    def config_routes(self, **kwargs):
        kwargs["update_route"] = False
        super().config_routes(**kwargs)

    async def create_item(
        self,
        request: fastapi.Request,
        data: RenderCreateSchema,
    ):
        render = await super().create_item(request, data.model_dump())
        await process_render(render)
        return render


class RenderGroupRouter(AbstractBaseRouter[RenderGroup, RenderGroupSchema]):
    def __init__(self):
        super().__init__(
            model=RenderGroup,
            schema=RenderGroupSchema,
            user_dependency=jwt_access_security,
            tags=["Render"],
            prefix="/renders/bulk",
        )

    def config_routes(self, **kwargs):
        kwargs["update_route"] = False
        super().config_routes(**kwargs)

    async def create_item(
        self,
        request: fastapi.Request,
        data: RenderGroupCreateSchema,
    ):
        render_group = await super().create_item(request, data.model_dump())
        await process_render_bulk(render_group)
        return render_group


router = RenderRouter().router
router_group = RenderGroupRouter().router
