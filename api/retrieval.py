# retrieval.py
import os
from typing import Dict
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Import configuration from config.py
from config import openai_api_key, MODEL, db_name # Import db_name here as well


def setup_retrievers(vectorstore: Chroma):
    """
    Sets up multiple retrievers filtered by hierarchy levels based on metadata presence.
    Removes reliance on the 'products' doc_type filter.
    """
    # Ensure the vectorstore is not None
    if vectorstore is None:
        print("Vectorstore is not initialized. Cannot setup retrievers.")
        return {}

    base_search_kwargs = {'k': 3}

    # Create retrievers for each hierarchy level without static filters.
    # Filtering by company/department/employee will be handled dynamically in the API endpoint.
    retrievers = {
        'employee_level': vectorstore.as_retriever(search_kwargs=base_search_kwargs),
        'department_level': vectorstore.as_retriever(search_kwargs=base_search_kwargs),
        'company_level': vectorstore.as_retriever(search_kwargs=base_search_kwargs),
        'general': vectorstore.as_retriever(search_kwargs=base_search_kwargs),
    }

    return retrievers


def setup_llm():
    """
    Sets up the ChatOpenAI language model.
    """
    llm = ChatOpenAI(temperature=0.7, model_name=MODEL, openai_api_key=openai_api_key)
    return llm