from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-32b:free"
    ollama_base_url: str = ""
    ollama_model: str = "qwen2.5:7b-instruct"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "appointments@kyronmedical.com"
    # Gmail SMTP (free alternative to SendGrid — no domain needed)
    smtp_email: str = ""
    smtp_password: str = ""       # Gmail App Password (NOT your Gmail password)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    app_base_url: str = "http://localhost:8000"
    database_url: str = "sqlite+aiosqlite:///./kyron.db"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

