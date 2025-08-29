#!/usr/bin/env python3
"""
Diagnostic script to check for data leakage between companies.
This script will examine the vector stores and their contents to identify
where data leakage might be occurring.
"""

import os
import sys
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from loading import load_and_chunk_documents
import config

def check_vectorstore_contents():
    """Check the contents of each company's vector store"""
    print("=== DIAGNOSING DATA LEAKAGE ===")
    
    # Check knowledge base structure
    knowledge_base_path = "knowledge_base"
    print(f"\n1. Knowledge Base Structure:")
    if os.path.exists(knowledge_base_path):
        for root, dirs, files in os.walk(knowledge_base_path):
            relative_root = os.path.relpath(root, knowledge_base_path)
            if relative_root != '.':
                print(f"   {relative_root}: {len(files)} files")
    else:
        print("   Knowledge base directory not found!")
        return
    
    # Check vector store directories
    vector_db_path = "vector_db"
    print(f"\n2. Vector Store Directories:")
    if os.path.exists(vector_db_path):
        for company_dir in os.listdir(vector_db_path):
            company_path = os.path.join(vector_db_path, company_dir)
            if os.path.isdir(company_path):
                print(f"   {company_dir}: exists")
    else:
        print("   Vector DB directory not found!")
        return
    
    # Check what documents are loaded during startup
    print(f"\n3. Document Loading Analysis:")
    try:
        all_documents = load_and_chunk_documents(knowledge_base_path=knowledge_base_path)
        print(f"   Total documents loaded: {len(all_documents)}")
        
        # Group by company
        by_company = {}
        for doc in all_documents:
            company = doc.metadata.get('company', 'unknown')
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(doc)
        
        for company, docs in by_company.items():
            print(f"   Company '{company}': {len(docs)} documents")
            # Show first few document sources
            sources = list(set(doc.metadata.get('source', 'unknown') for doc in docs[:3]))
            print(f"     Sample sources: {sources}")
            
    except Exception as e:
        print(f"   Error loading documents: {e}")
    
    # Check vector store contents
    print(f"\n4. Vector Store Contents:")
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=config.API_KEY, chunk_size=1000)
        
        for company_dir in os.listdir(vector_db_path):
            company_path = os.path.join(vector_db_path, company_dir)
            if os.path.isdir(company_path):
                try:
                    vectorstore = Chroma(persist_directory=company_path, embedding_function=embeddings)
                    collection = vectorstore._collection
                    count = collection.count()
                    print(f"   Company '{company_dir}': {count} documents in vector store")
                    
                    # Get sample documents to check metadata
                    if count > 0:
                        results = collection.get(limit=5)
                        if 'metadatas' in results and results['metadatas']:
                            companies_in_store = set()
                            for metadata in results['metadatas']:
                                if metadata and 'company' in metadata:
                                    companies_in_store.add(metadata['company'])
                            print(f"     Companies found in metadata: {companies_in_store}")
                            
                            if len(companies_in_store) > 1:
                                print(f"     ⚠️  DATA LEAKAGE DETECTED! Multiple companies in single vector store!")
                            elif len(companies_in_store) == 1 and list(companies_in_store)[0] != company_dir:
                                print(f"     ⚠️  DATA LEAKAGE DETECTED! Wrong company in vector store!")
                            else:
                                print(f"     ✅ Company isolation appears correct")
                        else:
                            print(f"     ⚠️  No metadata found in vector store")
                            
                except Exception as e:
                    print(f"   Error checking vector store for {company_dir}: {e}")
                    
    except Exception as e:
        print(f"   Error setting up embeddings: {e}")
    
    print(f"\n=== DIAGNOSIS COMPLETE ===")

if __name__ == "__main__":
    check_vectorstore_contents() 