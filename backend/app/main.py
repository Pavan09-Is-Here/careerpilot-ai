from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.router import api_router


app = FastAPI(
    title="CareerPilot AI API",
    description=(
        "Backend API for candidate profiles, "
        "verified career facts, job discovery, "
        "CV tailoring and safe job applications."
    ),
    version="0.7.0",
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
