import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Load the expected API key from environment variables
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("Warning: API_KEY environment variable not set. API will not be protected.")

# Load the OpenAI API key from environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Create a .env file and add OPENAI_API_KEY='your-key'")

MODEL = "gpt-4o-mini"
db_name = "vector_db" # Directory to store the Chroma vector database
knowledge_base_path = "knowledge_base" # Define knowledge base path
