from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    sync_database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "studyflow"
    db_user: str = "postgres"
    db_password: str

    debug: bool = True
    app_version: str = "0.1.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
