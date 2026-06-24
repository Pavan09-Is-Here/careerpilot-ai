from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


ALLOWED_PROFICIENCY_LEVELS = {
    "Beginner",
    "Intermediate",
    "Advanced",
    "Expert",
}


class SkillBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=150,
    )

    category: str | None = Field(
        default=None,
        max_length=100,
    )

    proficiency: str = Field(
        default="Intermediate",
        max_length=50,
    )

    years_experience: float | None = Field(
        default=None,
        ge=0,
        le=50,
    )

    evidence: str | None = Field(
        default=None,
        max_length=3000,
    )

    is_primary: bool = False
    verified: bool = False

    @field_validator("name")
    @classmethod
    def clean_skill_name(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Skill name is required."
            )

        return cleaned_value

    @field_validator(
        "category",
        "evidence",
        mode="before",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: object,
    ) -> object:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value

    @field_validator("proficiency")
    @classmethod
    def validate_proficiency(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip().title()

        if (
            cleaned_value
            not in ALLOWED_PROFICIENCY_LEVELS
        ):
            raise ValueError(
                "Proficiency must be Beginner, "
                "Intermediate, Advanced, or Expert."
            )

        return cleaned_value


class SkillCreate(SkillBase):
    pass


class SkillUpdate(SkillBase):
    pass


class SkillResponse(SkillBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime