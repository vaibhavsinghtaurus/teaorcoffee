from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    mongodb_uri: str = ""
    allowed_names: List[str] = [
        "Vaibhav",
        "Sourabh",
        "Nitin",
        "Hemang",
        "Om",
        "Bhavya Shah",
        "Bhavya Prajapati",
        "Meet",
        "Gopal",
        "Sashikant",
        "Ranjeet",
        "Gaurav",
        "Jimish",
        "Devesh",
        "Pratik",
        "Abhi",
        "Abhishek",
    ]

    max_users: int = 20
    admin_password: str = Field(validation_alias="ADMIN_PASS")

    class Config:
        env_file = ".env"
        env_prefix = "TOC_"


settings = Settings()
