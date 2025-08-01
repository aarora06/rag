#!/usr/bin/env python3
"""
Script to clear vector stores and restart the application to test the data leakage fix.
"""

import os
import shutil
import subprocess
import time

def clear_vector_stores():
    """Clear all vector store directories"""
    vector_db_path = "vector_db"
    if os.path.exists(vector_db_path):
        print(f"Clearing vector stores in {vector_db_path}...")
        for item in os.listdir(vector_db_path):
            item_path = os.path.join(vector_db_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"  Removed: {item}")
        print("Vector stores cleared successfully!")
    else:
        print("No vector_db directory found.")

def restart_application():
    """Restart the FastAPI application"""
    print("\nRestarting the application...")
    try:
        # Start the application in the background
        process = subprocess.Popen(
            ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a bit for startup
        print("Waiting for application to start...")
        time.sleep(10)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Application started successfully!")
            print("PID:", process.pid)
            return process
        else:
            stdout, stderr = process.communicate()
            print("❌ Application failed to start!")
            print("STDOUT:", stdout.decode())
            print("STDERR:", stderr.decode())
            return None
            
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return None

def test_data_isolation():
    """Test that data isolation is working correctly"""
    print("\nTesting data isolation...")
    
    # Run the diagnostic script
    try:
        result = subprocess.run(
            ["python", "diagnose_data_leakage.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Diagnostic completed successfully!")
            print("\nDiagnostic output:")
            print(result.stdout)
        else:
            print("❌ Diagnostic failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            
    except subprocess.TimeoutExpired:
        print("❌ Diagnostic timed out!")
    except Exception as e:
        print(f"❌ Error running diagnostic: {e}")

if __name__ == "__main__":
    print("=== CLEARING AND RESTARTING APPLICATION ===")
    
    # Clear vector stores
    clear_vector_stores()
    
    # Restart application
    process = restart_application()
    
    if process:
        # Test data isolation
        test_data_isolation()
        
        # Keep the process running for manual testing
        print("\nApplication is running. Press Ctrl+C to stop...")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\nStopping application...")
            process.terminate()
            process.wait()
            print("Application stopped.")
    else:
        print("Failed to start application. Please check the logs.") 