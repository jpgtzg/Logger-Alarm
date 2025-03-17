import json
import os
import time
from models.alarm import Alarm
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from models.alarm_type import AlarmType
import threading
from api.api_manager import get_all_logs

# Ensure directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handlers if they don't exist
if not logger.handlers:
    # File handler
    file_handler = logging.FileHandler('logs/alarm_monitor.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

class AlarmMonitor:
    _instance = None
    _initialized = False
    _all_logs = []
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AlarmMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self, checking_times: list[str] = None):
        # Only initialize once
        if not self._initialized:
            self._alarms_lock = threading.Lock()
            self._logger_names_lock = threading.Lock()
            self.checking_times = checking_times or ["14:30", "18:30", "22:30"]
            self.alarms = self.load_alarms()
            self._initialized = True
        elif checking_times is not None and checking_times != self.checking_times:
            logging.warning(f"Attempted to reinitialize AlarmMonitor with different checking times. Using existing times: {self.checking_times}")

    def run(self):

        logging.info(f"Starting monitoring service for alarms at {self.checking_times}")
         
        while True:
            current_time = datetime.now()
            next_run = self.get_next_run_time(current_time, self.checking_times)
            
            sleep_seconds = (next_run - current_time).total_seconds()
            
            logging.info(f"Next check scheduled for: {next_run.strftime('%Y-%m-%d %H:%M')}")
            logging.info(f"Sleeping for {sleep_seconds/3600:.2f} hours")
            
            time.sleep(sleep_seconds)
            
            self.check_alarms()

    def check_alarms(self):
        """Check all active alarms"""
        # Get a copy of active alarms while holding lock
        with self._alarms_lock:
            active_alarms = [
                alarm for alarm in self.alarms.values()
                if alarm.is_active()
            ]
        
        # Check alarms outside the lock
        for alarm in active_alarms:
            try:
                alarm.check_alarm()
            except Exception as e:
                logging.error(f"Error checking alarm {alarm.id}: {str(e)}")

    def get_alarms(self):
        with self._alarms_lock:
            return self.alarms.copy()

    def create_alarm(self, json_data: Dict[str, Any] | List[Dict[str, Any]]) -> List[str]:
        """
        Create new alarm(s) from JSON data and add to alarms dictionary
        
        Args:
            json_data: Either a single alarm dictionary or list of alarm dictionaries
        
        Returns:
            List[str]: List of created alarm IDs
        """
        created_ids = []
        try:
            # Convert single dict to list for uniform processing
            alarm_data_list = [json_data] if isinstance(json_data, dict) else json_data
            
            # Create alarms outside the lock
            new_alarms = {}
            for data in alarm_data_list:
                alarm = Alarm.from_dict(data)
                new_alarms[alarm.id] = alarm
                created_ids.append(alarm.id)
                logging.info(f"Created alarm: {alarm.id} for logger {alarm.serial_number}")
            
            # Add alarms to the dictionary while holding lock
            with self._alarms_lock:
                self.alarms.update(new_alarms)
            
            # Save after releasing lock
            self.save_alarms()
            
            return created_ids
            
        except Exception as e:
            logging.error(f"Error creating alarm(s): {str(e)}")
            raise ValueError(f"Failed to create alarm(s): {str(e)}")

    def update_alarm(self, alarm_id: str, json_data: dict) -> None:
        """
        Update an existing alarm with new data
        
        Args:
            alarm_id: The alarm identifier (serial number_channel)
            json_data: Dictionary containing new alarm configuration
        """
        try:
            # Check existence and update while holding lock
            with self._alarms_lock:
                if alarm_id not in self.alarms:
                    raise KeyError(f"Alarm {alarm_id} not found")
                self.alarms[alarm_id].update(json_data)
            
            # Save after releasing lock
            self.save_alarms()
            logging.info(f"Updated alarm: {alarm_id}")
            
        except Exception as e:
            logging.error(f"Error updating alarm {alarm_id}: {str(e)}")
            raise ValueError(f"Failed to update alarm: {str(e)}")

    def delete_alarm(self, alarm_id: str) -> None:
        """Delete an alarm from the alarms dictionary"""
        try:
            # Check existence and delete while holding lock
            with self._alarms_lock:
                if alarm_id not in self.alarms:
                    raise KeyError(f"Alarm {alarm_id} not found")
                del self.alarms[alarm_id]
            
            # Save after releasing lock
            self.save_alarms()
            logging.info(f"Deleted alarm: {alarm_id}")
            
        except Exception as e:
            logging.error(f"Error deleting alarm {alarm_id}: {str(e)}")
            raise ValueError(f"Failed to delete alarm: {str(e)}")

    def load_alarms(self) -> Dict[str, Alarm]:
        """
        Load alarms from storage file and convert to Alarm objects
        
        Returns:
            Dict[str, Alarm]: Dictionary with alarm_id -> Alarm object mapping
        """
        alarms = {}
        if os.path.exists("data/alarms.json"):
            try:
                with open("data/alarms.json", 'r') as f:
                    data = json.load(f)
                    
                alarm_data = data.get('alarms', data) if isinstance(data, dict) else data
                
                for alarm_id, alarm_dict in alarm_data.items():
                    try:
                        alarm = Alarm.from_dict(alarm_dict)
                        alarms[alarm_id] = alarm
                        logging.info(f"Loaded alarm: {alarm_id} for logger {alarm.serial_number}")
                    except Exception as e:
                        logging.error(f"Error loading alarm {alarm_id}: {str(e)}")
                        continue
                
                logging.info(f"Successfully loaded {len(alarms)} alarms")
                
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding alarms.json: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error loading alarms: {str(e)}")
        else:
            logging.info("No alarms.json file found, starting with empty alarms")
        
        return alarms

    def load_logger_names(self):
        for alarm in self.alarms.values():
            alarm.logger_name = self._get_logger_name(alarm.serial_number)

    def _get_logger_name(self, serial_number: str):
        if type(serial_number) == str:
            serial_number = int(serial_number)

        if not self._all_logs:
            self._all_logs = get_all_logs()

        for log in self._all_logs:
            if log["serial"] == serial_number:
                return log["name"]
        return None

    def save_alarms(self) -> None:
        """Save alarms to storage file"""
        try:
            os.makedirs(os.path.dirname("data/alarms.json"), exist_ok=True)
            
            # Create the alarm dictionary while holding the lock
            with self._alarms_lock:
                alarm_dict = {
                    key: {
                        'serial': alarm.serial_number,
                        'channel': alarm.channel,
                        'type': alarm.alarm_type.name,
                        'threshold1': alarm.alarm_type.threshold1,
                        'threshold2': alarm.alarm_type.threshold2,
                        'enabled': alarm.active,  
                        'emails': alarm.emails,
                        'pozo': alarm.pozo
                    }
                    for key, alarm in self.alarms.items()
                }
            
            # Release lock before file I/O
            with open("data/alarms.json", 'w') as f:
                json.dump({
                    'alarms': alarm_dict,
                }, f, indent=2)
                    
            logging.info(f"Successfully saved {len(alarm_dict)} alarms")
            
        except Exception as e:
            logging.error(f"Error saving alarms: {str(e)}")
            raise

    def test_alarm(self, alarm_id: str) -> bool:
        """
        Test a specific alarm by forcing a check
        
        Args:
            alarm_id: The ID of the alarm to test
            
        Returns:
            bool: True if alarm was triggered, False otherwise
            
        Raises:
            KeyError: If alarm_id not found
        """
        with self._alarms_lock:
            if alarm_id not in self.alarms:
                raise KeyError(f"Alarm {alarm_id} not found")
            
            alarm = self.alarms[alarm_id]
            
        # Run check without sending email
        return alarm.check_alarm(send_email=True)

    def get_next_run_time(self, current_time: datetime, check_times: List[str]) -> datetime:
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

    def get_next_check_time(self) -> datetime:
        """Get the next scheduled check time"""
        return self.get_next_run_time(datetime.now(), self.checking_times)
    
    def get_alarm_value(self, alarm_id: str) -> float:
        """Get the value of an alarm"""
        with self._alarms_lock:
            if alarm_id not in self.alarms:
                raise KeyError(f"Alarm {alarm_id} not found")
            return self.alarms[alarm_id].get_value()
