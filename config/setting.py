from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("AI_MODEL")
EMBEDDING_MODEL =os.getenv('EMBEDDING_MODEL')