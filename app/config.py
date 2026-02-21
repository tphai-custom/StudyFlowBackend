from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    sync_database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "studyflowdb"
    db_user: str = "postgres"
    db_password: str

    debug: bool = True
    app_version: str = "0.1.0"

    jwt_secret_key: str = "studyflow-super-secret-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
