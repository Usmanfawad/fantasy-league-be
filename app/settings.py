from pydantic import field_validator
from pydantic_settings import BaseSettings

# Constants
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    All settings can be overridden using environment variables.
    """

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    ROOT_PATH: str = ""
    PROJECT_NAME: str = "FastAPI Boilerplate"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- Database Settings ---
    # Option A: provide a full SQLAlchemy URL directly
    # e.g. postgresql+psycopg2://postgres:123@localhost:5432/postgres
    DATABASE_URL: str | None = None

    # Option B: provide discrete parts (recommended for Docker/dev)
    DB_HOST: str | None = None
    DB_PORT: int | None = None
    DB_NAME: str | None = None
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None
    DB_SSLMODE: str | None = None  # e.g., "require" in some hosted envs

    # Security Settings
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8

    # CORS / Host Settings (as strings to avoid DotEnv JSON parsing issues)
    BACKEND_CORS_ORIGINS: str = "*"
    ALLOWED_HOSTS: str = "*"

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Performance / Proxy Settings
    ENABLE_GZIP: bool = True
    USE_PROXY_HEADERS: bool = False
    ENABLE_HTTPS_REDIRECT: bool = False

    # Database Pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # -------- Validators & helpers --------

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str | None) -> str:
        """Validate that SECRET_KEY is set and has minimum length."""
        if not v:
            raise ValueError("SECRET_KEY must be set")
        if len(v) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH}")
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def coalesce_database_url(cls, v: str | None, values: dict) -> str:
        """
        Build DATABASE_URL from discrete DB_* parts if not explicitly provided.
        Fallback to local SQLite if nothing else is configured.
        """
        if v and v.strip():
            return v.strip()

        # Pull pieces (may be None)
        host = values.get("DB_HOST")
        port = values.get("DB_PORT")
        name = values.get("DB_NAME")
        user = values.get("DB_USER")
        pwd = values.get("DB_PASSWORD")
        sslmode = values.get("DB_SSLMODE")

        if all([host, port, name, user, pwd]):
            # Compose a Postgres URL that SQLAlchemy understands.
            # Psycopg v2 driver name remains 'psycopg2' in the URL.
            base = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"
            if sslmode:
                base += f"?sslmode={sslmode}"
            return base

        # Final fallback: local SQLite (dev)
        return "sqlite:///./app.db"

    def parse_list(self, raw: str, default: list[str]) -> list[str]:
        """Parse comma-separated or JSON-list string into list of strings."""
        value = (raw or "").strip()
        if not value:
            return default
        if value == "*":
            return ["*"]
        if value.startswith("["):
            import json
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(i).strip() for i in parsed]
            except Exception:
                pass
        return [i.strip() for i in value.split(",") if i.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return self.parse_list(self.BACKEND_CORS_ORIGINS, default=["*"])

    @property
    def allowed_hosts(self) -> list[str]:
        return self.parse_list(self.ALLOWED_HOSTS, default=["*"])

    class Config:
        """Pydantic config class."""
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()

