import os

BASE_URL = os.getenv("BASE_URL") or "http://localhost:8000"
API_PREFIX_V1 = os.getenv("API_PREFIX_V1") or "/api/v1"

servers = [
    {"url": f"{BASE_URL}", "description": "Default server"},
]


def create_sub_app_servers(path: str):
    return [
        {"url": f"{BASE_URL}{API_PREFIX_V1}/{path}", "description": "Default server"},
    ]
