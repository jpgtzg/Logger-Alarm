"""
    API Manager for the alarm monitor, allows for the creation, updating, deletion and testing of alarms. 
    Shares the same instance of the alarm monitor as the run_monitor.py file.
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
from services.alarm_monitor import AlarmMonitor 
import uvicorn
from datetime import datetime
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Alarm Monitor API")

# Initialize alarm monitor and load logger names
alarm_monitor = AlarmMonitor()
alarm_monitor.load_logger_names()  # Load logger names on startup

@app.get("/")
async def root():
    """API health check endpoint"""
    return {
        "status": "running",
        "next_check": alarm_monitor.get_next_check_time().strftime("%Y-%m-%d %H:%M:%S"),
        "check_times": alarm_monitor.checking_times
    }

@app.get("/alarms")
async def get_alarms():
    """Get all configured alarms"""
    try:
        alarms = alarm_monitor.get_alarms()
        return {
            "count": len(alarms),
            "alarms": {
                key: {
                    "serial": alarm.serial_number,
                    "channel": alarm.channel,
                    "type": alarm.alarm_type.name,
                    "threshold1": alarm.alarm_type.threshold1,
                    "threshold2": alarm.alarm_type.threshold2,
                    "active": alarm.active,
                    "emails": alarm.emails,
                    "pozo": alarm.pozo,
                    "logger_name": alarm.logger_name
                } for key, alarm in alarms.items()
            }
        }
    except Exception as e:
        logging.error(f"Error getting alarms: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alarms")
async def create_alarm(alarm_data: Dict[str, Any]):
    """Create a new alarm"""
    try:
        alarm_ids = alarm_monitor.create_alarm(alarm_data)
        return {"message": "Alarm(s) created successfully", "alarm_ids": alarm_ids}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creating alarm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/alarms/{alarm_id}")
async def update_alarm(alarm_id: str, alarm_data: Dict[str, Any]):
    """Update an existing alarm"""
    try:
        alarm_monitor.update_alarm(alarm_id, alarm_data)
        return {"message": f"Alarm {alarm_id} updated successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alarm {alarm_id} not found")
    except Exception as e:
        logging.error(f"Error updating alarm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/alarms/{alarm_id}")
async def delete_alarm(alarm_id: str):
    """Delete an alarm"""
    try:
        alarm_monitor.delete_alarm(alarm_id)
        return {"message": f"Alarm {alarm_id} deleted successfully"}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alarm {alarm_id} not found")
    except Exception as e:
        logging.error(f"Error deleting alarm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alarms/{alarm_id}/test")
async def test_alarm(alarm_id: str):
    """Test an alarm by forcing a check"""
    try:
        result = alarm_monitor.test_alarm(alarm_id)
        return {
            "message": "Alarm test completed",
            "triggered": result,
            "alarm_id": alarm_id
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alarm {alarm_id} not found")
    except Exception as e:
        logging.error(f"Error testing alarm: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-times")
async def get_check_times():
    """Get configured check times"""
    return {"check_times": alarm_monitor.checking_times}

@app.post("/refresh-logger-names")
async def refresh_logger_names():
    """Refresh all logger names from the API"""
    try:
        alarm_monitor._all_logs = []  # Clear cache
        alarm_monitor.load_logger_names()
        return {"message": "Logger names refreshed successfully"}
    except Exception as e:
        logging.error(f"Error refreshing logger names: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logger-names")
async def get_logger_names():
    """Get all logger names"""
    try:
        if not alarm_monitor._all_logs:
            alarm_monitor.load_logger_names()
        
        logger_names = {
            alarm.serial_number: alarm.logger_name 
            for alarm in alarm_monitor.alarms.values()
            if alarm.logger_name
        }
        return {
            "count": len(logger_names),
            "logger_names": logger_names
        }
    except Exception as e:
        logging.error(f"Error getting logger names: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logger-names/{serial_number}")
async def get_logger_name(serial_number: str):
    """Get name for a specific logger"""
    try:
        name = alarm_monitor._get_logger_name(serial_number)
        if name is None:
            raise HTTPException(status_code=404, detail=f"Logger {serial_number} not found")
        return {"serial_number": serial_number, "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting logger name: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alarm/{alarm_id}/value")
async def get_alarm_value(alarm_id: str):
    """Get the value of an alarm"""
    try:
        result = alarm_monitor.get_alarm_value(alarm_id)
        return {"message": "Alarm value retrieved", "value": result}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alarm {alarm_id} not found")
    except Exception as e:
        logging.error(f"Error getting alarm value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

