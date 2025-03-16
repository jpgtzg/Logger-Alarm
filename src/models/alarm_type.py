"""
    Written by Juan Pablo Gutiérrez
    04 03 2025

    This enum is used to set the type of alarm
"""

from enum import Enum
from typing import Union, Tuple, Optional

class AlarmType(Enum):
    BELOW = "below"          
    ABOVE = "above"          
    BETWEEN = "between"      
    OUTSIDE = "outside"      
    EQUAL = "equal"          

    def __init__(self, value: str):
        super().__init__()
        self._value = value
        self._threshold1: Optional[float] = None
        self._threshold2: Optional[float] = None

    def __init__(self, json_data: dict):
        self._value = json_data["value"]
        self._threshold1 = json_data["threshold1"]
        self._threshold2 = json_data["threshold2"]

    def __str__(self) -> str:
        return self._value

    @property
    def threshold1(self) -> Optional[float]:
        return self._threshold1
    
    @property
    def threshold2(self) -> Optional[float]:
        return self._threshold2
    
    def set_thresholds(self, threshold1: float, threshold2: Optional[float] = None) -> None:
        """Set the threshold values for the alarm type.
        
        Args:
            threshold1: Primary threshold value
            threshold2: Secondary threshold value (required for BETWEEN and OUTSIDE)
        
        Raises:
            ValueError: If thresholds are invalid for the alarm type
        """
        if self in [AlarmType.BETWEEN, AlarmType.OUTSIDE]:
            if threshold2 is None:
                raise ValueError(f"{self._value} alarm type requires two threshold values")
            if threshold1 >= threshold2:
                raise ValueError("First threshold must be less than second threshold")
            self._threshold1 = threshold1
            self._threshold2 = threshold2
        else:
            if threshold2 is not None:
                raise ValueError(f"{self._value} alarm type only accepts one threshold value")
            self._threshold1 = threshold1
            self._threshold2 = None
    
    def check_alarm(self, value: float) -> bool:
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
            
        if self == AlarmType.BELOW:
            return value < self._threshold1
        elif self == AlarmType.ABOVE:
            return value > self._threshold1
        elif self == AlarmType.EQUAL:
            return value == self._threshold1
        elif self == AlarmType.BETWEEN:
            if self._threshold2 is None:
                raise ValueError("Second threshold not set")
            return self._threshold1 < value < self._threshold2
        elif self == AlarmType.OUTSIDE:
            if self._threshold2 is None:
                raise ValueError("Second threshold not set")
            return value < self._threshold1 or value > self._threshold2
        
        return False
    
    