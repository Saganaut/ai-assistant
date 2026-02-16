from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Assistant"
    debug: bool = False

    # Paths
    data_dir: Path = Path(__file__).resolve().parent.parent.parent / "data"
    db_path: Path = Path(__file__).resolve().parent.parent.parent / "assistant.db"

    # LLM
    llm_provider: str = "gemini"  # gemini | openai | local
    gemini_api_key: str = ""

    # TTS
    tts_provider: str = "elevenlabs"  # elevenlabs | local
    elevenlabs_api_key: str = ""

    # Google
    google_credentials_path: str = ""

    # GitHub
    github_token: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "env_prefix": "ASSISTANT_",
    }


settings = Settings()
