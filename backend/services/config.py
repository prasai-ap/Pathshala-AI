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
DEFAULT_LLM_PROVIDER = "qwen"
DEFAULT_LLM_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
DEFAULT_TRANSLATION_PROVIDER = "mock"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_OCR_PROVIDER = "off"
DEFAULT_OCR_MAX_PAGES = 0


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    environment: str
    backend_host: str
    backend_port: int
    backend_url: str
    frontend_port: int
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str
    embedding_model: str
    llm_provider: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    translation_provider: str
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    openai_model: str
    ocr_provider: str
    ocr_max_pages: int

    @property
    def llm_mode(self) -> str:
        if self.llm_provider == "gemini" and self.gemini_api_key:
            return "Gemini mode"

        if self.llm_provider == "qwen" and self.llm_base_url:
            return "Qwen vLLM mode"

        return "mock mode"

    @property
    def is_mock_llm(self) -> bool:
        return self.llm_mode == "mock mode"


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

    if config.llm_provider not in {"qwen", "gemini", "mock"}:
        raise RuntimeError("LLM_PROVIDER must be qwen, gemini, or mock.")

    if config.llm_provider == "qwen" and not config.llm_model:
        raise RuntimeError("LLM_MODEL is required when LLM_PROVIDER=qwen.")

    if config.llm_base_url and not config.llm_api_key.strip():
        LOGGER.warning("LLM_BASE_URL is set but LLM_API_KEY is empty.")

    if config.llm_provider == "qwen" and not config.llm_base_url:
        LOGGER.warning("LLM_PROVIDER=qwen but LLM_BASE_URL is empty; using mock mode.")

    if config.llm_provider == "gemini" and not config.gemini_api_key:
        LOGGER.warning("LLM_PROVIDER=gemini but GEMINI_API_KEY is empty; using mock mode.")

    if config.translation_provider not in {"gemini", "openai", "mock"}:
        raise RuntimeError("TRANSLATION_PROVIDER must be gemini, openai, or mock.")

    if config.ocr_provider not in {"gemini", "off"}:
        raise RuntimeError("OCR_PROVIDER must be gemini or off.")

    if config.ocr_max_pages < 0:
        raise RuntimeError("OCR_MAX_PAGES must be zero or greater.")


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
        qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
        qdrant_collection=os.getenv(
            "QDRANT_COLLECTION",
            DEFAULT_QDRANT_COLLECTION,
        ).strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip(),
        llm_provider=os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip().lower(),
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip(),
        translation_provider=os.getenv(
            "TRANSLATION_PROVIDER",
            DEFAULT_TRANSLATION_PROVIDER,
        ).strip().lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip(),
        ocr_provider=os.getenv("OCR_PROVIDER", DEFAULT_OCR_PROVIDER).strip().lower(),
        ocr_max_pages=_get_int("OCR_MAX_PAGES", DEFAULT_OCR_MAX_PAGES),
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
    LOGGER.info("Qdrant API key configured: %s", "yes" if config.qdrant_api_key else "no")
    LOGGER.info("Embedding model: %s", config.embedding_model)

    if config.llm_provider == "qwen" and not config.is_mock_llm:
        LOGGER.info(
            "LLM mode: Qwen vLLM mode using %s with model %s",
            config.llm_base_url,
            config.llm_model,
        )
    elif config.llm_provider == "gemini" and not config.is_mock_llm:
        LOGGER.info("LLM mode: Gemini using model %s", config.gemini_model)
    else:
        LOGGER.info("LLM mode: mock mode")

    if config.translation_provider == "gemini" and config.gemini_api_key:
        LOGGER.info("Nepali adaptation mode: Gemini using model %s", config.gemini_model)
    elif config.translation_provider == "openai" and config.openai_api_key:
        LOGGER.info("Nepali adaptation mode: OpenAI using model %s", config.openai_model)
    else:
        LOGGER.info("Nepali adaptation mode: mock fallback")

    if config.ocr_provider == "gemini" and config.gemini_api_key:
        page_label = "all" if config.ocr_max_pages == 0 else str(config.ocr_max_pages)
        LOGGER.info("PDF OCR mode: Gemini fallback enabled for %s pages", page_label)
    else:
        LOGGER.info("PDF OCR mode: off")


def _get_int(name: str, default: int) -> int:
    import os

    raw_value = os.getenv(name, str(default)).strip()

    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
