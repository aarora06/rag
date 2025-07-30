# Create a virtual Python environment
# Choose a Directory and Create the Environment
python -m venv .venv

#Activate the Virtual Environment
.venv\Scripts\activate

# To Run from Terminal 
uvicorn main:app --reload      

# Local server runs on http://127.0.0.1:8000/
