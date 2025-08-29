# api.py
import os
import shutil
from fastapi import FastAPI, HTTPException, Depends, Header, File, UploadFile, Form
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Tuple, Dict
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.messages import HumanMessage, AIMessage
from langchain_chroma import Chroma
from langchain.text_splitter import CharacterTextSplitter
# Import necessary loaders for processing the uploaded file
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
from pypdf.errors import PdfReadError # Import PdfReadError for error handling


# Import from other modules in the application
from config import API_KEY, openai_api_key, MODEL, db_name, knowledge_base_path
from loading import load_and_chunk_documents, initialize_vectorstore
from retrieval import setup_retrievers, setup_llm # Assuming setup_llm is needed here


# --- Global Variables ---
# Global variables to hold the initialized components
retrievers: Dict[str, VectorStoreRetriever] = {}
llm_instance: object | None = None # Using object as a generic type for the LLM instance
# Need access to the vectorstore instance globally or pass it
vectorstore_instance: Chroma | None = None # Add global variable for vectorstore


# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.
    Initializes RAG components (vectorstore, retrievers, LLM) on startup.
    """
    global vectorstore_instances, retrievers, llm_instance
    print("Starting RAG component initialization...")
    vectorstore_instances = None # Will be a dict: {company: vectorstore}
    try:
        from loading import load_and_chunk_documents
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings
        import os
        # Find all companies in the knowledge base
        companies = set()
        for root, dirs, files in os.walk(knowledge_base_path):
            relative_root = os.path.relpath(root, knowledge_base_path)
            path_parts = [part for part in relative_root.split(os.sep) if part]
            if len(path_parts) > 0:
                companies.add(path_parts[0])
        print(f"[STARTUP DEBUG] Companies found: {companies}")
        vectorstore_instances_local = {}
        retrievers_local = {}
        for company in companies:
            if not company or company == '.' or company == '__pycache__':
                continue
            print(f"[STARTUP DEBUG] Processing company: {company}")
            # Only process documents for this company using the company filter
            document_chunks = load_and_chunk_documents(knowledge_base_path=knowledge_base_path, company_filter=company)
            print(f"[STARTUP DEBUG] Loaded {len(document_chunks)} chunks for company {company}.")
            
            # Verify no cross-company contamination
            companies_in_chunks = set(doc.metadata.get('company') for doc in document_chunks)
            if len(companies_in_chunks) > 1 or (len(companies_in_chunks) == 1 and company not in companies_in_chunks):
                print(f"[ERROR] Cross-company contamination detected for {company}. Companies found: {companies_in_chunks}")
                continue
            company_db_path = os.path.join("vector_db", company)
            embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, chunk_size=1000)
            if not os.path.exists(company_db_path):
                os.makedirs(company_db_path, exist_ok=True)
            vectorstore = Chroma(persist_directory=company_db_path, embedding_function=embeddings)
            if len(document_chunks) > 0:
                vectorstore.add_documents(documents=document_chunks)
            vectorstore_instances_local[company] = vectorstore
            retrievers_local[company] = setup_retrievers(vectorstore)
            print(f"[STARTUP DEBUG] Vectorstore for {company} initialized with {vectorstore._collection.count()} documents.")
        vectorstore_instances = vectorstore_instances_local
        retrievers = retrievers_local
        llm_instance = setup_llm()
        print("LLM initialized.")
    except Exception as e:
        print(f"Error during RAG component initialization: {e}")
        retrievers = {}
        llm_instance = None
        vectorstore_instances = None
    yield
    print("Application shutting down.")

# Initialize the FastAPI app with the lifespan context manager

app = FastAPI(lifespan=lifespan)

# --- CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    company: str
    department: str | None = None
    employee: str | None = None

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
        company = chat_request.company
        department = chat_request.department
        employee = chat_request.employee
        print(f"Chat request for company={company}, department={department}, employee={employee}")

        # Select the correct retrievers for the company
        print(f"[DEBUG] Available companies in retrievers: {list(retrievers.keys())}")
        if company not in retrievers:
            print(f"[ERROR] No retrievers found for company '{company}'.")
            raise HTTPException(status_code=404, detail=f"No vectorstore found for company '{company}'")
        company_retrievers = retrievers[company]
        print(f"[DEBUG] Using retrievers for company: {company}")

        # 2. Perform hierarchical retrieval - collect information from all relevant levels
        retrieved_docs = []
        level_docs = {}  # Track documents by level for better context organization
        
        # Determine which retrieval levels to use based on provided filters
        retriever_keys_to_query = []
        
        # Collect from most specific to most general levels
        if company and department and employee:
            retriever_keys_to_query.append('employee_level')
        if company and department:
            retriever_keys_to_query.append('department_level')
        if company:
            retriever_keys_to_query.append('company_level')
        
        # Add general level last for broader context
        retriever_keys_to_query.append('general')

        print(f"[DEBUG] Will query levels: {retriever_keys_to_query}")

        for key in retriever_keys_to_query:
            if key in company_retrievers and company_retrievers[key] is not None:
                retriever = company_retrievers[key]
                print(f"[DEBUG] Retrieving documents from {key} level for company '{company}'...")
                try:
                    filter_dict = {}
                    # Use a single hierarchy_key for filtering to satisfy ChromaDB's requirements
                    if key == "employee_level":
                        if not (company and department and employee):
                            print(f"[WARN] Missing hierarchy for employee_level retrieval. Skipping.")
                            continue
                        hierarchy_key = f"{company}|{department}|{employee}"
                        filter_dict = {"hierarchy_key": hierarchy_key}
                    elif key == "department_level":
                        if not (company and department):
                            print(f"[WARN] Missing hierarchy for department_level retrieval. Skipping.")
                            continue
                        hierarchy_key = f"{company}|{department}"
                        filter_dict = {"hierarchy_key": hierarchy_key}
                    elif key == "company_level":
                        if not company:
                            print(f"[WARN] Company not provided for company_level retrieval. Skipping.")
                            continue
                        hierarchy_key = f"{company}"
                        filter_dict = {"hierarchy_key": hierarchy_key}
                    
                    print(f"[DEBUG] Using filter for {key}: {filter_dict if filter_dict else 'No filter (general)'}")
                    
                    if key == "general":
                        # For general level, still filter by company to prevent cross-company contamination
                        if company:
                            filter_dict = {"company": company}
                            docs = retriever.get_relevant_documents(question, filter=filter_dict)
                        else:
                            docs = retriever.get_relevant_documents(question)
                    else:
                        docs = retriever.get_relevant_documents(question, filter=filter_dict)
                    
                    print(f"[DEBUG] Retrieved {len(docs)} documents from {key} for company '{company}'.")
                    
                    # Store documents by level for better organization
                    if docs:
                        level_docs[key] = docs
                        retrieved_docs.extend(docs)
                        
                except Exception as retrieve_error:
                    print(f"Error retrieving from {key}: {retrieve_error}")
            else:
                print(f"Retriever key '{key}' not found or is None for company '{company}'. Skipping retrieval for this level.")


        # Remove duplicate documents based on page_content and source
        unique_docs = {}
        for doc in retrieved_docs:
            # Create a simple key based on content, source, and page (for PDFs) to identify duplicates
            # Use a tuple of immutable components. Also include relevant metadata in the key.
            # Including source and page helps differentiate same content from different files/pages.
            doc_key = (doc.page_content, doc.metadata.get('source'), doc.metadata.get('page'),
                       doc.metadata.get('company'), doc.metadata.get('department'), doc.metadata.get('employee'))

            # Add the document if the key is not already in the unique_docs dictionary
            if doc_key not in unique_docs:
                unique_docs[doc_key] = doc

        final_retrieved_docs = list(unique_docs.values())
        print(f"Total unique retrieved documents: {len(final_retrieved_docs)}")

        # If no documents were retrieved, inform the user
        if not final_retrieved_docs:
             return {"answer": "I couldn't find any relevant information in the knowledge base.", "chat_history": chat_history + [(question, "I couldn't find any relevant information in the knowledge base.")]}


        # 3. Prepare the context for the LLM with hierarchical organization
        context_sections = []
        
        # Add context from each level, organized by hierarchy
        if level_docs:
            print(f"[DEBUG] Organizing context by levels: {list(level_docs.keys())}")
            
            # Employee level (most specific)
            if 'employee_level' in level_docs and level_docs['employee_level']:
                employee_content = "\n\n".join([doc.page_content for doc in level_docs['employee_level']])
                context_sections.append(f"EMPLOYEE-SPECIFIC INFORMATION:\n{employee_content}")
                print(f"[DEBUG] Added {len(level_docs['employee_level'])} employee-level documents to context")
            
            # Department level
            if 'department_level' in level_docs and level_docs['department_level']:
                department_content = "\n\n".join([doc.page_content for doc in level_docs['department_level']])
                context_sections.append(f"DEPARTMENT-LEVEL INFORMATION:\n{department_content}")
                print(f"[DEBUG] Added {len(level_docs['department_level'])} department-level documents to context")
            
            # Company level
            if 'company_level' in level_docs and level_docs['company_level']:
                company_content = "\n\n".join([doc.page_content for doc in level_docs['company_level']])
                context_sections.append(f"COMPANY-LEVEL INFORMATION:\n{company_content}")
                print(f"[DEBUG] Added {len(level_docs['company_level'])} company-level documents to context")
            
            # General level (broadest)
            if 'general' in level_docs and level_docs['general']:
                general_content = "\n\n".join([doc.page_content for doc in level_docs['general']])
                context_sections.append(f"GENERAL COMPANY INFORMATION:\n{general_content}")
                print(f"[DEBUG] Added {len(level_docs['general'])} general-level documents to context")
        
        # Combine all context sections
        context_text = "\n\n" + "\n\n".join(context_sections) if context_sections else ""
        
        print(f"[DEBUG] Final context organized into {len(context_sections)} sections")


        # 4. Prepare input for the LLM, including chat history and context
        # Langchain LLM.invoke expects a list of messages
        messages = []
        # Add previous chat history as HumanMessage and AIMessage pairs
        for user_q, ai_a in chat_history:
            messages.append(HumanMessage(content=user_q))
            messages.append(AIMessage(content=ai_a))

        # Add the context and the current question
        # The system message provides instructions and the retrieved context
        # It's often better to format the prompt using Langchain's prompt templates
        # for more complex scenarios, but a simple f-string works here.
        system_message_content = f"""You are a helpful AI assistant for {company}. Use the following hierarchical context to answer the user's question. 

