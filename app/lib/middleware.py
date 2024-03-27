from fastapi import Request
import time
from starlette.middleware.base import BaseHTTPMiddleware

class TimeLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Print the request info first
        print(f"{request.method} {request.url} - {response.status_code}")

        # format string to be more readable
        formatted_process_time = "{:.3f}".format(process_time)

        # add process time to response headers
        response.headers["X-Process-Time"] = formatted_process_time

        print(f"Total request time: {formatted_process_time} secs")
        return response