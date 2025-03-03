from models.alarm import Alarm
from models.alarm_type import AlarmType
import time
def main():
    print("Hello, World!")

    while True:
        alarm_type = AlarmType.BELOW
        alarm_type.set_thresholds(10)

        alarm = Alarm("1234567890", "Channel 1", alarm_type)
        print(alarm.check_alarm())
        time.sleep(900)

if __name__ == "__main__":
    main()

