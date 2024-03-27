# per FastAPI docs, current best practice for startup/shutdown is to use lifespan events
# https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.lib.prisma import prisma


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Context manager for starting up and shutting down the app.
    """
    print("Starting up the app...")
    print("Connecting to the database with prisma...")
    prisma.connect()

    yield

    print("Shutting down the app...")
