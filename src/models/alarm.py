"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This class is used to set alarms on specific loggers/channels
"""

from datetime import datetime
from typing import Dict, Any, Optional
import os

from algorithms.mail_sender import send_email
from .alarm_type import AlarmType
from api.api_manager import get_latest_data
import logging

logger = logging.getLogger(__name__)

# Ensure log directory exists
os.makedirs('logs', exist_ok=True)

# Setup file handler
file_handler = logging.FileHandler('logs/alarm_monitor.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Setup stream handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure logger
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

class Alarm:
    active: bool = True

    def __init__(self, 
                 serial_number: str, 
                 channel: str, 
                 alarm_type: AlarmType,
                 threshold1: float = None,
                 threshold2: Optional[float] = None,
                 pozo: str = "",
                 emails: list[str] = None,
                 logger_name: str = ""):
        """
        Initialize an Alarm instance
        
        Args:
            serial_number: Logger serial number
            channel: Channel name
            alarm_type: AlarmType instance
            threshold1: Primary threshold value
            threshold2: Secondary threshold value (required for BETWEEN and OUTSIDE)
            pozo: Pozo identifier (optional)
            emails: List of email addresses (optional)
            logger_name: Logger display name (optional)
        """
        self.serial_number = serial_number
        self.channel = channel
        self.alarm_type = alarm_type
        self.pozo = pozo
        self.emails = emails or []
        self.logger_name = logger_name
        self.id = f"{serial_number}_{channel}"
        self.active = True
        self._threshold1 = None
        self._threshold2 = None
        self.set_thresholds(threshold1, threshold2)

    def set_thresholds(self, threshold1: float, threshold2: Optional[float] = None) -> None:
        """Set the threshold values for the alarm.
        
        Args:
            threshold1: Primary threshold value
            threshold2: Secondary threshold value (required for BETWEEN and OUTSIDE)
        
        Raises:
            ValueError: If thresholds are invalid for the alarm type
        """
        if threshold1 is None:
            return
            
        if self.alarm_type in [AlarmType.BETWEEN, AlarmType.OUTSIDE]:
            if threshold2 is None:
                raise ValueError(f"{self.alarm_type} alarm type requires two threshold values")
            if threshold1 >= threshold2:
                raise ValueError("First threshold must be less than second threshold")
            self._threshold1 = threshold1
            self._threshold2 = threshold2
        else:
            if threshold2 is not None:
                raise ValueError(f"{self.alarm_type} alarm type only accepts one threshold value")
            self._threshold1 = threshold1
            self._threshold2 = None

    @property
    def threshold1(self) -> Optional[float]:
        return self._threshold1
    
    @property
    def threshold2(self) -> Optional[float]:
        return self._threshold2

    def check_threshold(self, value: float) -> bool:
        """Check if the value triggers the alarm based on the alarm type and thresholds.
        
        Args:
            value: The value to check against the thresholds
        
        Returns:
            bool: True if alarm should trigger, False otherwise
        
        Raises:
            ValueError: If thresholds haven't been set
        """
        if self._threshold1 is None:
            raise ValueError("Thresholds not set")
            
        if self.alarm_type == AlarmType.BELOW:
            return value < self._threshold1
        elif self.alarm_type == AlarmType.ABOVE:
            return value > self._threshold1
        elif self.alarm_type == AlarmType.EQUAL:
            return value == self._threshold1
        elif self.alarm_type == AlarmType.BETWEEN:
            if self._threshold2 is None:
                raise ValueError("Second threshold not set")
            return self._threshold1 < value < self._threshold2
        elif self.alarm_type == AlarmType.OUTSIDE:
            if self._threshold2 is None:
                raise ValueError("Second threshold not set")
            return value < self._threshold1 or value > self._threshold2
        
        return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alarm':
        """
        Create an Alarm instance from a dictionary
        
        Args:
            data: Dictionary containing alarm configuration
                Required keys: 'serial', 'channel', 'type', 'threshold1'
                Optional keys: 'threshold2', 'enabled', 'emails', 'pozo', 'logger_name'
        """
        # Create alarm instance
        alarm = cls(
            serial_number=data['serial'],
            channel=data['channel'],
            alarm_type=AlarmType[data['type']],
            threshold1=data.get('threshold1'),
            threshold2=data.get('threshold2'),
            pozo=data.get('pozo', ''),
            emails=data.get('emails', []),
            logger_name=data.get('logger_name', '')
        )
        alarm.active = data.get('enabled', True)
        alarm.id = f"{data['serial']}_{data['channel']}"
        return alarm

    def to_dict(self) -> Dict[str, Any]:
        """Convert alarm instance to dictionary representation"""
        return {
            'serial': self.serial_number,
            'channel': self.channel,
            'type': self.alarm_type.name,
            'threshold1': self.threshold1,
            'threshold2': self.threshold2,
            'enabled': self.active,
            'emails': self.emails,
            'pozo': self.pozo,
            'logger_name': self.logger_name
        }

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update alarm configuration from dictionary
        
        Args:
            data: Dictionary containing new alarm configuration
        """
        if 'type' in data:
            self.alarm_type = AlarmType[data['type']]
        
        self.serial_number = data.get('serial', self.serial_number)
        self.channel = data.get('channel', self.channel)
        self.pozo = data.get('pozo', self.pozo)
        self.emails = data.get('emails', self.emails)
        self.active = data.get('enabled', self.active)
        self.logger_name = data.get('logger_name', self.logger_name)
        
        # Update thresholds if provided
        if 'threshold1' in data:
            self.set_thresholds(
                data.get('threshold1'), 
                data.get('threshold2', self.threshold2)
            )
            
        self.id = f"{self.serial_number}_{self.channel}"

    def __str__(self):
        return f"Alarm(serial_number={self.serial_number}, channel_name={self.channel}, alarm_type={self.alarm_type}, active={self.active}, pozo={self.pozo}, threshold1={self.threshold1}, threshold2={self.threshold2}, id={self.id})"

    def is_active(self) -> bool:
        return self.active

    def send_alarm_email(self, value: float) -> None:
        """Send alarm notification email"""
        if not self.emails:
            logging.warning(f"No email recipients for alarm {self.serial_number}")
            return
        
        display_name = self.logger_name if self.logger_name else self.serial_number
        pozo_info = f" (Pozo: {self.pozo})" if self.pozo else ""
        subject = f"{display_name} - {self.channel}{pozo_info}"
        body = (f"The alarm for {display_name} ({self.serial_number}) - {self.channel}{pozo_info} has been triggered.\n"
               f"Current value: {value}\n"
               f"Threshold: {self.threshold1}")
        
        send_email(subject, body, self.emails)
        logging.info(f"Alarm email sent to {', '.join(self.emails)} for {display_name} - {self.serial_number} - {self.channel}")

    def send_old_data_email(self, timestamp: str) -> None:
        """Send old data notification email"""
        if not self.emails:
            logging.warning(f"No email recipients for alarm {self.serial_number}")
            return
        
        display_name = self.logger_name if self.logger_name else self.serial_number
        pozo_info = f" (Pozo: {self.pozo})" if self.pozo else ""
        subject = f"{display_name} - {self.channel}{pozo_info}"
        body = (f"The data for {display_name} ({self.serial_number}) - {self.channel}{pozo_info} is too old.\n"
               f"Last update: {timestamp}")
        
        send_email(subject, body, self.emails)
        logging.info(f"Old data email sent to {', '.join(self.emails)} for {display_name} - {self.serial_number} - {self.channel}")


    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Convert timestamp string to datetime object"""
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        return None
    
    def check_alarm(self, send_email: bool = True) -> bool:
        """
        Check if the alarm should be triggered based on the latest data
        """
        latest_data = get_latest_data(self.serial_number, self.channel)
        
        if latest_data:
            timestamp_str, value = latest_data
            value = float(value)
            timestamp = self.parse_timestamp(timestamp_str)

            if timestamp:
                time_diff = (datetime.now() - timestamp).total_seconds()
                days_old = time_diff / (24 * 60 * 60)

                if send_email:
                    if days_old > 1:
                        logging.info(f"Old data detected for {self.serial_number} - {self.channel} - {self.pozo}")
                        self.send_old_data_email(timestamp_str)

                    else:
                        if self.check_threshold(value):
                            logging.info(f"Alarm triggered for {self.serial_number} - {self.channel} - {self.pozo}")
                            self.send_alarm_email(value)
                            return True
                else:
                    if self.check_threshold(value):
                        return True
        return False

    def get_value(self) -> float:
        """Get the value of the alarm"""
        latest_data = get_latest_data(self.serial_number, self.channel)
        if latest_data:
            timestamp_str, value = latest_data
            return float(value)
        return None