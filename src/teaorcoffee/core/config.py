from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = ""
    admin_password: str = Field(validation_alias="ADMIN_PASS")
    main_admin_name: str = Field(default="Vaibhav", validation_alias="MAIN_ADMIN_NAME")

    class Config:
        env_file = ".env"
        env_prefix = "TOC_"


settings = Settings()
