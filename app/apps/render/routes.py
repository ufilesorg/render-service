import fastapi
from fastapi_mongo_base.routes import AbstractBaseRouter
from usso.fastapi import jwt_access_security

from .models import Render
from .schemas import RenderCreateSchema, RenderSchema
from .services import process_render


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


router = RenderRouter().router
