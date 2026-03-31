from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Indie Game API"


settings = Settings()
