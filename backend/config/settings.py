from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM API Keys
    GOOGLE_API_KEY: str | None = None
    groq_api_key: str | None = None
    OPENAI_API_KEY: str | None = None
    
    # Neo4j Database
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str | None = None
    aura_instanceid: str | None = None
    aura_instancename: str | None = None
    
    # Vector Database
    chroma_persist_directory: str = "./chroma_db"
    
    # External Integrations
    notion_api_key: str | None = None
    
    # Logging
    log_level: str | None = None
    log_file: str | None = None
    
    # Legacy fields (keeping for compatibility)
    custom_password: str | None = None
    useranme: str | None = None   # (typo? maybe username?)

    class Config:
        env_file = ".env"


settings = Settings()