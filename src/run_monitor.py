"""
    Backend service entry point with additional robustness
"""
import sys
import logging
from services.alarm_monitor import AlarmMonitor
from datetime import datetime
import time
import os
email_sending_times = ["14:30", "18:30", "22:30"]
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
def main():
    logging.basicConfig(
        filename=f'logs/monitor_{datetime.now().strftime("%Y%m%d")}.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting monitoring service")
    
    try:
        monitor = AlarmMonitor(email_sending_times)  # Uses default times
        monitor.run()
    except KeyboardInterrupt:
        logging.info("Service stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        # Optionally send admin notification about service failure
        raise

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            logging.error(f"Service crashed, restarting... Error: {str(e)}")
            time.sleep(60)  # Wait before restarting