from fastapi import Request
from fastapi_mongo_base.routes import AbstractBaseRouter
from usso import UserData
from usso.fastapi import jwt_access_security

from .models import Template
from .schemas import TemplateCreateSchema, TemplateSchema


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


router = TemplateRouter().router
