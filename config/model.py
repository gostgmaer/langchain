from dataclasses import dataclass

from config.setting import API_KEY, EMBEDDING_MODEL, MODEL


@dataclass
class ModelConfig:
    model: str = MODEL
    embedding:str=EMBEDDING_MODEL
    model_provider: str = "google_genai"
    api_key: str = API_KEY
    temperature: float = 0.1
