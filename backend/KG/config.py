"""
Configuration management for Knowledge Graph RAG system.
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Knowledge Graph RAG system."""
    
    def __init__(self):
        self.groq_api_key = self._get_env_var("GROQ_API_KEY")
        self.neo4j_url = self._get_env_var("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_username = self._get_env_var("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = self._get_env_var("NEO4J_PASSWORD")
        self.log_level = self._get_env_var("LOG_LEVEL", "INFO")
        self.log_file = self._get_env_var("LOG_FILE", "kg_rag.log")
        
        # Validate required configurations
        self._validate_config()
    
    def _get_env_var(self, key: str, default: Optional[str] = None) -> str:
        """Get environment variable with optional default value."""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Environment variable {key} is required but not set")
        return value
    
    def _validate_config(self):
        """Validate that all required configuration values are present."""
        required_vars = {
            "GROQ_API_KEY": self.groq_api_key,
            "NEO4J_PASSWORD": self.neo4j_password
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please check your .env file or set these environment variables."
            )
    
    def __str__(self):
        """String representation of config (without sensitive data)."""
        return (
            f"Config(\n"
            f"  neo4j_url={self.neo4j_url},\n"
            f"  neo4j_username={self.neo4j_username},\n"
            f"  log_level={self.log_level},\n"
            f"  log_file={self.log_file}\n"
            f")"
        )

# Global config instance
config = Config()
