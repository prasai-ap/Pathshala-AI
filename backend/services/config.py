"""Application configuration loaded from environment variables."""

import logging
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()

LOGGER = logging.getLogger(__name__)


DEFAULT_APP_NAME = "Pathshala AI"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_BACKEND_HOST = "0.0.0.0"
DEFAULT_BACKEND_PORT = 8000
DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_FRONTEND_PORT = 8501
DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_QDRANT_COLLECTION = "pathshala_curriculum"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    environment: str
    backend_host: str
    backend_port: int
    backend_url: str
    frontend_port: int
    qdrant_url: str
    qdrant_collection: str
    embedding_model: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str

    @property
    def llm_mode(self) -> str:
        return "AMD vLLM mode" if self.llm_base_url else "mock mode"

    @property
    def is_mock_llm(self) -> bool:
        return not self.llm_base_url


def validate_config(config: AppConfig) -> None:
    missing = []

    required_values = {
        "APP_NAME": config.app_name,
        "ENVIRONMENT": config.environment,
        "BACKEND_HOST": config.backend_host,
        "BACKEND_URL": config.backend_url,
        "QDRANT_URL": config.qdrant_url,
        "QDRANT_COLLECTION": config.qdrant_collection,
        "EMBEDDING_MODEL": config.embedding_model,
        "LLM_MODEL": config.llm_model,
    }

    for name, value in required_values.items():
        if not str(value).strip():
            missing.append(name)

    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required environment values: {joined}")

    if config.backend_port <= 0:
        raise RuntimeError("BACKEND_PORT must be greater than zero.")

    if config.frontend_port <= 0:
        raise RuntimeError("FRONTEND_PORT must be greater than zero.")

    if config.llm_base_url and not config.llm_api_key.strip():
        LOGGER.warning("LLM_BASE_URL is set but LLM_API_KEY is empty.")


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    import os

    config = AppConfig(
        app_name=os.getenv("APP_NAME", DEFAULT_APP_NAME).strip(),
        environment=os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT).strip(),
        backend_host=os.getenv("BACKEND_HOST", DEFAULT_BACKEND_HOST).strip(),
        backend_port=_get_int("BACKEND_PORT", DEFAULT_BACKEND_PORT),
        backend_url=os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL).strip().rstrip("/"),
        frontend_port=_get_int("FRONTEND_PORT", DEFAULT_FRONTEND_PORT),
        qdrant_url=os.getenv("QDRANT_URL", DEFAULT_QDRANT_URL).strip(),
        qdrant_collection=os.getenv(
            "QDRANT_COLLECTION",
            DEFAULT_QDRANT_COLLECTION,
        ).strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip(),
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip(),
    )
    validate_config(config)
    return config


def log_startup_config(config: AppConfig) -> None:
    LOGGER.info(
        "Starting %s in %s environment on %s:%s",
        config.app_name,
        config.environment,
        config.backend_host,
        config.backend_port,
    )
    LOGGER.info("Qdrant URL: %s", config.qdrant_url)
    LOGGER.info("Qdrant collection: %s", config.qdrant_collection)
    LOGGER.info("Embedding model: %s", config.embedding_model)

    if config.is_mock_llm:
        LOGGER.info("LLM mode: mock mode because LLM_BASE_URL is empty.")
    else:
        LOGGER.info(
            "LLM mode: AMD vLLM mode using %s with model %s",
            config.llm_base_url,
            config.llm_model,
        )


def _get_int(name: str, default: int) -> int:
    import os

    raw_value = os.getenv(name, str(default)).strip()

    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
