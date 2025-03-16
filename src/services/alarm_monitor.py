import json
import os
import time
from models.alarm import Alarm
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from models.alarm_type import AlarmType
import threading

logger = logging.getLogger(__name__)

class AlarmMonitor:
    _instance = None
    _initialized = False
    
    def __new__(cls, checking_times: list[str] = None):
        if cls._instance is None:
            cls._instance = super(AlarmMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self, checking_times: list[str] = None):
        # Only initialize once
        if not self._initialized:
            self._alarms_lock = threading.Lock()
            self._logger_names_lock = threading.Lock()
            self._logger_names = {}
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
        with self._alarms_lock:
            alarms_to_check = self.alarms.copy()
        
        for alarm in alarms_to_check.values():
            if not alarm.is_active():
                continue
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
            
            with self._alarms_lock:
                for data in alarm_data_list:
                    alarm = Alarm.from_dict(data)
                    self.alarms[alarm.id] = alarm
                    created_ids.append(alarm.id)
                    logging.info(f"Created alarm: {alarm.id} for logger {alarm.serial_number}")
                
                self.save_alarms()
            
            return created_ids
            
        except Exception as e:
            logging.error(f"Error creating alarm(s): {str(e)}")
            raise ValueError(f"Failed to create alarm(s): {str(e)}")

    def update_alarm(self, alarm_key: str, json_data: dict) -> None:
        """
        Update an existing alarm with new data
        
        Args:
            alarm_key: The alarm identifier (serial_number_channel)
            json_data: Dictionary containing new alarm configuration
        """
        try:
            with self._alarms_lock:
                if alarm_key not in self.alarms:
                    raise KeyError(f"Alarm {alarm_key} not found")
                
                self.alarms[alarm_key].update(json_data)
                self.save_alarms()
                
            logging.info(f"Updated alarm: {alarm_key}")
            
        except Exception as e:
            logging.error(f"Error updating alarm {alarm_key}: {str(e)}")
            raise ValueError(f"Failed to update alarm: {str(e)}")

    def load_alarms(self) -> Dict[str, Alarm]:
        """
        Load alarms from storage file and convert to Alarm objects
        
        Returns:
            Dict[str, Alarm]: Dictionary with alarm_key -> Alarm object mapping
        """
        alarms = {}
        if os.path.exists("data/alarms.json"):
            try:
                with open("data/alarms.json", 'r') as f:
                    data = json.load(f)
                    
                alarm_data = data.get('alarms', data) if isinstance(data, dict) else data
                
                for alarm_key, alarm_dict in alarm_data.items():
                    try:
                        alarm = Alarm.from_dict(alarm_dict)
                        alarms[alarm_key] = alarm
                        logging.info(f"Loaded alarm: {alarm_key} for logger {alarm.serial_number}")
                    except Exception as e:
                        logging.error(f"Error loading alarm {alarm_key}: {str(e)}")
                        continue
                
                if isinstance(data, dict) and 'logger_names' in data:
                    with self._logger_names_lock:
                        self._logger_names.update(data['logger_names'])
                
                logging.info(f"Successfully loaded {len(alarms)} alarms")
                
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding alarms.json: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error loading alarms: {str(e)}")
        else:
            logging.info("No alarms.json file found, starting with empty alarms")
        
        return alarms

    def save_alarms(self) -> None:
        """Save alarms to storage file"""
        try:
            os.makedirs(os.path.dirname("data/alarms.json"), exist_ok=True)
            
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
                
                with open("data/alarms.json", 'w') as f:
                    with self._logger_names_lock:
                        json.dump({
                            'alarms': alarm_dict,
                            'logger_names': self._logger_names
                        }, f, indent=2)
                    
            logging.info(f"Successfully saved {len(self.alarms)} alarms")
            
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
        return alarm.check_alarm(send_email=False)

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

    def get_logger_name(self, serial_number: str) -> str:
        """Get the human-readable name for a logger
        
        Args:
            serial_number: The logger's serial number
            
        Returns:
            str: The logger's name or the serial number if not found
        """
        with self._logger_names_lock:
            return self._logger_names.get(serial_number, serial_number)

    def update_logger_name(self, serial_number: str, name: str) -> None:
        """Update or add a logger name
        
        Args:
            serial_number: The logger's serial number
            name: The human-readable name for the logger
        """
        with self._logger_names_lock:
            self._logger_names[serial_number] = name
            self.save_alarms()  # Save changes to persist logger names

    def get_all_logger_names(self) -> Dict[str, str]:
        """Get all logger names
        
        Returns:
            Dict[str, str]: Dictionary mapping serial numbers to logger names
        """
        with self._logger_names_lock:
            return self._logger_names.copy()