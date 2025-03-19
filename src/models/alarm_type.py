"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This enum is used to set the type of alarm
"""

from enum import Enum

class AlarmType(Enum):
    BELOW = "below"          
    ABOVE = "above"          
    BETWEEN = "between"      
    OUTSIDE = "outside"      
    EQUAL = "equal"          

    def __init__(self, value: str):
        self._value = value

    def __str__(self) -> str:
        return self._value
    
    