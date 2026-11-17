import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (tabloların metadata'ya kaydı için)
from app.api.routes import auth, users
from app.core.config import settings
from app.db import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("taskflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Veritabanı hazır: %s", engine.url.render_as_string(hide_password=True))
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Takımlar için görev yönetimi REST API'si. "
        "JWT kimlik doğrulama, rol bazlı yetkilendirme (owner/admin/member), "
        "filtreleme, sıralama ve sayfalama destekler."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok"}


for router in (auth.router, users.router):
    app.include_router(router, prefix=settings.API_V1_PREFIX)
