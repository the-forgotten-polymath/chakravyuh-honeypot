from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
load_dotenv()



class Settings(BaseSettings):
    """Application settings"""
    # GEMINI API KEY
    

    # API Configuration
    api_key: str = "default-api-key-change-me"
    api_key_header: str = "X-API-Key"

 # ✅ ADD THIS LINE (CRITICAL)
    google_api_key: Optional[str] = None

    # Application
    app_title: str = "Agentic Scam Honeypot API"
    app_version: str = "0.1.0"
    app_description: str = "Backend REST API for scam detection and intelligence gathering"

    # Session Management
    max_messages_per_session: int = 20
    session_timeout_seconds: int = 3600
    min_messages_for_callback: int = 3

    # Scam Detection
    scam_confidence_threshold: float = 0.6

    # Callback Configuration
    callback_url: Optional[str] = None
    callback_timeout: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
