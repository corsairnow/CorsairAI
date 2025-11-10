from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    DEFAULT_MODEL: str = "pacozaa/defog-llama3-sqlcoder-8b"
    ALLOWED_MODELS: str = "llama-3-sqlcoder-8b:latest,sqlcoder-best:latest,pacozaa/defog-llama3-sqlcoder-8b"
    SCHEMA_PATH: str = "./schema/schema.yaml"
    SHOTS_PATH: str = "./schema/shots.yaml"
    LIMIT_MAX: int = 200
    LIMIT_MAX_CAP: int = 2000
    OLLAMA_TIMEOUT: float = 60.0

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

settings = Settings()

def allowed_models() -> set[str]:
    return {m.strip() for m in settings.ALLOWED_MODELS.split(",") if m.strip()}




