# Save this code into a file named main.py

import os
import glob
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile, Form
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from pypdf.errors import PdfReadError
import math
import numpy as np
from pydantic import BaseModel
from typing import List, Tuple, Dict
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.messages import HumanMessage, AIMessage
import shutil


# --- Configuration ---
# Load the expected API key from environment variables
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("Warning: API_KEY environment variable not set. API will not be protected.")

# Load the OpenAI API key from environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

MODEL = "gpt-4o-mini"
db_name = "vector_db" # Directory to store the Chroma vector database
knowledge_base_path = "knowledge_base" # Define knowledge base path

# --- Global Variables ---
# Global variables to hold the initialized components
retrievers: Dict[str, VectorStoreRetriever] = {}
llm_instance: ChatOpenAI | None = None

# --- Helper Functions ---

def load_and_chunk_documents(knowledge_base_path: str = knowledge_base_path):
    """
    Loads documents from the specified path, handles different file types,
    adds metadata, and splits them into chunks.
    Supports a three-level hierarchy (company, department, employee) directly
    under knowledge_base.
    Supports .md, .pdf, .docx, .pptx files.
    """
    documents = []

    text_loader_kwargs = {'encoding': 'utf-8'}

    # Walk through the knowledge base directory to find all files
    for root, dirs, files in os.walk(knowledge_base_path):
        # Determine the relative path from the knowledge_base_path
        relative_root = os.path.relpath(root, knowledge_base_path)

        # Filter out the vector database directory if it's within knowledge_base
        if relative_root.startswith(db_name) and relative_root != '.': # Ensure we don't skip the root if db_name is '.'
            continue

        # Extract hierarchy information from the relative path
        path_parts = relative_root.split(os.sep)

        # Handle cases where path_parts might be shorter than expected hierarchy levels
        # Filter out empty strings from split results in case of leading/trailing slashes or unusual paths
        cleaned_path_parts = [part for part in path_parts if part]

        company = cleaned_path_parts[0] if len(cleaned_path_parts) > 0 else "unknown_company"
        department = cleaned_path_parts[1] if len(cleaned_path_parts) > 1 else "unknown_department"
        employee = cleaned_path_parts[2] if len(cleaned_path_parts) > 2 else "unknown_employee"

        # If the current root is the knowledge base root itself and there are files there,
        # these are "general" documents, not part of the company hierarchy.
        if relative_root == '.' and files:
             doc_type = "general"
        # If the current root is part of the hierarchy
        elif company != "unknown_company":
             # Determine doc_type based on the highest available level in the hierarchy path
             if employee != "unknown_employee":
                 doc_type = f"{company}_{department}_{employee}"
             elif department != "unknown_department":
                 doc_type = f"{company}_{department}"
             else:
                 doc_type = company # Just company level

        else:
            # This case should ideally not be reached with the current walk and filter logic,
            # but as a fallback, mark as general.
            doc_type = "general"


        for file in files:
            file_path = os.path.join(root, file)

            # Skip hidden files or temporary files
            if file.startswith('.') or file.startswith('~$'):
                continue

            loader = None
            if file.lower().endswith('.md'):
                loader = TextLoader(file_path, **text_loader_kwargs)
            elif file.lower().endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file.lower().endswith('.docx'):
                 loader = Docx2txtLoader(file_path)
            elif file.lower().endswith('.pptx'):
                 loader = UnstructuredPowerPointLoader(file_path)


            if loader:
                try:
                    loaded_docs = loader.load()
                    for doc in loaded_docs:
                        doc.metadata["doc_type"] = doc_type
                        doc.metadata["company"] = company
                        doc.metadata["department"] = department
                        doc.metadata["employee"] = employee
                        documents.extend([doc])

                except PdfReadError:
                    print(f"Skipping corrupted PDF file: {file_path}")
                except Exception as e:
                     print(f"Error loading file {file_path}: {e}")
            else:
                 print(f"Skipping unsupported file type: {file_path}")


    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)

    # Remove PDF specific metadata after splitting if not needed for RAG
    for chunk in chunks:
        if chunk.metadata.get('source', '').lower().endswith('.pdf'):
            pdf_metadata_keys = ['producer', 'creator', 'creationdate', 'author', 'moddate', 'title', 'total_pages', 'page', 'page_label']
            for key in pdf_metadata_keys:
                if key in chunk.metadata:
                    del chunk.metadata[key]
        # Clean up any None values or 'unknown' if not part of the intended metadata structure
        # Only keep hierarchy metadata if doc_type is not 'general' and company is known
        if chunk.metadata.get('doc_type') == 'general' or chunk.metadata.get('company') == 'unknown_company':
             chunk.metadata.pop('company', None)
             chunk.metadata.pop('department', None)
             chunk.metadata.pop('employee', None)
        else:
             # Remove 'unknown' values if they exist for hierarchy levels that weren't present in the path
             if chunk.metadata.get('department') == 'unknown_department':
                  chunk.metadata.pop('department', None)
             if chunk.metadata.get('employee') == 'unknown_employee':
                  chunk.metadata.pop('employee', None)


        chunk.metadata = {k: v for k, v in chunk.metadata.items() if v is not None} # Final clean up of None values


    print(f"Total number of chunks: {len(chunks)}")
    if len(chunks) > 0:
      print ("First chunk data: " + str(chunks[0]))
      # Optional: print document types and hierarchy metadata found
      doc_types_found = set(c.metadata.get('doc_type', 'unknown') for c in chunks)
      print(f"Document types found in chunks: {doc_types_found}")
      print("Hierarchy metadata examples:")
      # Print examples of hierarchy metadata, focusing on different levels if possible
      example_count = 0
      for chunk in chunks:
           # Only print examples for hierarchical docs (where company is known)
           if chunk.metadata.get('company') != 'unknown_company':
               print(f"  DocType={chunk.metadata.get('doc_type')}, Company={chunk.metadata.get('company')}, Department={chunk.metadata.get('department')}, Employee={chunk.metadata.get('employee')}, Source={chunk.metadata.get('source')}")
               example_count += 1
               if example_count > 5: break # Print a few examples
      if example_count == 0:
          print("  No documents found with company hierarchy metadata.")


    return documents # Return full documents before splitting for potential alternative chunking


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
        os.makedirs(db_path, exist_ok=True)

    vectorstore = Chroma(persist_directory=db_path, embedding_function=embeddings)

    total_chunks = len(chunks)
    print(f"Adding {total_chunks} chunks to vectorstore.")

    if total_chunks > 0:
        vectorstore.add_documents(documents=chunks)

    print(f"Vectorstore created/updated in {db_path} with {vectorstore._collection.count()} documents")
    return vectorstore

