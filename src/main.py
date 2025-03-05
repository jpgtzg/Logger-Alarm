from models.alarm import Alarm
from models.alarm_type import AlarmType
import streamlit as st
import time
from datetime import datetime, timedelta
from api.api_manager import get_latest_data
from algorithms.excel_reader import read_excel_thresholds
import pandas as pd
import os

def initialize_session_state():
    if 'alarms' not in st.session_state:
        st.session_state.alarms = {}  # Dictionary to store alarms
    if 'current_time' not in st.session_state:
        st.session_state.current_time = datetime.now()  # Store a consistent timestamp

def create_alarm(serial_number, channel, alarm_type, threshold1, threshold2=None):
    alarm_type_obj = AlarmType[alarm_type]
    alarm_type_obj.set_thresholds(threshold1, threshold2)
    return Alarm(serial_number, channel, alarm_type_obj)

def parse_timestamp(timestamp_str):
    """Convert timestamp string to datetime object"""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    return None  # Return None if parsing fails

def main():
    initialize_session_state()
    
    st.title("Alarm Monitoring System")
    
    st.header("Import Alarms from File")
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            temp_file_path = f"temp_upload{file_ext}"
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            thresholds = read_excel_thresholds(temp_file_path)
            
            if thresholds:
                new_alarms_count = 0
                for serial_number, data in thresholds.items():
                    if data['threshold'] != -1.0:
                        alarm_key = f"{serial_number}_CH1"
                        if alarm_key not in st.session_state.alarms:
                            st.session_state.alarms[alarm_key] = {
                                "serial": serial_number,
                                "channel": "Pressure1",
                                "type": "BELOW",
                                "threshold1": data['threshold'],
                                "threshold2": None,
                                "enabled": True,
                                "emails": data['emails']
                            }
                            new_alarms_count += 1
                
                if new_alarms_count > 0:
                    st.success(f"Successfully added {new_alarms_count} new alarms!")
                else:
                    st.info("No new alarms were added.")
            
            os.remove(temp_file_path)
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Sidebar for adding alarms
    st.sidebar.header("Add New Alarm")
    new_serial = st.sidebar.text_input("Serial Number")
    new_channel = st.sidebar.text_input("Channel")
    new_type = st.sidebar.selectbox("Alarm Type", ["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"])
    new_emails = st.sidebar.text_input("Email Addresses (comma-separated)")
    
    new_threshold1 = st.sidebar.number_input("Threshold 1", value=10.0)
    new_threshold2 = None
    if new_type in ["BETWEEN", "OUTSIDE"]:
        new_threshold2 = st.sidebar.number_input("Threshold 2", value=20.0)
        if new_threshold1 >= new_threshold2:
            st.sidebar.error("Threshold 1 must be less than Threshold 2!")
    
    if st.sidebar.button("Add Alarm"):
        if new_serial and new_channel:
            alarm_key = f"{new_serial}_{new_channel}"
            if alarm_key not in st.session_state.alarms:
                st.session_state.alarms[alarm_key] = {
                    "serial": new_serial,
                    "channel": new_channel,
                    "type": new_type,
                    "threshold1": new_threshold1,
                    "threshold2": new_threshold2,
                    "enabled": True,
                    "emails": [email.strip() for email in new_emails.split(',') if email.strip()]
                }
                st.sidebar.success("Alarm added successfully!")
            else:
                st.sidebar.error("This serial and channel already exists!")
    
    # Display alarms
    st.header("Configured Alarms")
    
    now = st.session_state.current_time  # Use stored time instead of datetime.now()

    for alarm_key in list(st.session_state.alarms.keys()):
        alarm_data = st.session_state.alarms[alarm_key]
        
        with st.expander(f"Alarm: {alarm_data['serial']} - {alarm_data['channel']}", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                alarm_data['type'] = st.selectbox(
                    "Alarm Type",
                    ["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"],
                    index=["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"].index(alarm_data['type']),
                    key=f"alarm_type_{alarm_key}"  # Unique key based on alarm_key
                )
                new_channel = st.text_input("Channel", value=alarm_data['channel'], key=f"channel_{alarm_key}")
                
                # Email addresses input
                current_emails = ', '.join(alarm_data.get('emails', []))
                new_emails = st.text_input("Email Addresses (comma-separated)", 
                                         value=current_emails,
                                         key=f"emails_{alarm_key}")
                # Update emails in alarm data
                alarm_data['emails'] = [email.strip() for email in new_emails.split(',') if email.strip()]

                if new_channel != alarm_data['channel']:
                    new_alarm_key = f"{alarm_data['serial']}_{new_channel}"
                    if new_alarm_key not in st.session_state.alarms:
                        current_alarm = st.session_state.alarms.pop(alarm_key)
                        current_alarm['channel'] = new_channel
                        st.session_state.alarms[new_alarm_key] = current_alarm
                        st.rerun()
                    else:
                        st.error("Alarm with this serial and channel exists!")
                
                alarm_data['threshold1'] = st.number_input("Threshold 1", value=float(alarm_data['threshold1']), key=f"threshold1_{alarm_key}")
                
                if alarm_data['type'] in ["BETWEEN", "OUTSIDE"]:
                    alarm_data['threshold2'] = st.number_input("Threshold 2", value=float(alarm_data['threshold2'] or 20.0))
                    if alarm_data['threshold1'] >= alarm_data['threshold2']:
                        st.error("Threshold 1 must be less than Threshold 2!")

            with col2:
                try:
                    alarm = create_alarm(alarm_data['serial'], alarm_data['channel'], alarm_data['type'], alarm_data['threshold1'], alarm_data['threshold2'])

                    if alarm_data['enabled']:
                        latest_data = get_latest_data(alarm_data['serial'], alarm_data['channel'])

                        if latest_data:
                            timestamp_str, value = latest_data
                            timestamp = parse_timestamp(timestamp_str)

                            if timestamp:
                                time_diff = (now - timestamp).total_seconds()
                                days_old = time_diff / (24 * 3600)

                                st.metric("Last Value", f"{float(value):.4f}", f"Updated: {timestamp_str}")
                                if days_old > 1:
                                    st.error(f"⚠️ Data too old! ({days_old:.2f} days)")
                                else: 
                                    alarm_status = alarm.check_alarm()
                                    status_container = st.empty()
                                    if alarm_status:
                                        status_container.error("⚠️ Alarm Triggered!")
                                    else:
                                        status_container.success("✅ System Normal")
                        else:
                            st.error("No data found")
                    else:
                        st.warning("Alarm Disabled")

                except ValueError as e:
                    st.error(f"Configuration Error: {str(e)}")
                except Exception as e:
                    st.error(f"Unexpected Error: {str(e)}")

            with col3:
                alarm_data['enabled'] = st.checkbox("Enable", value=alarm_data['enabled'], key=f"enable_{alarm_key}")
                if st.button("Remove", key=f"remove_{alarm_key}"):
                    del st.session_state.alarms[alarm_key]
                    st.rerun()
    
    st.sidebar.header("Auto-refresh Settings")
    if st.sidebar.checkbox("Enable Auto-refresh", value=False):
        refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 900, 60)
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()
