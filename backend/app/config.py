"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings, SettingsConfigDict, field_validator
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # База данных
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    # Для генерации ключа: python -c "import secrets; print(secrets.token_hex(32))"

    KNOWN_WEAK_KEYS = (
        "secret",
        "change-me",
        "super-secret-key-change-in-production",
        "your-super-secret-key-change-in-production",
        "change-this-to-a-very-long-random-string-at-least-32-characters",
        "your-secret-key",
        "my-secret-key",
        "secret-key",
        "jwt-secret",
    )

    DEBUG: bool = False
    
    @field_validator("DEBUG")
    @classmethod
    def warn_debug(cls, v: bool) -> bool:
        if v:
            import warnings
            warnings.warn(
                "⚠️ DEBUG=True! Не используйте в продакшене. "
                "API-документация будет доступна публично.",
                stacklevel=2
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY слишком короткий!")
        if v in KNOWN_WEAK_KEYS:
            raise ValueError("SECRET_KEY содержит дефолтное значение!")
        return v
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Т-Банк API
    TBANK_API_URL: str = "https://business.tbank.ru/openapi"
    TBANK_TOKEN: str = Field(..., env="TBANK_TOKEN")
    
    # Курсы валют API
    CURRENCY_API_URL: str = "https://api.exchangerate-api.com/v4/latest"
    CURRENCY_API_KEY: str = Field(..., env="CURRENCY_API_KEY")
    
    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    # Приложение
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Получить настройки (кэшированные)"""
    return Settings()
