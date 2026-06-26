from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAREERPILOT_",
    )

    document_storage_dir: Path = (
        Path(__file__).resolve().parents[2] / "data" / "documents"
    )
    max_document_upload_size_bytes: int = 10 * 1024 * 1024
    max_document_extracted_text_characters: int = 200_000
