import os
from dataclasses import dataclass


@dataclass
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./campus_connect.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


settings = Settings()
