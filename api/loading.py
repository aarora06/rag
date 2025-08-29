# loading.py
import os
import glob
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredPowerPointLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from pypdf.errors import PdfReadError
from typing import List, Dict

# Import configuration from config.py
from config import db_name, knowledge_base_path, openai_api_key

def load_and_chunk_documents(knowledge_base_path: str = knowledge_base_path, company_filter: str = None):
    """
    Loads documents from the specified path, handles different file types,
    adds metadata, and splits them into chunks.
    Supports a three-level hierarchy (company, department, employee) directly
    under knowledge_base.
    Supports .md, .pdf, .docx, .pptx files.
    
    Args:
        knowledge_base_path: Path to the knowledge base directory
        company_filter: If provided, only load documents for this specific company
    """
    documents = []

    text_loader_kwargs = {'encoding': 'utf-8'}

    # Only process documents for a single company if specified
    def process_company(company_name=None):
        docs = []
        for root, dirs, files in os.walk(knowledge_base_path):
            relative_root = os.path.relpath(root, knowledge_base_path)
            path_parts = [part for part in relative_root.split(os.sep) if part]
            company = path_parts[0] if len(path_parts) > 0 else "unknown_company"
            if company_name and company != company_name:
                continue
            department = path_parts[1] if len(path_parts) > 1 else "unknown_department"
            employee = path_parts[2] if len(path_parts) > 2 else "unknown_employee"
            if employee != "unknown_employee":
                doc_type = f"{company}_{department}_{employee}"
            elif department != "unknown_department":
                doc_type = f"{company}_{department}"
            elif company != "unknown_company":
                doc_type = company
            else:
                doc_type = "general"
            for file in files:
                file_path = os.path.join(root, file)
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
                            if employee != "unknown_employee":
                                doc.metadata["hierarchy_key"] = f"{company}|{department}|{employee}"
                            elif department != "unknown_department":
                                doc.metadata["hierarchy_key"] = f"{company}|{department}"
                            elif company != "unknown_company":
                                doc.metadata["hierarchy_key"] = f"{company}"
                            docs.append(doc)
                    except PdfReadError:
                        print(f"Skipping corrupted PDF file: {file_path}")
                    except Exception as e:
                        print(f"Error loading file {file_path}: {e}")
                else:
                    print(f"Skipping unsupported file type: {file_path}")
        return docs

    # Process documents based on company filter
    if company_filter:
        print(f"[LOADING] Loading documents for company: {company_filter}")
        documents = process_company(company_filter)
    else:
        print(f"[LOADING] Loading documents for all companies")
        documents = process_company(None)


    # --- Chunking ---
    # Split documents into chunks after loading all documents
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)

    # Remove PDF specific metadata after splitting if not needed for RAG
    for chunk in chunks:
        if chunk.metadata.get('source', '').lower().endswith('.pdf'):
            pdf_metadata_keys = ['producer', 'creator', 'creationdate', 'author', 'moddate', 'title', 'total_pages', 'page', 'page_label']
            for key in pdf_metadata_keys:
                if key in chunk.metadata:
                    del chunk.metadata[key]
        # Clean up 'unknown' values if they exist for hierarchy levels that weren't present in the path
        if chunk.metadata.get('company') == 'unknown_company':
             chunk.metadata.pop('company', None)
             chunk.metadata.pop('department', None) # Also remove department/employee if company is unknown
             chunk.metadata.pop('employee', None)
        else: # If company is known, clean up lower levels if they are unknown
             if chunk.metadata.get('department') == 'unknown_department':
                  chunk.metadata.pop('department', None)
                  chunk.metadata.pop('employee', None) # Also remove employee if department is unknown
             elif chunk.metadata.get('employee') == 'unknown_employee':
                  chunk.metadata.pop('employee', None)
        
        # Ensure hierarchy_key is always set if we have company information
        if chunk.metadata.get('company') and not chunk.metadata.get('hierarchy_key'):
            company = chunk.metadata.get('company')
            department = chunk.metadata.get('department')
            employee = chunk.metadata.get('employee')
            
            if employee:
                chunk.metadata["hierarchy_key"] = f"{company}|{department}|{employee}"
            elif department:
                chunk.metadata["hierarchy_key"] = f"{company}|{department}"
            else:
                chunk.metadata["hierarchy_key"] = f"{company}"


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
           if chunk.metadata.get('company') is not None: # Check if company metadata exists after cleanup
               print(f"  DocType={chunk.metadata.get('doc_type')}, Company={chunk.metadata.get('company')}, Department={chunk.metadata.get('department')}, Employee={chunk.metadata.get('employee')}, Source={chunk.metadata.get('source')}")
               example_count += 1
               if example_count > 5: break # Print a few examples
      if example_count == 0:
          print("  No documents found with company hierarchy metadata.")


    return chunks # Return chunks after splitting

def initialize_vectorstore(chunks: list[Document], db_path: str = db_name):
    """
    Initializes or updates the Chroma vector store with the given chunks.
    Deletes existing collection before adding new ones.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key, chunk_size=1000)

    # Group chunks by company
    company_chunks = {}
    for chunk in chunks:
        company = chunk.metadata.get("company")
        if not company:
            company = "unknown_company"
        if company not in company_chunks:
            company_chunks[company] = []
        company_chunks[company].append(chunk)

    vectorstores = {}
    for company, company_docs in company_chunks.items():
        # Each company gets its own vector DB directory
        company_db_path = os.path.join("vector_db", company)
        if os.path.exists(company_db_path):
            try:
                existing_vectorstore = Chroma(persist_directory=company_db_path, embedding_function=embeddings)
                existing_vectorstore.delete_collection()
                print(f"Deleted existing collection in {company_db_path}")
            except Exception as e:
                print(f"Could not delete existing collection: {e}")
        else:
            os.makedirs(company_db_path, exist_ok=True)

        vectorstore = Chroma(persist_directory=company_db_path, embedding_function=embeddings)
        total_chunks = len(company_docs)
        print(f"Adding {total_chunks} chunks to vectorstore for company {company}.")
        if total_chunks > 0:
            vectorstore.add_documents(documents=company_docs)
        print(f"Vectorstore created/updated in {company_db_path} with {vectorstore._collection.count()} documents")
        vectorstores[company] = vectorstore

    return vectorstores