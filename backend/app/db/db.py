from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import config


def _engine_kwargs() -> dict:
    return {
        "pool_pre_ping": config.DB_POOL_PRE_PING,
        "echo": config.DB_ECHO,
        "pool_size": max(1, config.DB_POOL_SIZE),
        "max_overflow": max(0, config.DB_MAX_OVERFLOW),
        "pool_timeout": max(1, config.DB_POOL_TIMEOUT),
        "pool_recycle": max(30, config.DB_POOL_RECYCLE),
    }


engine = create_engine(config.DATABASE_URL, **_engine_kwargs())
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
