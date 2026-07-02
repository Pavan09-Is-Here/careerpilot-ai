from fastapi import APIRouter

from app.api.routes.candidate_profile import (
    router as candidate_profile_router,
)
from app.api.routes.certification import (
    router as certification_router,
)
from app.api.routes.cv_artifact import (
    router as cv_artifact_router,
)
from app.api.routes.cv_version import (
    router as cv_version_router,
)
from app.api.routes.education import (
    router as education_router,
)
from app.api.routes.experience import (
    router as experience_router,
)
from app.api.routes.fact_comparison import (
    router as fact_comparison_router,
)
from app.api.routes.job import (
    router as job_router,
)
from app.api.routes.project import (
    router as project_router,
)
from app.api.routes.skill import (
    router as skill_router,
)
from app.api.routes.document import (
    router as document_router,
)


api_router = APIRouter(
    prefix="/api",
)

api_router.include_router(
    candidate_profile_router,
)

api_router.include_router(
    education_router,
)

api_router.include_router(
    experience_router,
)

api_router.include_router(
    project_router,
)

api_router.include_router(
    skill_router,
)

api_router.include_router(
    certification_router,
)

api_router.include_router(
    document_router,
)

api_router.include_router(
    fact_comparison_router,
)

api_router.include_router(
    cv_version_router,
)

api_router.include_router(
    cv_artifact_router,
)

api_router.include_router(
    job_router,
)
