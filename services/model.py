from langchain.chat_models import init_chat_model
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config.model import ModelConfig

config = ModelConfig()





model = init_chat_model(
    model=config.model,
    model_provider=config.model_provider,
    api_key=config.api_key,
    temperature=config.temperature,
)
embedding = GoogleGenerativeAIEmbeddings(
    model=config.embedding,
    api_key=config.api_key,
    model_provider=config.model_provider,
)