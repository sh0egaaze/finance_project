"""Модуль конфигурации приложения"""
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
    # Секрет для генерации ключей: python -c "import secrets; print(secrets.token_hex(32))"

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

    PUBLIC_BASE_URL: str | None = None

    DEBUG: bool = False
    
    @field_validator("DEBUG")
    @classmethod
    def warn_debug(cls, v: bool) -> bool:
        if v:
            import warnings
            warnings.warn(
                "⚠️ DEBUG=True! Не используйте в продакшене. "
                "API-документация будет доступна по пути /docs.",
                stacklevel=2
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY недостаточно длинный!")
        if v in cls.KNOWN_WEAK_KEYS:
            raise ValueError("SECRET_KEY находится в списке небезопасных ключей!")
        if "сгенерируйте" in v.lower() or "generate" in v.lower() or v.startswith("<"):
            raise ValueError(
                "SECRET_KEY не был установлен! Сгенерируйте настоящий ключ: "
                "python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        return v
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Т-Банк API
    TBANK_API_URL: str = "https://sandbox-invest-public-api.tinkoff.ru/rest"
    TBANK_TOKEN: str = Field(..., env="TBANK_TOKEN")
    
    # Курсы валют API
    CURRENCY_API_URL: str = "https://api.exchangerate-api.com/v4/latest"
    CURRENCY_API_KEY: str = Field("", env="CURRENCY_API_KEY")
    
    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    @field_validator("SMTP_USER")
    @classmethod
    def validate_smtp_user(cls, v: str) -> str:
        if not v:
            import warnings
            warnings.warn(
                "⚠️ SMTP_USER не задан! Email-уведомления не будут работать. "
                "Укажите SMTP_USER, SMTP_PASSWORD и EMAIL_FROM в .env для production.",
                stacklevel=2
            )
        return v
    
    # Ключи шифрования банковских токенов (ОТДЕЛЬНО ОТ JWT!)
    TBANK_ENCRYPTION_KEY: str = Field(..., env="TBANK_ENCRYPTION_KEY")

    @field_validator("TBANK_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "TBANK_ENCRYPTION_KEY должен быть установлен и содержать минимум 32 символа! "
                "Сгенерируйте: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        return v
        
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
    """Загрузка настроек (кэшируется автоматически)"""
    return Settings()