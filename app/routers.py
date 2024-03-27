import os
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    APIRouter,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import health
from app.core import main as core

from app.lib import middleware
from app.lib.models.response import Response
from app.lib.servers import servers
from app.lib.lifespan import app_lifespan

load_dotenv()

API_PREFIX_V1 = os.getenv("API_PREFIX_V1") or "/api/v1"


def setup_router():
    """
    Setup the API router with all routes included in the root app.
    """
    router = APIRouter()
    router.include_router(health.router)

    return router


def setup_mounts(app: FastAPI):
    """
    Mount sub apps and static files. A sub app is a FastAPI instance which is mounted on
    a specific path. This allows for a modular approach to the API. Static files are
    mounted on the root path /static.

    Args:
        app (FastAPI): FastAPI instance

    Returns:
        FastAPI: FastAPI instance with sub apps and static files mounted

    """

    # Mount sub apps
    app.mount(API_PREFIX_V1 + "/core", core.app, name="core")
    # mount documentation
    # app.mount(
    #     "/documentation",
    #     StaticFiles(directory="app/documentation", html=True),
    #     name="documentation",
    # )

    return app


def setup_app():
    """
    Setup the FastAPI instance with middleware, routes, and sub apps.

    Returns:
        FastAPI: FastAPI instance with middleware added

    """
    _lifespan = app_lifespan

    app = FastAPI(
        title="OpenAI Assistants Link API",
        description="Link your OpenAI Assistants to your own database and services",
        version="0.0.1",
        lifespan=_lifespan,
        servers=servers,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # add middleware to http requests
    app.add_middleware(
        middleware.TimeLoggingMiddleware,
    )

    @app.get("/", tags=["Index"])
    async def index():
        return Response(data={"data": "Welcome to the OpenAI Assistants Link API"}, success=True)
        # return RedirectResponse(url="/documentation", status_code=status.HTTP_302_FOUND) # implement later with documentation

    app.include_router(
        setup_router(),
    )

    app = setup_mounts(app)

    return app