def setup_retrievers(vectorstore: Chroma):
    """
    Sets up multiple retrievers filtered by hierarchy levels based on metadata presence.
    """
    # Ensure the vectorstore is not None
    if vectorstore is None:
        print("Vectorstore is not initialized. Cannot setup retrievers.")
        return {}

    base_search_kwargs = {'k': 3}

    # Create retrievers for different hierarchy levels based on metadata presence
    # These retrievers will filter documents based on whether specific metadata keys exist
    # and are not the 'unknown' placeholder values.
    retrievers = {
        # Retrieve documents where the employee metadata is present and not 'unknown'
        'employee_level': vectorstore.as_retriever(search_kwargs={**base_search_kwargs, 'filter': {'employee': {'$exists': True, '$ne': 'unknown_employee'}}}),
        # Retrieve documents where department metadata is present and not 'unknown'
        'department_level': vectorstore.as_retriever(search_kwargs={**base_search_kwargs, 'filter': {'department': {'$exists': True, '$ne': 'unknown_department'}}}),
        # Retrieve documents where company metadata is present and not 'unknown'
        'company_level': vectorstore.as_retriever(search_kwargs={**base_search_kwargs, 'filter': {'company': {'$exists': True, '$ne': 'unknown_company'}}}),
        # General retriever for documents without specific hierarchy (if applicable, e.g., directly under knowledge_base)
        'general': vectorstore.as_retriever(search_kwargs={**base_search_kwargs, 'filter': {'doc_type': 'general'}}),
    }

    # You might also want specific retrievers by exact metadata values if needed,
    # e.g., filtering by a specific company name 'CompanyA'.
    # This would typically be dynamic based on available companies/departments/employees.
    # Example: retriever for documents in a specific company 'CompanyA' within products
    # retrievers['products_CompanyA'] = vectorstore.as_retriever(search_kwargs={**base_search_kwargs, 'filter': {'doc_type': 'products', 'company': 'CompanyA'}})


    return retrievers


