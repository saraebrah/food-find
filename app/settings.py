from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_maps_api_key: SecretStr
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.6-flash"
