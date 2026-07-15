from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os
from config.model import ModelConfig
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
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

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
openai_embedding = OpenAIEmbeddings(
    model="text-embedding-3-large"
    # With the `text-embedding-3` class
    # of models, you can specify the size
    # of the embeddings you want returned.
    # dimensions=1024
)
openai_model =  ChatOpenAI(
    model="gpt-5-pro",
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # api_key="...",
    # base_url="...",
    # organization="...",
    # other params...
)

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
modelGorq = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.0,
    max_retries=2,
    # other params...
)
