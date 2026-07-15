from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os
from config.model import ModelConfig

config = ModelConfig()





model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=config.api_key,
)
embedding = GoogleGenerativeAIEmbeddings(
    model=config.embedding,
    api_key=config.api_key,
    model_provider=config.model_provider,
)



os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
modelGorq = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.0,
    max_retries=2,
    # other params...
)