"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This class is used to set alarms on specific loggers/channels
"""

from datetime import datetime
from typing import Dict, Any

from algorithms.mail_sender import send_email
from .alarm_type import AlarmType
from api.api_manager import get_latest_data
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alarm_monitor.log'),
        logging.StreamHandler()
    ]
)

class Alarm:
    active: bool = True

    def __init__(self, 
                 serial_number: str, 
                 channel: str, 
                 alarm_type: AlarmType,
                 pozo: str = "",
                 emails: list[str] = None):
        """
        Initialize an Alarm instance
        
        Args:
            serial_number: Logger serial number
            channel: Channel name
            alarm_type: AlarmType instance
            pozo: Pozo identifier (optional)
            emails: List of email addresses (optional)
        """
        self.serial_number = serial_number
        self.channel = channel
        self.alarm_type = alarm_type
        self.pozo = pozo
        self.emails = emails or []
        self.id = f"{serial_number}_{channel}"
        self.active = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alarm':
        """
        Create an Alarm instance from a dictionary
        
        Args:
            data: Dictionary containing alarm configuration
                Required keys: 'serial', 'channel', 'type', 'threshold1'
                Optional keys: 'threshold2', 'enabled', 'emails', 'pozo'
        """
        # Create and configure alarm type
        alarm_type = AlarmType[data['type']]
        alarm_type.set_thresholds(data['threshold1'], data.get('threshold2'))
        
        # Create alarm instance
        alarm = cls(
            serial_number=data['serial'],
            channel=data['channel'],
            alarm_type=alarm_type,
            pozo=data.get('pozo', ''),
            emails=data.get('emails', [])
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
            'threshold1': self.alarm_type.threshold1,
            'threshold2': self.alarm_type.threshold2,
            'enabled': self.active,
            'emails': self.emails,
            'pozo': self.pozo
        }

    def update(self, data: Dict[str, Any]) -> None:
        """
        Update alarm configuration from dictionary
        
        Args:
            data: Dictionary containing new alarm configuration
        """
        if 'type' in data:
            alarm_type = AlarmType[data['type']]
            alarm_type.set_thresholds(
                data.get('threshold1', self.alarm_type.threshold1),
                data.get('threshold2', self.alarm_type.threshold2)
            )
            self.alarm_type = alarm_type
        
        self.serial_number = data.get('serial', self.serial_number)
        self.channel = data.get('channel', self.channel)
        self.pozo = data.get('pozo', self.pozo)
        self.emails = data.get('emails', self.emails)
        self.active = data.get('enabled', self.active)
        self.id = f"{self.serial_number}_{self.channel}"

    def __str__(self):
        return f"Alarm(serial_number={self.serial_number}, channel_name={self.channel}, alarm_type={self.alarm_type}, active={self.active}, id={self.id})"

    def is_active(self) -> bool:
        return self.active

    def send_alarm_email(self, value: float) -> None:
        """Send alarm notification email"""
        if not self.emails:
            logging.warning(f"No email recipients for alarm {self.serial_number}")
            return
        
        pozo_info = f" (Pozo: {self.pozo})" 
        subject = f"Alarm triggered: {self.serial_number} - {self.channel}{pozo_info}"
        body = (f"The alarm for {self.serial_number} - {self.channel}{pozo_info} has been triggered.\n"
               f"Current value: {value}\n"
               f"Threshold: {self.alarm_type.threshold1}")
        
        send_email(subject, body, self.emails)
        logging.info(f"Alarm email sent to {', '.join(self.emails)} for {self.serial_number} - {self.channel}")

    def send_old_data_email(self, timestamp: str) -> None:
        """Send old data notification email"""
        if not self.emails:
            logging.warning(f"No email recipients for alarm {self.serial_number}")
            return
        
        pozo_info = f" (Pozo: {self.pozo})" 
        subject = f"Old data: {self.serial_number} - {self.channel}{pozo_info}"
        body = (f"The data for {self.serial_number} - {self.channel}{pozo_info} is too old.\n"
               f"Last update: {timestamp}")
        
        send_email(subject, body, self.emails)
        logging.info(f"Old data email sent to {', '.join(self.emails)} for {self.serial_number} - {self.channel}")


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
                        if self.alarm_type.check_alarm(value):
                            logging.info(f"Alarm triggered for {self.serial_number} - {self.channel} - {self.pozo}")
                            self.send_alarm_email(value)
                            return True
                else:
                    if self.alarm_type.check_alarm(value):
                        return True
        return False
