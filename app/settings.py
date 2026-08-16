from typing import Optional
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class DatabaseSettings(BaseSettings):
    HOST: str = Field(alias="DB_HOST")
    PORT: int = Field(default=5432, alias="DB_PORT")
    NAME: str = Field(alias="DB_NAME")
    USER: str = Field(alias="DB_USER")
    PASSWORD: SecretStr = Field(alias="DB_PASSWORD")

    @computed_field
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.USER}:"
            f"{self.PASSWORD.get_secret_value()}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )


class ProxySettings(BaseSettings):
    ENABLED: bool = Field(default=False, alias="PROXY_ENABLED")
    URL: str = Field(default="socks5://xray:10808", alias="PROXY_URL")


class OpenAISettings(BaseSettings):
    API_KEY: Optional[SecretStr] = Field(default=None, alias="OPENAI_API_KEY")
    DEFAULT_MODEL: str = Field(default="gpt-4o-mini", alias="OPENAI_DEFAULT_MODEL")
    BASE_URL: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")


class AnthropicSettings(BaseSettings):
    API_KEY: Optional[SecretStr] = Field(default=None, alias="ANTHROPIC_API_KEY")
    DEFAULT_MODEL: str = Field(default="claude-3-5-haiku-20241022", alias="ANTHROPIC_DEFAULT_MODEL")
    BASE_URL: str = Field(default="https://api.anthropic.com/v1", alias="ANTHROPIC_BASE_URL")


class GeminiSettings(BaseSettings):
    API_KEY: Optional[SecretStr] = Field(default=None, alias="GEMINI_API_KEY")
    DEFAULT_MODEL: str = Field(default="gemini-2.5-flash", alias="GEMINI_DEFAULT_MODEL")
    BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        alias="GEMINI_BASE_URL",
    )


class Settings(BaseSettings):
    SERVICE_HOST: str = Field(default="0.0.0.0")
    SERVICE_PORT: int = Field(default=8100)
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    REQUEST_TIMEOUT_SECONDS: int = Field(default=60)
    STREAM_TIMEOUT_SECONDS: int = Field(default=120)

    REDIS_URL: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    RATE_LIMIT_PER_MINUTE: int = Field(default=5, alias="RATE_LIMIT_PER_MINUTE")

    DATABASE: DatabaseSettings = Field(default_factory=DatabaseSettings)
    PROXY: ProxySettings = Field(default_factory=ProxySettings)
    OPENAI: OpenAISettings = Field(default_factory=OpenAISettings)
    ANTHROPIC: AnthropicSettings = Field(default_factory=AnthropicSettings)
    GEMINI: GeminiSettings = Field(default_factory=GeminiSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
