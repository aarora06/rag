import os
from dotenv import load_dotenv
import glob
from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from pypdf.errors import PdfReadError
from pydantic import BaseModel
from typing import List, Tuple

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Load the expected API key from environment variables
# In a production environment, manage this securely
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    # This should ideally not be reached if the environment variable is set during deployment
    print("Warning: API_KEY environment variable not set. API will not be protected.")
    # As a fallback for local testing or if auth is optional, you might set a default
    # API_KEY = "insecure_default_key_for_testing" # Use with caution!

# Load the OpenAI API key from environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

MODEL = "gpt-4o-mini"
db_name = "vector_db" # Directory to store the Chroma vector database

# --- Global Variables ---
# Global variables to hold the initialized components
conversation_chain_instance: ConversationalRetrievalChain | None = None
memory_instance: ConversationBufferMemory | None = None

# --- Helper Functions (from previous steps) ---

def load_and_chunk_documents(knowledge_base_path: str = "knowledge_base"):
    """
    Loads documents from the specified path, handles different file types,
    adds metadata, and splits them into chunks.
    """
    folders = glob.glob(os.path.join(knowledge_base_path, "*"))
    documents = []

    text_loader_kwargs = {'encoding': 'utf-8'}

    for folder in folders:
        doc_type = os.path.basename(folder)
        print(f"Loading documents from folder: {doc_type}")

        markdown_files = glob.glob(os.path.join(folder, "**/*.md"), recursive=True)
        pdf_files = glob.glob(os.path.join(folder, "**/*.pdf"), recursive=True)

        for md_file in markdown_files:
            loader = TextLoader(md_file, **text_loader_kwargs)
            documents.extend([doc for doc in loader.load()]) # Metadata will be added later

        for pdf_file in pdf_files:
            try:
                loader = PyPDFLoader(pdf_file)
                documents.extend([doc for doc in loader.load()]) # Metadata will be added later
            except PdfReadError:
                print(f"Skipping corrupted PDF file: {pdf_file}")

    # Add metadata after loading all documents
    processed_documents = []
    for doc in documents:
        # Extract doc_type from the folder name containing the source file
        source_dir = os.path.dirname(doc.metadata.get('source', ''))
        # Handle cases where source_dir might be empty or just "knowledge_base"
        if source_dir and source_dir != knowledge_base_path:
             doc_type = os.path.basename(source_dir)
        else:
             # Fallback or default doc_type if path structure is unexpected
             doc_type = "unknown" # Or handle as appropriate

        doc.metadata["doc_type"] = doc_type
        processed_documents.append(doc)


    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(processed_documents)

    # Remove PDF specific metadata after splitting
    for chunk in chunks:
        if chunk.metadata.get('source', '').lower().endswith('.pdf'):
            pdf_metadata_keys = ['producer', 'creator', 'creationdate', 'author', 'moddate', 'title', 'total_pages', 'page', 'page_label']
            for key in pdf_metadata_keys:
                if key in chunk.metadata:
                    del chunk.metadata[key]

    print(f"Total number of chunks: {len(chunks)}")
    if len(chunks) > 0:
      print ("First chunk data: " + str(chunks[0]))
      # Optional: print document types found
      print(f"Document types found in chunks: {set(c.metadata.get('doc_type', 'unknown') for c in chunks)}")


    return chunks