def setup_llm():
    """
    Sets up the ChatOpenAI language model.
    """
    llm = ChatOpenAI(temperature=0.7, model_name=MODEL, openai_api_key=openai_api_key)
    return llm


# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.
    Initializes RAG components (vectorstore, retrievers, LLM) on startup.
    """
    global retrievers, llm_instance
    print("Starting RAG component initialization...")
    vectorstore_instance = None
    try:
        # Load and chunk documents
        # Note: load_and_chunk_documents now returns full documents, not chunks directly
        documents = load_and_chunk_documents()

        # Split documents into chunks after loading
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        document_chunks = text_splitter.split_documents(documents)

        print(f"Loaded {len(documents)} documents and chunked into {len(document_chunks)} chunks.")

        # Initialize or update the vector store
        if document_chunks: # Only initialize vectorstore if there are chunks
             vectorstore_instance = initialize_vectorstore(document_chunks)
             print("Vector store initialized.")
        else:
             print("No documents loaded, skipping vector store initialization.")


        # Setup retrievers for different levels (even if vectorstore_instance is None)
        retrievers = setup_retrievers(vectorstore_instance)
        print("Retrievers setup.")

        # Setup the language model
        llm_instance = setup_llm()
        print("LLM initialized.")

    except Exception as e:
        print(f"Error during RAG component initialization: {e}")
        retrievers = {}
        llm_instance = None
        # Depending on the platform, you might want to raise the exception
        # to cause the service to fail health checks if initialization is critical.
        # raise e # Uncomment to fail startup on error

    yield
    # Clean up resources here if needed on shutdown
    print("Application shutting down.")

# Initialize the FastAPI app with the lifespan context manager
app = FastAPI(lifespan=lifespan)

# --- Authentication Dependency ---

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if API_KEY is None:
         print("Warning: API_KEY environment variable not set. Authentication is bypassed.")
         return api_key
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# --- Pydantic Models ---

class ChatRequest(BaseModel):
    question: str
    chat_history: List[Tuple[str, str]] = [] # (UserQuestion, AgentAnswer) tuples

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for basic health check."""
    return {"message": "RAG API is running"}

