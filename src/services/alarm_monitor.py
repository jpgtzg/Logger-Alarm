"""
    Backend service for monitoring alarms continuously
"""
import time
from datetime import datetime
from typing import Dict, Any
import json
import os
import logging

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alarm_monitor.log'),
        logging.StreamHandler()
    ]
)

from models.alarm import Alarm
from models.alarm_type import AlarmType
from api.api_manager import get_latest_data
from algorithms.mail_sender import send_email

class AlarmMonitor:
    def __init__(self, storage_path: str = "data/alarms.json"):
        self.storage_path = storage_path
        self.alarms: Dict[str, Any] = self.load_alarms()
        
    def load_alarms(self) -> Dict[str, Any]:
        """Load alarms from storage file"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_alarms(self) -> None:
        """Save alarms to storage file"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.alarms, f)

    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Convert timestamp string to datetime object"""
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        return None

    def send_alarm_email(self, alarm_data: Dict[str, Any], value: float) -> None:
        """Send alarm notification email"""
        for email in alarm_data['emails']:
            subject = f"Alarm triggered: {alarm_data['serial']} - {alarm_data['channel']}"
            body = (f"The alarm for {alarm_data['serial']} - {alarm_data['channel']} has been triggered.\n"
                   f"Current value: {value}\n"
                   f"Threshold: {alarm_data['threshold1']}")
            send_email(subject, body, [email])
            logging.info(f"Alarm email sent to {email} for {alarm_data['serial']}")

    def send_old_data_email(self, alarm_data: Dict[str, Any], timestamp: str) -> None:
        """Send old data notification email"""
        for email in alarm_data['emails']:
            subject = f"Old data: {alarm_data['serial']} - {alarm_data['channel']}"
            body = (f"The data for {alarm_data['serial']} - {alarm_data['channel']} is too old.\n"
                   f"Last update: {timestamp}")
            send_email(subject, body, [email])
            logging.info(f"Old data email sent to {email} for {alarm_data['serial']}")

    def check_alarms(self) -> None:
        """Check all enabled alarms"""
        now = datetime.now()
        
        for alarm_key, alarm_data in self.alarms.items():
            if not alarm_data.get('enabled', True):
                continue

            try:
                # Create alarm object
                alarm_type = AlarmType[alarm_data['type']]
                alarm_type.set_thresholds(alarm_data['threshold1'], alarm_data.get('threshold2'))
                alarm = Alarm(alarm_data['serial'], alarm_data['channel'], alarm_type)

                # Get latest data
                latest_data = get_latest_data(alarm_data['serial'], alarm_data['channel'])
                
                if latest_data:
                    timestamp_str, value = latest_data
                    timestamp = self.parse_timestamp(timestamp_str)

                    if timestamp:
                        time_diff = (now - timestamp).total_seconds()
                        days_old = time_diff / (24 * 3600)

                        if days_old > 1:
                            self.send_old_data_email(alarm_data, timestamp_str)
                        else:
                            if alarm.check_alarm():
                                self.send_alarm_email(alarm_data, value)
                
            except Exception as e:
                logging.error(f"Error checking alarm {alarm_key}: {str(e)}")

    def run(self, check_interval: int = 60) -> None:
        """Run continuous monitoring"""
        logging.info("Starting alarm monitoring service")
        while True:
            try:
                self.alarms = self.load_alarms()  # Reload alarms in case of updates
                self.check_alarms()
                print("Checking alarms")
                time.sleep(check_interval)
            except Exception as e:
                logging.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(check_interval) 