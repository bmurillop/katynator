from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — constructed by docker-compose; set manually for local dev.
    database_url: str

    # Auth
    secret_key: str
    admin_email: str = ""
    admin_password: str = ""
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 7

    # IMAP
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_interval_minutes: int = 5

    # AI provider
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    claude_api_key: str = ""
    lmstudio_base_url: str = "http://host.docker.internal:1234/v1"
    lmstudio_model: str = ""


settings = Settings()
