import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings as _config
from app.auth.bootstrap import bootstrap_admin, seed_categories
from app.api import health, auth, settings
from app.api import emails, persons, accounts, entities, categories, category_rules, transactions, unresolved_entities, users
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)

_CORS_ORIGINS = [o.strip() for o in _config.cors_origins.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_admin()
    await seed_categories()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="MY Finanzas", version="1.0.0", lifespan=lifespan)

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
app.include_router(emails.router, prefix="/api", tags=["emails"])
app.include_router(persons.router, prefix="/api", tags=["persons"])
app.include_router(accounts.router, prefix="/api", tags=["accounts"])
app.include_router(entities.router, prefix="/api", tags=["entities"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
app.include_router(category_rules.router, prefix="/api", tags=["category-rules"])
app.include_router(transactions.router, prefix="/api", tags=["transactions"])
app.include_router(unresolved_entities.router, prefix="/api", tags=["unresolved-entities"])
app.include_router(users.router, prefix="/api", tags=["users"])
