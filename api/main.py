# Save this code into a file named main.py

# Import the FastAPI app instance from api.py
from api import app

# The rest of the main.py file is now minimal as the app and logic are in api.py
# The __main__ block for running locally with uvicorn is commented out
# to prevent RuntimeError in environments like Jupyter notebooks.

if __name__ == "__main__":
    import uvicorn
    import asyncio # Import asyncio for local testing lifespan
    import os # Import os for local testing setup
    from config import knowledge_base_path, db_name # Import config for paths

    # Ensure environment variables are set for local testing
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set the OPENAI_API_KEY environment variable for local testing.")
        # os.environ["OPENAI_API_KEY"] = "dummy_openai_key" # Uncomment for dummy key if needed
        # raise ValueError("OPENAI_API_KEY environment variable not set for local testing.")

    if "API_KEY" not in os.environ:
        os.environ["API_KEY"] = "dummy_local_api_key"
        print("Setting a dummy API_KEY 'dummy_local_api_key' for local testing.")
        # API_KEY is now imported in api.py, no need to re-get it here

    # Create the knowledge_base directory and add dummy files for testing if they don't exist
    # This part should ideally be in a separate setup script or handled by the deployment
    # Use imported paths
    # knowledge_base_path = "knowledge_base" # Defined in config.py
    # db_name = "vector_db" # Defined in config.py

    # Create the knowledge_base directory if it doesn't exist
    os.makedirs(knowledge_base_path, exist_ok=True)

    # Define dummy files with the new hierarchy structure
    dummy_files = {
        os.path.join("company_a", "department_x", "employee_1", "doc_a_details.md"): "Details about document A, related to employee 1 in department X of company A.",
        os.path.join("company_a", "department_y", "employee_2", "doc_b_specs.md"): "Specifications for document B, handled by employee 2 in department Y of company A.",
        os.path.join("company_b", "department_z", "doc_c_overview.md"): "Overview of document C, managed by department Z of company B.",
        os.path.join("company_a", "company_policy.md"): "This is Company A's general policy.",
        os.path.join("company_a", "department_x", "dept_guidelines.md"): "Guidelines for Company A, Department X.",
        os.path.join("general_docs", "overview.md"): "This is a general overview document." # Added a general doc example
    }

    for relative_path, content in dummy_files.items():
        full_path = os.path.join(knowledge_base_path, relative_path)
        # Check if the file is not inside the db_name directory (using imported db_name)
        if not full_path.startswith(os.path.join(knowledge_base_path, db_name)):
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            if not os.path.exists(full_path):
                with open(full_path, "w") as f:
                    f.write(content)
                print(f"Created dummy file: {full_path}")


    print("Starting uvicorn server...")
    # The lifespan context manager is automatically handled by uvicorn when app is passed
    # For local testing, ensure lifespan events run
    # This requires running uvicorn directly, not through the notebook cell execution
    # uvicorn.run(app, host="0.0.0.0", port=8000)