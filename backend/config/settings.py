from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_API_KEY: str | None = None
    groq_api_key: str | None = None
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str | None = None
    aura_instanceid: str | None = None
    aura_instancename: str | None = None
    notion_api_key: str | None = None
    log_level: str | None = None
    log_file: str | None = None
    custom_password: str | None = None
    useranme: str | None = None   # (typo? maybe username?)

    class Config:
        env_file = ".env"


settings = Settings()