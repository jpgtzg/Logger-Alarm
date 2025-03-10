"""
    Backend service for monitoring alarms continuously
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
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
    def __init__(self, email_sending_times=None):
        self._email_sending_times = email_sending_times or ["14:30", "18:30", "22:30"]  # UTC times (CST+6)
        self.alarms = self.load_alarms()

    @property
    def email_sending_times(self):
        return self._email_sending_times

    @email_sending_times.setter
    def email_sending_times(self, times):
        self._email_sending_times = times

    def load_alarms(self) -> Dict[str, Any]:
        """Load alarms from storage file"""
        if os.path.exists("data/alarms.json"):
            with open("data/alarms.json", 'r') as f:
                return json.load(f)
        return {}
    
    def save_alarms(self) -> None:
        """Save alarms to storage file"""
        os.makedirs(os.path.dirname("data/alarms.json"), exist_ok=True)
        with open("data/alarms.json", 'w') as f:
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
        if not alarm_data['emails']:  # Check if email list is empty
            logging.warning(f"No email recipients for alarm {alarm_data['serial']}")
            return
        
        pozo_info = f" (Pozo: {alarm_data['pozo']})" if alarm_data.get('pozo') else ""
        subject = f"Alarm triggered: {alarm_data['serial']} - {alarm_data['channel']}{pozo_info}"
        body = (f"The alarm for {alarm_data['serial']} - {alarm_data['channel']}{pozo_info} has been triggered.\n"
               f"Current value: {value}\n"
               f"Threshold: {alarm_data['threshold1']}")
        
        send_email(subject, body, alarm_data['emails'])
        logging.info(f"Alarm email sent to {', '.join(alarm_data['emails'])} for {alarm_data['serial']}")

    def send_old_data_email(self, alarm_data: Dict[str, Any], timestamp: str) -> None:
        """Send old data notification email"""
        if not alarm_data['emails']:
            logging.warning(f"No email recipients for alarm {alarm_data['serial']}")
            return
        
        pozo_info = f" (Pozo: {alarm_data['pozo']})" if alarm_data.get('pozo') else ""
        subject = f"Old data: {alarm_data['serial']} - {alarm_data['channel']}{pozo_info}"
        body = (f"The data for {alarm_data['serial']} - {alarm_data['channel']}{pozo_info} is too old.\n"
               f"Last update: {timestamp}")
        
        send_email(subject, body, alarm_data['emails'])
        logging.info(f"Old data email sent to {', '.join(alarm_data['emails'])} for {alarm_data['serial']}")

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
                            logging.warning(f"Old data detected for {alarm_data['serial']}")
                            self.send_old_data_email(alarm_data, timestamp_str)
                        else:
                            if alarm.check_alarm():
                                logging.info(f"Alarm triggered for {alarm_data['serial']}")
                                self.send_alarm_email(alarm_data, value)
                
            except Exception as e:
                logging.error(f"Error checking alarm {alarm_key}: {str(e)}")

    def run(self) -> None:
        """Run continuous monitoring"""
        logging.info(f"Starting alarm monitoring service with check times: {self._email_sending_times}")
        
        def get_next_run_time(current_time: datetime, check_times: List[str]) -> datetime:
            """Get the next closest run time from now.
            
            Args:
                current_time: Current datetime
                check_times: List of times in "HH:MM" format
            
            Returns:
                datetime: Next closest future run time
            """
            # Convert all check times to datetime objects for today
            today_times = [datetime.strptime(t, "%H:%M").replace(
                year=current_time.year,
                month=current_time.month,
                day=current_time.day
            ) for t in check_times]
            
            # Add tomorrow's times
            tomorrow_times = [t + timedelta(days=1) for t in today_times]
            all_times = today_times + tomorrow_times
            
            # Get all future times and their time differences
            future_times_with_diff = [
                (t, (t - current_time).total_seconds()) 
                for t in all_times 
                if t > current_time
            ]
            
            # Sort by time difference and get the closest one
            next_time = min(future_times_with_diff, key=lambda x: x[1])[0]
            
            logging.info(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M')}")
            logging.info(f"Next check time: {next_time.strftime('%Y-%m-%d %H:%M')}")
            
            return next_time

        while True:
            try:
                current_time = datetime.now()
                next_run = get_next_run_time(current_time, self._email_sending_times)
                
                sleep_seconds = (next_run - current_time).total_seconds()
                
                logging.info(f"Next check scheduled for: {next_run.strftime('%Y-%m-%d %H:%M')}")
                logging.info(f"Sleeping for {sleep_seconds/3600:.2f} hours")
                
                time.sleep(sleep_seconds)
                
                self.alarms = self.load_alarms()  # Reload alarms in case of updates
                self.check_alarms()
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60) 