import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, reports, upload
from app.config import get_settings
from app.db.database import init_db
from app.utils.auth import setup_logging

settings = get_settings()
logger = logging.getLogger("medintel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    logger.info("MedIntel AI backend started")
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.app_name}
