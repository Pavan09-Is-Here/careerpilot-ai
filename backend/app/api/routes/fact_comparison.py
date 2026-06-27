from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.fact_comparison import (
    FactComparisonFinding,
    FactComparisonRun,
)
from app.schemas.fact_comparison import FactComparisonRunResponse


router = APIRouter(
    prefix="/fact-comparisons",
    tags=["Fact Comparisons"],
)


def list_fact_comparison_findings(
    comparison_run_id: int,
    database: Session,
) -> list[FactComparisonFinding]:
    findings = database.scalars(
        select(FactComparisonFinding)
        .where(
            FactComparisonFinding.comparison_run_id == comparison_run_id,
        )
        .order_by(
            FactComparisonFinding.sort_order.asc(),
            FactComparisonFinding.id.asc(),
        )
    ).all()

    return list(findings)


def get_latest_fact_comparison_run(
    document_id: int,
    database: Session,
) -> FactComparisonRun | None:
    latest_successful = database.scalars(
        select(FactComparisonRun)
        .where(
            FactComparisonRun.document_id == document_id,
            FactComparisonRun.status == "completed",
            FactComparisonRun.is_latest_successful.is_(True),
        )
        .order_by(
            FactComparisonRun.created_at.desc(),
            FactComparisonRun.id.desc(),
        )
    ).first()

    if latest_successful is not None:
        return latest_successful

    return database.scalars(
        select(FactComparisonRun)
        .where(FactComparisonRun.document_id == document_id)
        .order_by(
            FactComparisonRun.created_at.desc(),
            FactComparisonRun.id.desc(),
        )
    ).first()


def get_fact_comparison_or_404(
    comparison_id: int,
    database: Session,
) -> FactComparisonRun:
    comparison_run = database.get(FactComparisonRun, comparison_id)

    if comparison_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact comparison was not found.",
        )

    document = database.get(Document, comparison_run.document_id)

    if document is None or document.candidate_profile_id != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact comparison was not found.",
        )

    return comparison_run


def build_fact_comparison_response(
    comparison_run: FactComparisonRun,
    database: Session,
) -> dict[str, object]:
    return {
        "id": comparison_run.id,
        "document_id": comparison_run.document_id,
        "status": comparison_run.status,
        "started_at": comparison_run.started_at,
        "completed_at": comparison_run.completed_at,
        "error": comparison_run.error,
        "total_findings": comparison_run.total_findings,
        "confirmed_count": comparison_run.confirmed_count,
        "mismatch_count": comparison_run.mismatch_count,
        "missing_verified_count": comparison_run.missing_verified_count,
        "unverified_claim_count": comparison_run.unverified_claim_count,
        "manual_review_count": comparison_run.manual_review_count,
        "comparison_version": comparison_run.comparison_version,
        "is_latest_successful": comparison_run.is_latest_successful,
        "created_at": comparison_run.created_at,
        "findings": list_fact_comparison_findings(
            comparison_run.id,
            database,
        ),
    }


@router.get(
    "/{comparison_id}",
    response_model=FactComparisonRunResponse,
)
def get_fact_comparison(
    comparison_id: int,
    database: Session = Depends(get_db),
) -> dict[str, object]:
    comparison_run = get_fact_comparison_or_404(
        comparison_id,
        database,
    )

    return build_fact_comparison_response(comparison_run, database)
