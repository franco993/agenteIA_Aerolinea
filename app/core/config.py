# =====================================================================
# AIRLINE - CORE CONFIGURATION (app/core/config.py)
# Manejo de variables de entorno con Pydantic Settings BaseSettings
# =====================================================================
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SKY Airline - Agentic AI Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # API Keys & LLM Service Providers (Con valores por defecto para desarrollo)
    OPENAI_API_KEY: str = Field(default="sk-dummy-dev-key-openai")
    ANTHROPIC_API_KEY: str = Field(default="sk-dummy-dev-key-anthropic")
    DEFAULT_FAST_MODEL: str = "gpt-4o-mini"
    DEFAULT_ADVANCED_MODEL: str = "gpt-4o"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Bases de Datos Relacionales (MySQL) & Vector DB (Qdrant/PGvector)
    DATABASE_URL: str = Field(
        default="mysql+pymysql://sky_user:sky_pass@localhost:3306/sky_agent_db"
    )
    PGVECTOR_COLLECTION: str = "sky_legal_regulations"

    # Credenciales de Sabre GDS Integration (Con valores por defecto para desarrollo)
    SABRE_USERNAME: str = Field(default="SKY_AGENT_DEV")
    SABRE_PASSWORD: str = Field(default="SKY_PASS_DEV")
    SABRE_PCC: str = Field(default="H2SCL")
    SABRE_ENDPOINT: str = Field(default="https://webservices.sabre.com")

    # Configuración de Seguridad JWT & Autenticación (Con valores por defecto para desarrollo)
    JWT_SECRET_KEY: str = Field(default="sky-airline-secret-key-2026")
    SECRET_KEY: str = Field(default="sky-airline-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS & Observabilidad
    CORS_ORIGINS: List[str] = ["*"]
    LANGCHAIN_TRACING_V2: str = Field(default="true")
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = "sky-agentic-airlines"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()