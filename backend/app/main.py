from fastapi import FastAPI
from app.api.v1.router import api_router
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Lawhook API",
    description="API for Lawhook, a tool for monitoring and analyzing code changes.",
    version="0.1.0"
)

from fastapi.middleware.cors import CORSMiddleware
import os
from app.middleware.rate_limit import RateLimitMiddleware

# Origins that are allowed to call the API
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173"      # Vite default dev port
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(
    RateLimitMiddleware,
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

app.include_router(api_router, prefix="/v1")


@app.get("/")
def root():
    return {
        "service": "Lawhook API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'Lawhook API'}

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    logger.warning("422 on %s: %s", request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})