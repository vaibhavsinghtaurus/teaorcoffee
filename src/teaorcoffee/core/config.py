from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "TOC_"


settings = Settings()