def initialize_vectorstore(chunks: list[Document], db_path: str = db_name):
    """
    Initializes or updates the Chroma vector store with the given chunks.
    Deletes existing collection before adding new ones.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, chunk_size=1000)

    if os.path.exists(db_path):
        try:
            # Initialize Chroma with the existing directory to perform operations like delete_collection
            # Ensure embedding_function is provided even for deleting
            existing_vectorstore = Chroma(persist_directory=db_path, embedding_function=embeddings)
            existing_vectorstore.delete_collection()
            print(f"Deleted existing collection in {db_path}")
        except Exception as e:
            print(f"Could not delete existing collection: {e}")
    else:
        # Ensure the directory exists if it wasn't already there for the existing_vectorstore check
        os.makedirs(db_path, exist_ok=True)


    vectorstore = Chroma(persist_directory=db_path, embedding_function=embeddings)

    # Determine an appropriate batch size for adding documents
    # This can be adjusted based on memory and network constraints
    batch_size = 50 # Increased batch size as an example

    total_chunks = len(chunks)
    print(f"Adding {total_chunks} chunks to vectorstore in batches of {batch_size}")

    if total_chunks > 0:
        # Langchain's add_documents handles batching internally, but explicit batching
        # can sometimes offer more control or be necessary depending on the vector store.
        # For Chroma, add_documents is efficient. Let's use it directly.
        # If explicit batching is needed:
        # for i in range(0, total_chunks, batch_size):
        #     batch_chunks = chunks[i:i + batch_size]
        #     print(f"Adding batch {i//batch_size + 1}/ {math.ceil(total_chunks/batch_size)} with {len(batch_chunks)} chunks")
        #     vectorstore.add_documents(documents=batch_chunks)

        # Using the standard add_documents approach
        vectorstore.add_documents(documents=chunks)


    print(f"Vectorstore created/updated in {db_path} with {vectorstore._collection.count()} documents")
    return vectorstore


def setup_rag_chain(vectorstore: Chroma):
    """
    Sets up the ConversationalRetrievalChain with the given vector store,
    LLM, and memory.
    """
    llm = ChatOpenAI(temperature=0.7, model_name=MODEL, openai_api_key=openai_api_key)
    # Use a new memory instance for each chat session if state is managed by the client
    # If using server-side state, memory_instance should be global and managed per user/session
    # For this stateless example relying on client-provided history, we'll use a simple buffer.
    # The memory instance passed to the chain during setup is for internal use by the chain
    # to format the prompt correctly with history provided in the 'chat_history' key of invoke().
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    retriever = vectorstore.as_retriever()
    conversation_chain = ConversationalRetrievalChain.from_llm(llm=llm, retriever=retriever, memory=memory)
    return conversation_chain, memory # Return memory instance for potential state management


# --- RAG Initialization ---

def reinitialize_rag_components():
    """
    Loads all documents from the knowledge base, re-initializes the vector store,
    and sets up the RAG chain. This is a complete refresh.
    """
    global conversation_chain_instance, memory_instance
    print("Starting RAG component re-initialization...")
    try:
        # Load and chunk documents
        document_chunks = load_and_chunk_documents()
        print(f"Loaded and chunked {len(document_chunks)} documents.")

        # Initialize or update the vector store
        vectorstore_instance = initialize_vectorstore(document_chunks)
        print("Vector store initialized.")

        # Setup the RAG chain
        conversation_chain_instance, memory_instance = setup_rag_chain(vectorstore_instance)
        print("RAG chain re-initialized successfully.")
        return True

    except Exception as e:
        print(f"Error during RAG component re-initialization: {e}")
        # Set instances to None to indicate failure, making the service unhealthy
        conversation_chain_instance = None
        memory_instance = None
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.
    """
    reinitialize_rag_components()
    yield
    # Clean up resources here if needed on shutdown
    print("Application shutting down.")

# Initialize the FastAPI app with the lifespan context manager
app = FastAPI(lifespan=lifespan)

# --- Authentication Dependency ---

# Define the API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key")

# Allow requests from your React app's origin
origins = [
    "http://localhost:3000",  # React dev server
    # Add more origins if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Allows your frontend origin
    allow_credentials=True,
    allow_methods=["*"],              # Allows all HTTP methods
    allow_headers=["*"],              # Allows all headers
)


# Define a dependency function to validate the API key
async def get_api_key(api_key: str = Depends(api_key_header)):
    # Check if API_KEY was loaded (i.e., env var was set)
    if API_KEY is None:
         # If API_KEY env var was not set, allow access but print warning
         # This makes auth optional if the env var is missing.
         # For strict auth, remove this if block and the check in __main__
         print("Warning: API_KEY environment variable not set. Authentication is bypassed.")
         return api_key # Allow access
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# --- Pydantic Models ---

