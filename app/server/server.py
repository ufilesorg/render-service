from apps.render.routes import router as render_router
from apps.render.routes import router_group as render_group_router
from apps.template.routes import router as template_router
from apps.template.routes import router_group as template_group_router
from fastapi_mongo_base.core import app_factory

from . import config

app = app_factory.create_app(settings=config.Settings(), original_host_middleware=True)
app.include_router(render_router, prefix=f"{config.Settings.base_path}")
app.include_router(render_group_router, prefix=f"{config.Settings.base_path}")
app.include_router(template_router, prefix=f"{config.Settings.base_path}")
app.include_router(template_group_router, prefix=f"{config.Settings.base_path}")
