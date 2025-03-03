"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This class is used to set alarms on specific loggers/channels
"""

from models.alarm_type import AlarmType
from datetime import datetime, timedelta
from api.api_manager import get_latest_data
    
class Alarm:
    def __init__(self, serial_number: str, channel_name: str, alarm_type: AlarmType):
        self.serial_number = serial_number
        self.channel_name = channel_name
        self.alarm_type = alarm_type

    def __str__(self):
        return f"Alarm(serial_number={self.serial_number}, channel_name={self.channel_name}, alarm_type={self.alarm_type})"

    def check_alarm(self):
        data = get_latest_data(self.serial_number, self.channel_name)

        if data:
            timestamp, value = data

            if timestamp < datetime.now() - timedelta(hours=8):
                return False

            return self.alarm_type.check_alarm(value)

        return False