The context is organized by levels of specificity:
- EMPLOYEE-SPECIFIC INFORMATION: Most relevant to the specific employee
- DEPARTMENT-LEVEL INFORMATION: Relevant to the department
- COMPANY-LEVEL INFORMATION: General company information
- GENERAL COMPANY INFORMATION: Broad company context

Prioritize information from more specific levels (employee > department > company > general) when available. 
If you don't know the answer from the context, say you don't know.

Context:{context_text}"""

        # Insert the system message at the beginning of the messages list
        messages.insert(0, {"role": "system", "content": system_message_content})
        # Add the user's current question
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
    level: str = Form(...) # Keep level for clarity, though hierarchy defines path
):
    """
    Handles document uploads into the Company/Department/Employee hierarchy.
    Documents are saved under knowledge_base/company/department/employee/.
    The 'level' parameter indicates the intended level of the document
    (company, department, or employee) for validation.
    """
    # Validate hierarchy based on provided level
    if level not in ["company", "department", "employee"]:
         raise HTTPException(status_code=400, detail="Invalid level specified. Must be 'company', 'department', or 'employee'.")

    if level == "department" and not company:
         raise HTTPException(status_code=400, detail="Company must be provided for 'department' level documents.")

    if level == "employee" and (not company or not department):
         raise HTTPException(status_code=400, detail="Company and Department must be provided for 'employee' level documents.")


    # Build the upload directory path based on the provided hierarchy
    # Start with knowledge_base and company
    upload_dir_parts = [knowledge_base_path, company]

    # Add department if provided and relevant for the level
    if department and level in ["department", "employee"]:
        upload_dir_parts.append(department)
        # Add employee if provided and relevant for the level
        if employee and level == "employee":
            upload_dir_parts.append(employee)
        elif employee and level == "department":
             # Allow employee for department level uploads if they are the subject, but not a subfolder
             # However, the current structure assumes employee is a subfolder of department.
             # Let's stick to the strict hierarchy for now based on the folder structure.
             if employee: # If employee is provided for department level
                  raise HTTPException(status_code=400, detail="Employee should not be provided for 'department' level documents based on the directory structure.")
        elif employee and level == "company":
             if employee: # If employee is provided for company level
                  raise HTTPException(status_code=400, detail="Employee should not be provided for 'company' level documents based on the directory structure.")

    elif department and level == "company":
         if department: # If department is provided for company level
              raise HTTPException(status_code=400, detail="Department should not be provided for 'company' level documents based on the directory structure.")

    # Handle the case where department is None but employee is provided (invalid hierarchy)
    if employee and not department:
         raise HTTPException(status_code=400, detail="Department must be provided if Employee is provided.")


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

        # --- Load, Chunk, and Add to Vector Store ---
        # 1. Load the newly saved file
        loader = None
        if file_location.lower().endswith('.md') or file_location.lower().endswith('.txt'):
            loader = TextLoader(file_location, encoding='utf-8') # Reuse text_loader_kwargs logic
        elif file_location.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_location)
        elif file_location.lower().endswith('.docx'):
             loader = Docx2txtLoader(file_location)
        elif file_location.lower().endswith('.pptx'):
             loader = UnstructuredPowerPointLoader(file_location)

        if not loader:
             print(f"Unsupported file type for vectorization: {file.filename}. File saved but not added to vector store.")
             return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. File type unsupported for vectorization."}

        try:
            loaded_docs = loader.load()
            if not loaded_docs:
                 print(f"No content loaded from {file.filename}. Skipping vectorization.")
                 return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. No content loaded for vectorization."}

            # 2. Add metadata based on upload parameters
            # Determine doc_type based on the level parameter provided
            if level == "employee":
                doc_type = f"{company}_{department}_{employee}"
            elif level == "department":
                doc_type = f"{company}_{department}"
            elif level == "company":
                doc_type = company
            else: # Should not happen due to validation, but as a fallback
                doc_type = "general"

            for doc in loaded_docs:
                # Always set company (mandatory, never None)
                doc.metadata["company"] = company
                # Only set department if provided and not None
                if department is not None:
                    doc.metadata["department"] = department
                else:
                    doc.metadata.pop("department", None)
                # Only set employee if provided and not None
                if employee is not None:
                    doc.metadata["employee"] = employee
                else:
                    doc.metadata.pop("employee", None)
                # Set doc_type for reference (optional, not used in filtering)
                doc.metadata["doc_type"] = doc_type

                # Set hierarchy_key for filtering (matches retrieval logic)
                if level == "employee":
                    doc.metadata["hierarchy_key"] = f"{company}|{department}|{employee}"
                elif level == "department":
                    doc.metadata["hierarchy_key"] = f"{company}|{department}"
                elif level == "company":
                    doc.metadata["hierarchy_key"] = f"{company}"

                # Clean up PDF-specific metadata if present
                if doc.metadata.get('source', '').lower().endswith('.pdf'):
                    pdf_metadata_keys = ['producer', 'creator', 'creationdate', 'author', 'moddate', 'title', 'total_pages', 'page', 'page_label']
                    for key in pdf_metadata_keys:
                        if key in doc.metadata:
                            del doc.metadata[key]
                # Clean up any None values (shouldn't be needed, but for safety)
                doc.metadata = {k: v for k, v in doc.metadata.items() if v is not None}


            # 3. Chunk the loaded document(s)
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            new_chunks = text_splitter.split_documents(loaded_docs)
            print(f"Chunked uploaded document into {len(new_chunks)} chunks.")

            # Propagate hierarchy_key to all chunks (in case splitter drops it)
            for chunk in new_chunks:
                # Always set hierarchy_key based on the level
                if level == "employee":
                    chunk.metadata["hierarchy_key"] = f"{company}|{department}|{employee}"
                elif level == "department":
                    chunk.metadata["hierarchy_key"] = f"{company}|{department}"
                elif level == "company":
                    chunk.metadata["hierarchy_key"] = f"{company}"
                
                # Ensure all required metadata is set
                chunk.metadata["company"] = company
                if department is not None:
                    chunk.metadata["department"] = department
                if employee is not None:
                    chunk.metadata["employee"] = employee

            if not new_chunks:
                 print(f"No chunks created from {file.filename}. Skipping vectorization.")
                 return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. No chunks created for vectorization."}


            # 4. Add the new chunks to the existing vector store
            global vectorstore_instances, retrievers
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings
            # Ensure vectorstore_instances is a dict
            if vectorstore_instances is None:
                vectorstore_instances = {}
            if retrievers is None:
                retrievers = {}
            # Path for this company's vector DB
            company_db_path = os.path.join("vector_db", company)
            # Create embeddings
            embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, chunk_size=1000)
            # Always re-instantiate the vectorstore for this company to avoid ChromaDB instance reuse issues
            if not os.path.exists(company_db_path):
                os.makedirs(company_db_path, exist_ok=True)
            vectorstore = Chroma(persist_directory=company_db_path, embedding_function=embeddings)
            vectorstore.add_documents(documents=new_chunks)
            vectorstore_instances[company] = vectorstore
            retrievers[company] = setup_retrievers(vectorstore)
            print(f"(Re)initialized vectorstore for company: {company} and added {len(new_chunks)} chunks.")


            # 5. Update the success message
            return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir} and added to vector store."}

        except PdfReadError:
             print(f"Skipping corrupted PDF file {file.filename} during vectorization.")
             return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. Corrupted PDF, not added to vector store."}
        except Exception as vectorization_error:
             print(f"Error processing file for vectorization {file.filename}: {vectorization_error}")
             return {"info": f"file '{file.filename}' uploaded successfully to {upload_dir}. Error during vectorization: {vectorization_error}"}


    except Exception as upload_error:
        print(f"Error uploading file: {upload_error}")
        raise HTTPException(status_code=500, detail=f"Could not upload file: {upload_error}")