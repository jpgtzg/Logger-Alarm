"""
    Backend service entry point with additional robustness
"""
import sys
import logging
from services.alarm_monitor import AlarmMonitor
from datetime import datetime
import time
import os
import signal

# Configuration
EMAIL_SENDING_TIMES = ["14:30", "18:30", "22:30"]
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds

def setup_logging():
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Received signal {signum}")
    logging.info("Shutting down monitoring service...")
    sys.exit(0)

def main():
    """Main monitoring service function"""
    setup_logging()
    logging.info("Starting monitoring service")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            # Initialize the singleton with the check times
            monitor = AlarmMonitor(EMAIL_SENDING_TIMES)
            logging.info(f"Monitoring service initialized successfully with check times: {monitor.checking_times}")
            monitor.run()  # This runs indefinitely unless an error occurs
            
        except KeyboardInterrupt:
            logging.info("Service stopped by user")
            sys.exit(0)
            
        except Exception as e:
            retry_count += 1
            logging.error(f"Error in monitoring service (attempt {retry_count}/{MAX_RETRIES}): {str(e)}")
            if retry_count < MAX_RETRIES:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logging.critical("Max retries reached. Shutting down service.")
                sys.exit(1)

if __name__ == "__main__":
    main()