from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.api import analytics, assistants, assistant_categories, categories, datasources, assistant_datasources
from app.lib.servers import create_sub_app_servers


def custom_generate_unique_id(route: APIRoute):
    """Custom function to generate unique id for each route"""
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(
    generate_unique_id_function=custom_generate_unique_id,
    root_path_in_servers=False,
    servers=create_sub_app_servers("core"),
)

app.include_router(analytics.router)
app.include_router(assistants.router)
app.include_router(datasources.router)
app.include_router(assistant_categories.router)
app.include_router(assistant_datasources.router)
app.include_router(categories.router)
