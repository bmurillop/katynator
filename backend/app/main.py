import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.bootstrap import bootstrap_admin, seed_categories
from app.api import health, auth, settings

logging.basicConfig(level=logging.INFO)

_CORS_ORIGINS = [
    "http://finanzas.internal",
    "https://finanzas.internal",
    "http://localhost",
    "http://localhost:5173",  # Vite dev server (Phase 5)
    "http://localhost:3000",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_admin()
    await seed_categories()
    yield


app = FastAPI(title="Family Finance Tracker", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
