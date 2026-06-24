from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.router import api_router
from app.core.database import Base, engine

# Import all database models before create_all().
from app.models.candidate_profile import (
    CandidateProfile,
)
from app.models.certification import Certification
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    Base.metadata.create_all(
        bind=engine,
    )

    yield


app = FastAPI(
    title="CareerPilot AI API",
    description=(
        "Backend API for candidate profiles, "
        "verified career facts, job discovery, "
        "CV tailoring and safe job applications."
    ),
    version="0.7.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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
    }