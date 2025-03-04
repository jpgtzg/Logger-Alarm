"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This class is used to set alarms on specific loggers/channels
"""

from datetime import datetime, timedelta
from .alarm_type import AlarmType
from api.api_manager import get_latest_data
    
class Alarm:
    def __init__(self, serial_number: str, channel: str, alarm_type: AlarmType):
        self.serial_number = serial_number
        self.channel = channel
        self.alarm_type = alarm_type

    def __str__(self):
        return f"Alarm(serial_number={self.serial_number}, channel_name={self.channel}, alarm_type={self.alarm_type})"

    def check_alarm(self) -> bool:
        """
        Check if the alarm should be triggered based on the latest data
        """
        # Get latest data from API
        latest_data = get_latest_data(self.serial_number, self.channel)
        
        if latest_data:
            value = latest_data[1]
        
            # Check value against thresholds
            return self.alarm_type.check_alarm(float(value))
        
        return False  # Trigger alarm if no data available
