"""
    Written by Juan Pablo Gutiérrez
    03 03 2025
"""
import dotenv
import os
import requests
from datetime import datetime, timedelta

dotenv.load_dotenv()

base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")

def send_request(endpoint : str):
    url = base_url + endpoint + api_key
    response = requests.get(url)
    response.raise_for_status()

    return response.json()


def get_all_logs():
    return send_request("/Logger/All/")

def get_logger_name(serial_number : str):
    if type(serial_number) == str:
        serial_number = int(serial_number)

    response = get_all_logs()
    for log in response:
        if log["serial"] == serial_number:
            return log["name"]
    return None

def get_logger_data(serial_number : str, start_date : datetime, end_date : datetime):
    start_date = start_date.strftime("%Y-%m-%d %H:%M")
    end_date = end_date.strftime("%Y-%m-%d %H:%M")
    return send_request(f"/Data/All/{serial_number}/{start_date}/{end_date}/")


def get_channel_data(serial_number : str, channel_name : str, start_date : datetime, end_date : datetime):
    start_date = start_date.strftime("%Y-%m-%d %H:%M")
    end_date = end_date.strftime("%Y-%m-%d %H:%M")
    return send_request(f"/Data/Channel/{serial_number}/{channel_name}/{start_date}/{end_date}/")


def get_daily_data(serial_number : str, start_date : datetime, end_date : datetime):
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")
    return send_request(f"/Data/DailyStats/{serial_number}/{start_date}/{end_date}/")


def get_latest_data(serial_number : str, channel_name : str):
    start_date = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M")
    end_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    response = send_request(f"/Data/Channel/{serial_number}/{channel_name}/{start_date}/{end_date}/")
    
    if response and "data" in response[0] and response[0]["data"]:
        all_data = response[0]["data"][0]["data"]
        if all_data:
            latest_entry = max(all_data, key=lambda x: x["timestamp"])
            return latest_entry["timestamp"], latest_entry["value"]

    return None
