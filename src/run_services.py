"""
Service runner that manages both the monitor and API server. 
"""
import multiprocessing
import uvicorn
import logging
import os
from api_manager import app
from run_monitor import main as run_monitor

def setup_logging():
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def run_api():
    """Run the FastAPI server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def main():
    setup_logging()
    
    # Start the monitor process
    monitor_process = multiprocessing.Process(target=run_monitor)
    monitor_process.start()
    
    # Run the API server in the main process
    run_api()

if __name__ == "__main__":
    main() 