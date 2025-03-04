from models.alarm import Alarm
from models.alarm_type import AlarmType
import streamlit as st
import time
from datetime import datetime, timedelta
from api.api_manager import get_latest_data

def initialize_session_state():
    if 'alarms' not in st.session_state:
        st.session_state.alarms = {}  # Dictionary to store alarms

def create_alarm(serial_number, channel, alarm_type, threshold1, threshold2=None):
    alarm_type_obj = AlarmType[alarm_type]
    alarm_type_obj.set_thresholds(threshold1, threshold2)
    return Alarm(serial_number, channel, alarm_type_obj)

def parse_timestamp(timestamp_str):
    """Convert timestamp string to datetime object"""
    try:
        return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None

def main():
    initialize_session_state()
    
    # Set page title
    st.title("Alarm Monitoring System")
    
    # Create sidebar for adding new alarms
    st.sidebar.header("Add New Alarm")
    
    # Input fields for new alarm
    new_serial = st.sidebar.text_input("Serial Number", key="new_serial")
    new_channel = st.sidebar.text_input("Channel", key="new_channel")
    new_type = st.sidebar.selectbox(
        "Alarm Type",
        ["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"],
        key="new_type"
    )
    
    # Threshold inputs based on alarm type
    new_threshold1 = st.sidebar.number_input(
        "Threshold Value" if new_type in ["BELOW", "ABOVE", "EQUAL"] else "Lower Threshold",
        value=10.0,
        key="new_threshold1"
    )
    
    # Show second threshold only for BETWEEN and OUTSIDE types
    new_threshold2 = None
    if new_type in ["BETWEEN", "OUTSIDE"]:
        new_threshold2 = st.sidebar.number_input(
            "Upper Threshold",
            value=20.0,
            key="new_threshold2"
        )
        
        # Validate thresholds
        if new_threshold1 >= new_threshold2:
            st.sidebar.error("Lower threshold must be less than upper threshold!")
    
    # Add alarm button
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
                    "enabled": True
                }
                st.sidebar.success("Alarm added successfully!")
            else:
                st.sidebar.error("This serial number and channel combination already exists!")
    
    # Main content area
    st.header("Configured Alarms")
    
    # Display and manage existing alarms
    for alarm_key in list(st.session_state.alarms.keys()):
        alarm_data = st.session_state.alarms[alarm_key]
        
        # Create an expander for each alarm
        with st.expander(f"Alarm: {alarm_data['serial']} - {alarm_data['channel']}", expanded=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Configuration options
                alarm_data['type'] = st.selectbox(
                    "Alarm Type",
                    ["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"],
                    index=["BELOW", "ABOVE", "BETWEEN", "OUTSIDE", "EQUAL"].index(alarm_data['type']),
                    key=f"type_{alarm_key}"
                )
                
                # Threshold inputs based on alarm type
                threshold_label = "Threshold Value" if alarm_data['type'] in ["BELOW", "ABOVE", "EQUAL"] else "Lower Threshold"
                alarm_data['threshold1'] = st.number_input(
                    threshold_label,
                    value=float(alarm_data['threshold1']),
                    key=f"threshold1_{alarm_key}"
                )
                
                if alarm_data['type'] in ["BETWEEN", "OUTSIDE"]:
                    alarm_data['threshold2'] = st.number_input(
                        "Upper Threshold",
                        value=float(alarm_data['threshold2']) if alarm_data['threshold2'] is not None else 20.0,
                        key=f"threshold2_{alarm_key}"
                    )
                    
                    # Validate thresholds
                    if alarm_data['threshold1'] >= alarm_data['threshold2']:
                        st.error("Lower threshold must be less than upper threshold!")
                else:
                    alarm_data['threshold2'] = None
            
            with col2:
                # Status display
                try:
                    alarm = create_alarm(
                        alarm_data['serial'],
                        alarm_data['channel'],
                        alarm_data['type'],
                        alarm_data['threshold1'],
                        alarm_data['threshold2']
                    )
                    
                    if alarm_data['enabled']:
                        # Get latest data
                        latest_data = get_latest_data(alarm_data['serial'], alarm_data['channel'])
                        
                        if latest_data:
                            timestamp_str, value = latest_data
                            # Display last value and timestamp
                            
                            # Convert timestamp string to datetime object
                            try:
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                            except ValueError:
                                # If the timestamp format is different, try alternative format
                                try:
                                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    raise ValueError(f"Unable to parse timestamp: {timestamp_str}")
                            
                            # Check if data is too old (more than 8 hours)
                            if timestamp < datetime.now() - timedelta(hours=24):
                                status_container.error("⚠️ Data is too old!")
                            else:
                                st.metric(
                                    "Last Value",
                                    f"{float(value):.4f}",
                                    f"Updated: {timestamp_str}"
                                )
                        
                        alarm_status = alarm.check_alarm()
                        status_container = st.empty()
                        if alarm_status:
                            status_container.error("⚠️ Alarm Triggered!")
                        else:
                            status_container.success("✅ System Normal")
                    else:
                        st.warning("Alarm Disabled")
                except ValueError as e:
                    st.error(f"Configuration Error: {str(e)}")
                except TypeError as e:
                    st.error(f"Data Type Error: {str(e)}")
                except Exception as e:
                    st.error(f"Unexpected Error: {str(e)}")
            
            with col3:
                # Control buttons
                alarm_data['enabled'] = st.checkbox("Enable", value=alarm_data['enabled'], key=f"enable_{alarm_key}")
                if st.button("Remove", key=f"remove_{alarm_key}"):
                    del st.session_state.alarms[alarm_key]
                    st.rerun()
    
    # Auto-refresh section
    st.sidebar.header("Auto-refresh Settings")
    if st.sidebar.checkbox("Enable Auto-refresh", value=False):
        refresh_interval = st.sidebar.slider(
            "Refresh Interval (seconds)",
            min_value=1,
            max_value=900,
            value=60
        )
        st.empty()
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()

