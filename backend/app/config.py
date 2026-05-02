"""
Модуль конфигурации приложения
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache
from typing import List, ClassVar


class Settings(BaseSettings):
    """Настройки для конфигурации приложения"""
    
    # База данных
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    # Для генерации ключа: python -c "import secrets; print(secrets.token_hex(32))"

    KNOWN_WEAK_KEYS: ClassVar[tuple] = (
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
                "API-документация будет доступна по адресу /docs.",
                stacklevel=2
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY недостаточно длинный!")
        if v in cls.KNOWN_WEAK_KEYS:
            raise ValueError("SECRET_KEY обнаружен в нежелательных списках!")
        return v
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Тинькофф API
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
    
    # Ключ шифрования банковских токенов (ОТДЕЛЬНЫЙ от JWT!)
    TBANK_ENCRYPTION_KEY: str = Field("", env="TBANK_ENCRYPTION_KEY")
    
    # Происхождение
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
    """Возвращает настройки (кэшированный синглтон)"""
    return Settings()
