"""Production config — 12-Factor: all values from environment variables."""
import logging
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip())
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    use_mock_llm: bool = field(
        default_factory=lambda: os.getenv("USE_MOCK_LLM", "false").lower() == "true"
    )
    llm_fallback_mock: bool = field(
        default_factory=lambda: os.getenv("LLM_FALLBACK_MOCK", "true").lower() == "true"
    )

    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me").strip())
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "").strip())
    history_max_messages: int = field(
        default_factory=lambda: int(os.getenv("HISTORY_MAX_MESSAGES", "20"))
    )

    @property
    def openai_configured(self) -> bool:
        key = self.openai_api_key
        # OpenAI keys usually start with sk-; project keys may use sk-proj-
        return bool(key) and key.startswith("sk") and len(key) > 20

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production":
            if self.agent_api_key == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY must be set in production!")
        if self.use_mock_llm:
            logger.info(
                "USE_MOCK_LLM=true — mock LLM enabled (set to false on Render to use OpenAI)"
            )
        elif not self.openai_configured:
            if self.openai_api_key:
                logger.warning("OPENAI_API_KEY is set but looks invalid — using mock LLM")
            else:
                logger.warning("OPENAI_API_KEY not set — using mock LLM")
        return self


settings = Settings().validate()
