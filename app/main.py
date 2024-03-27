from app.routers import setup_app
from app.lib.logging import setup_logging_config

setup_logging_config()

app = setup_app()