class ChatRequest(BaseModel):
    question: str
    chat_history: List[Tuple[str, str]] = []

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for basic health check."""
    return {"message": "RAG API is running"}

@app.post("/chat/", dependencies=[Depends(get_api_key)])
async def chat_endpoint(chat_request: ChatRequest):
    """
    Handles incoming chat requests with error handling and API key authentication.
    It validates service availability and manages exceptions during the RAG chain process.
    Requires a valid 'X-API-Key' header.
    """
    # 1. Check if the RAG chain is initialized
    if not conversation_chain_instance:
         raise HTTPException(
            status_code=503,
            detail={"error": "The service is not ready to handle requests. Initialization failed."}
        )

    # 2. Wrap the call to the RAG chain in a try...except block
    try:
        # Clear and repopulate memory with the chat history from the request
        # This approach makes the API stateless regarding conversation history,
        # relying on the client to send the full history with each request.
        # If server-side state is desired, you would need to manage memory
        # per user/session, possibly using a database or cache.
        if memory_instance:
            memory_instance.chat_memory.clear()
            for question, answer in chat_request.chat_history:
                memory_instance.chat_memory.add_user_message(question)
                memory_instance.chat_memory.add_ai_message(answer)

        # Invoke the RAG chain with the new question
        # The conversation_chain uses the memory instance provided during its setup
        # and the 'chat_history' key in the invoke call to manage context.
        result = conversation_chain_instance.invoke({"question": chat_request.question})
        answer = result.get("answer", "Could not retrieve an answer.")

        # Append the new question and answer to the chat history for the response
        updated_chat_history = chat_request.chat_history + [(chat_request.question, answer)]

        return {"answer": answer, "chat_history": updated_chat_history}
    except Exception as e:
        # Log the error for debugging
        print(f"An error occurred during chat processing: {e}")
        # Return a generic error message to the user
        raise HTTPException(
            status_code=500,
            detail={"error": "An internal error occurred while processing your request."}
        )

@app.post("/upload/", dependencies=[Depends(get_api_key)])
async def upload_document(file: UploadFile = File(...)):
    """
    Uploads a document to the 'knowledge_base/products' directory and
    triggers a re-initialization of the vector database and RAG chain.
    This is a blocking operation and will rebuild the entire vector store.
    Requires a valid 'X-API-Key' header.
    """
    upload_folder = "knowledge_base/products"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, file.filename)

    try:
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    # Trigger re-initialization of the RAG chain in a thread pool to avoid
    # blocking the main asyncio event loop.
    print(f"File '{file.filename}' uploaded. Triggering vector DB update...")
    success = await run_in_threadpool(reinitialize_rag_components)

    if success:
        return {"message": f"File '{file.filename}' uploaded and vector DB updated successfully."}
    else:
        # The file was saved, but the DB update failed.
        # The server might be in a bad state.
        raise HTTPException(
            status_code=500,
            detail="File uploaded, but the service failed to update its knowledge base."
        )

# --- Main entry point (for local testing with uvicorn) ---
# This part is typically used for local development and not directly
# by production web servers like gunicorn or uvicorn run by a platform.
# They will import 'app' directly.
if __name__ == "__main__":
    import uvicorn
    # Ensure environment variables are set for local testing
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set the OPENAI_API_KEY environment variable for local testing.")
    if "API_KEY" not in os.environ:
        print("Please set the API_KEY environment variable for local testing if authentication is needed.")

    # Create the knowledge_base directory and add dummy files for testing if they don't exist
    if not os.path.exists("knowledge_base/products"):
        os.makedirs("knowledge_base/products", exist_ok=True)
        with open("knowledge_base/products/product_info.md", "w") as f:
            f.write("This is information about our products.")
    if not os.path.exists("knowledge_base/employees"):
         os.makedirs("knowledge_base/employees", exist_ok=True)
         with open("knowledge_base/employees/employee_list.md", "w") as f:
            f.write("This is information about our employees.")


    print("Starting uvicorn server...")
    # The lifespan context manager is automatically handled by uvicorn when app is passed
    uvicorn.run(app, host="0.0.0.0", port=8000)