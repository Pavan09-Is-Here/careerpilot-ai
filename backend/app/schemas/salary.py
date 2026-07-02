from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SalaryConfidence = Literal["high", "medium", "low"]
SalaryBasis = Literal[
    "advertised_range",
    "comparable_jobs",
    "insufficient_data",
]


class SalaryRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: int = Field(gt=0)


class SalaryRecommendationResponse(BaseModel):
    job_id: int
    currency: str | None = Field(default=None, max_length=3)
    compensation_period: str | None = Field(
        default=None,
        max_length=50,
    )
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    midpoint: Decimal | None = None
    confidence: SalaryConfidence
    basis: SalaryBasis
    comparable_job_count: int = Field(ge=0)
    below_declared_minimum: bool
    factors: list[str]
    safe_answer: str = Field(max_length=2000)
    algorithm_version: str = Field(max_length=100)