@app.post("/chat/", dependencies=[Depends(get_api_key)])
async def chat_endpoint(chat_request: ChatRequest):
    """
    Handles incoming chat requests, performs multi-level retrieval,
    and returns the RAG chain's response.
    """
    # 1. Check if components are initialized
    if not retrievers or not llm_instance:
         raise HTTPException(
            status_code=503,
            detail={"error": "The service is not ready to handle requests. Initialization failed."}
        )

    try:
        question = chat_request.question
        chat_history = chat_request.chat_history

        # 2. Perform multi-level retrieval
        retrieved_docs = []
        # Query relevant retrievers based on the desired hierarchy lookup strategy
        # Prioritize more specific levels first (employee > department > company)
        # Then include other top-level doc types and a general retriever
        retriever_keys_to_query = [
            'employee_level', # Employee level documents (from any company/department)
            'department_level', # Department level documents (from any company)
            'company_level', # Company level documents
            'general'    # Fallback general retriever
        ]

        for key in retriever_keys_to_query:
             if key in retrievers and retrievers[key] is not None:
                 retriever = retrievers[key]
                 print(f"Retrieving documents from {key} level...")
                 try:
                     docs = retriever.get_relevant_documents(question)
                     retrieved_docs.extend(docs)
                     print(f"Retrieved {len(docs)} documents from {key}.")
                 except Exception as retrieve_error:
                     print(f"Error retrieving from {key}: {retrieve_error}")
             else:
                 print(f"Retriever key '{key}' not found or is None.")


        # Remove duplicate documents based on page_content and source
        unique_docs = {}
        for doc in retrieved_docs:
            # Create a simple key based on content, source, and page (for PDFs) to identify duplicates
            # Use a tuple of immutable components
            doc_key = (doc.page_content, doc.metadata.get('source'), doc.metadata.get('page'))
            if doc_key not in unique_docs:
                unique_docs[doc_key] = doc

        final_retrieved_docs = list(unique_docs.values())
        print(f"Total unique retrieved documents: {len(final_retrieved_docs)}")

        # If no documents were retrieved, inform the user
        if not final_retrieved_docs:
             return {"answer": "I couldn't find any relevant information in the knowledge base.", "chat_history": chat_history + [(question, "I couldn't find any relevant information in the knowledge base.")]}


        # 3. Prepare the context for the LLM
        context_text = "\n\n".join([doc.page_content for doc in final_retrieved_docs])


        # 4. Prepare input for the LLM, including chat history and context
        # Langchain LLM.invoke expects a list of messages
        messages = []
        # Add previous chat history
        for user_q, ai_a in chat_history:
            messages.append(HumanMessage(content=user_q))
            messages.append(AIMessage(content=ai_a))

        # Add the context and the current question
        # The system message provides instructions and the retrieved context
        # It's often better to format the prompt using Langchain's prompt templates
        # for more complex scenarios,
        # but a simple f-string works here.
        system_message_content = "You are a helpful AI assistant. Use the following context to answer the user's question. If you don't know the answer from the context, say you don't know.\n\nContext:\n" + context_text

        messages.insert(0, {"role": "system", "content": system_message_content})
        messages.append({"role": "user", "content": question})

        print("Sending prompt to LLM...")
        # 5. Invoke the LLM with the prepared messages
        response = llm_instance.invoke(messages)

        answer = response.content

        # 6. Append the new question and answer to the chat history for the response
        updated_chat_history = chat_history + [(question, answer)]

        return {"answer": answer, "chat_history": updated_chat_history}

    except Exception as e:
        print(f"An error occurred during chat processing: {e}")
        # Return a generic error message to the user for security
        raise HTTPException(
            status_code=500,
            detail={"error": "An internal error occurred while processing your request."}
        )

# --- Document Upload Endpoint ---

@app.post("/upload/", dependencies=[Depends(get_api_key)])
async def upload_document(
    file: UploadFile = File(...),
    company: str = Form(...), # Company is now mandatory as top level
    department: str = Form(None), # Optional
    employee: str = Form(None), # Optional
    # level: str = Form(...) # Removed 'level' as a separate parameter, hierarchy defines path
):
    """
    Handles document uploads into the Company/Department/Employee hierarchy.
    Documents are saved under knowledge_base/company/department/employee/.
    """
    # Build the upload directory path based on the provided hierarchy
    # Start with knowledge_base and company
    upload_dir_parts = [knowledge_base_path, company]

    # Add department if provided
    if department:
        upload_dir_parts.append(department)
        # Add employee if provided (only if department is also provided)
        if employee:
            upload_dir_parts.append(employee)

    upload_dir = os.path.join(*upload_dir_parts)


    # Ensure the upload directory exists
    os.makedirs(upload_dir, exist_ok=True)

    # Define the destination path for the uploaded file
    file_location = os.path.join(upload_dir, file.filename)

    # Save the uploaded file
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print(f"Successfully uploaded {file.filename} to {file_location}")

        # In a real application, you would trigger a vector store update here.
        # This could be a background task or a separate API call.
        print("Document uploaded. Vector store needs to be updated to include this document.")

        return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. Vector store needs to be updated."}
    except Exception as e:
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")


