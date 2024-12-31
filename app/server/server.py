from apps.render.routes import router as render_router
from apps.template.routes import router as template_router
from fastapi_mongo_base.core import app_factory

from . import config

app = app_factory.create_app(original_host_middleware=True)
app.include_router(render_router, prefix=f"{config.Settings.base_path}")
app.include_router(template_router, prefix=f"{config.Settings.base_path}")
