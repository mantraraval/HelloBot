import os
from functools import lru_cache
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for the HelloBot Python service.

    In a real deployment, these values should come from environment
    variables or a secrets manager. We keep sane defaults here to make
    local development easy while still promoting good practices.
    """

    app_name: str = "HelloBot Orchestration Service"
    environment: str = os.getenv("HELLOBOT_ENV", "development")

    # LLM provider configuration (e.g. OpenAI, Azure OpenAI, etc.)
    llm_api_key: str | None = os.getenv("HELLOBOT_LLM_API_KEY")
    llm_model: str = os.getenv("HELLOBOT_LLM_MODEL", "gpt-4.1-mini")
    llm_base_url: AnyHttpUrl | None = (
        os.getenv("HELLOBOT_LLM_BASE_URL")  # type: ignore[assignment]
        if os.getenv("HELLOBOT_LLM_BASE_URL")
        else None
    )

    # Relational database (PostgreSQL/MySQL) connection
    sql_dsn: str = os.getenv(
        "HELLOBOT_SQL_DSN",
        # Docker-compose default; replace driver as needed (postgresql, mysql+pymysql, etc.)
        "postgresql+psycopg2://hellobot:hellobot@postgres:5432/hellobot",
    )

    # MongoDB knowledge base connection
    mongo_dsn: str = os.getenv("HELLOBOT_MONGO_DSN", "mongodb://mongo:27017")
    mongo_db_name: str = os.getenv("HELLOBOT_MONGO_DB", "hellobot_knowledge")

    # Conversation / context configuration
    context_ttl_seconds: int = 60 * 30  # 30 minutes
    max_history_turns: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    FastAPI-friendly dependency to obtain a cached Settings instance.
    """

    return Settings()

