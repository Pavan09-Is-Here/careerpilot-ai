from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.router import api_router
from app.core.config import Settings
from app.core.database import engine
from app.core.security import SecurityHeadersMiddleware


settings = Settings()


def _init_error_reporting(app_settings: Settings) -> None:
    """Initialise Sentry only when a DSN is configured.

    Without a DSN this is a no-op, so development and tests run with no
    external reporting and no secrets in source.
    """
    if not app_settings.sentry_dsn:
        return

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=app_settings.sentry_dsn,
            environment=app_settings.environment,
            traces_sample_rate=app_settings.sentry_traces_sample_rate,
        )
    except Exception:  # noqa: BLE001 - reporting must never block startup
        pass


_init_error_reporting(settings)


app = FastAPI(
    title="CareerPilot AI API",
    description=(
        "Backend API for candidate profiles, "
        "verified career facts, job discovery, "
        "CV tailoring and safe job applications."
    ),
    version="0.7.0",
)

app.add_middleware(SecurityHeadersMiddleware)


def _allowed_origins(app_settings: Settings) -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    for origin in app_settings.cors_origins.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in origins:
            origins.append(cleaned)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": (
            "CareerPilot AI backend is running"
        ),
        "status": "healthy",
    }


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {
        "service": "careerpilot-api",
        "status": "healthy",
        "version": "0.7.0",
        "environment": settings.environment,
        "database": engine.url.get_backend_name(),
    }
