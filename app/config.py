# app/config.py
# This module defines application configuration using Pydantic's BaseSettings.
# It loads environment variables from a .env file and provides defaults.

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/order_service_db"
    APP_NAME: str = "YouTech Store"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