# --- Main entry point (for local testing with uvicorn) ---
# This part is typically used for local development and not directly
# by production web servers like gunicorn or uvicorn run by a platform.
# They will import 'app' directly.
# if __name__ == "__main__":
#     import uvicorn
#     import asyncio # Import asyncio for local testing lifespan

#     # Ensure environment variables are set for local testing
#     if "OPENAI_API_KEY" not in os.environ:
#         print("Please set the OPENAI_API_KEY environment variable for local testing.")
#         # os.environ["OPENAI_API_KEY"] = "dummy_openai_key" # Uncomment for dummy key if needed
#         # raise ValueError("OPENAI_API_KEY environment variable not set for local testing.")

#     if "API_KEY" not in os.environ:
#         os.environ["API_KEY"] = "dummy_local_api_key"
#         print("Setting a dummy API_KEY 'dummy_local_api_key' for local testing.")
#         API_KEY = os.getenv("API_KEY")

#     # Create the knowledge_base directory and add dummy files for testing if they don't exist
#     knowledge_base_path = "knowledge_base"
#     # Updated to create the nested structure directly under knowledge_base
#     if not os.path.exists(os.path.join(knowledge_base_path, "company_a", "department_x", "employee_1")):
#         os.makedirs(os.path.join(knowledge_base_path, "company_a", "department_x", "employee_1"), exist_ok=True)
#         with open(os.path.join(knowledge_base_path, "company_a", "department_x", "employee_1", "doc_a_details.md"), "w") as f:
#             f.write("Details about document A, related to employee 1 in department X of company A.")
#     if not os.path.exists(os.path.join(knowledge_base_path, "company_a", "department_y", "employee_2")):
#          os.makedirs(os.path.join(knowledge_base_path, "company_a", "department_y", "employee_2"), exist_ok=True)
#          with open(os.path.join(knowledge_base_path, "company_a", "department_y", "employee_2", "doc_b_specs.md"), "w") as f:
#             f.write("Specifications for document B, handled by employee 2 in department Y of company A.")
#     if not os.path.exists(os.path.join(knowledge_base_path, "company_b", "department_z")):
#         os.makedirs(os.path.join(knowledge_base_path, "company_b", "department_z"), exist_ok=True)
#         with open(os.path.join(knowledge_base_path, "company_b", "department_z", "doc_c_overview.md"), "w") as f:
#             f.write("Overview of document C, managed by department Z of company B.")

#     # Example for documents directly at company level (if applicable)
#     if not os.path.exists(os.path.join(knowledge_base_path, "company_a", "company_policy.md")):
#         os.makedirs(os.path.join(knowledge_base_path, "company_a"), exist_ok=True)
#         with open(os.path.join(knowledge_base_path, "company_a", "company_policy.md"), "w") as f:
#             f.write("This is Company A's general policy.")

#     # Example for documents directly at department level (if applicable)
#     if not os.path.exists(os.path.join(knowledge_base_path, "company_a", "department_x", "dept_guidelines.md")):
#         os.makedirs(os.path.join(knowledge_base_path, "company_a", "department_x"), exist_ok=True)
#         with open(os.path.join(knowledge_base_path, "company_a", "department_x", "dept_guidelines.md"), "w") as f:
#             f.write("Guidelines for Company A, Department X.")


#     print("Starting uvicorn server...")
#     # The lifespan context manager is automatically handled by uvicorn when app is passed
#     # For local testing, ensure lifespan events run
#     # This requires running uvicorn directly, not through the notebook cell execution
#     # uvicorn.run(app, host="0.0.0.0", port=8000)