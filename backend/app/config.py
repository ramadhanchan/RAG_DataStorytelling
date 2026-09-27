from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_path: str = "data/sales.db"
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-pro"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
