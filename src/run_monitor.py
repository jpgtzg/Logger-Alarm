"""
    Backend service entry point with additional robustness
"""
import sys
import logging
from services.alarm_monitor import AlarmMonitor
from datetime import datetime
import time
def main():
    logging.basicConfig(
        filename=f'logs/monitor_{datetime.now().strftime("%Y%m%d")}.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting monitoring service")
    
    try:
        monitor = AlarmMonitor()
        monitor.run(check_interval=28800)
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