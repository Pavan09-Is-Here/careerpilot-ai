from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAREERPILOT_",
    )

    document_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "data" / "documents"
    )
    generated_cv_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "data" / "generated-cvs"
    )
    max_document_upload_size_bytes: int = 10 * 1024 * 1024
    max_generated_cv_file_size_bytes: int = 5 * 1024 * 1024
    max_document_extracted_text_characters: int = 200_000
    default_job_source_retention_days: int = 30
