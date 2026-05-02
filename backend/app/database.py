"""
Модуль базы данных
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.DATABASE_URL,
    echo=_settings.DEBUG,   
    pool_pre_ping=True,     
    pool_size=20 if not _settings.DEBUG else 5,       
    max_overflow=30 if not _settings.DEBUG else 10,    
    pool_timeout=30,                                    
    pool_recycle=3600,                                  
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
