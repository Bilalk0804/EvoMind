from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GOOGLE_API_KEY: str

    class Config:
        env_file = ".env"

try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(f"Error loading settings: {e}")