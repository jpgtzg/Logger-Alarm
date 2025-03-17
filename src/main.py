from datetime import datetime
from typing import Dict, Any
import os
import json
import streamlit as st
import requests

from algorithms.excel_reader import read_excel_thresholds

# Constants
API_URL = f"http://{st.secrets['api_url']}"  # Add http:// protocol to the API URL
ALARM_TYPES = ["ABOVE", "BELOW", "BETWEEN", "OUTSIDE"]

def init_session_state():
    """Initialize session state variables"""
    if 'alarms' not in st.session_state:
        st.session_state.alarms = {}
    if 'logger_names' not in st.session_state:
        st.session_state.logger_names = {}
    if 'check_times' not in st.session_state:
        st.session_state.check_times = []
    if 'next_check' not in st.session_state:
        st.session_state.next_check = None
    if 'alarm_values' not in st.session_state:
        st.session_state.alarm_values = {}
    if 'delete_confirmation' not in st.session_state:
        st.session_state.delete_confirmation = None

def fetch_api_data():
    """Fetch all necessary data from the API"""
    try:
        # Fetch root info
        response = requests.get(f"{API_URL}/")
        root_data = response.json()
        st.session_state.check_times = root_data["check_times"]
        st.session_state.next_check = datetime.strptime(root_data["next_check"], "%Y-%m-%d %H:%M:%S")

        # Fetch alarms
        response = requests.get(f"{API_URL}/alarms")
        st.session_state.alarms = response.json()["alarms"]

        # Fetch logger names
        response = requests.get(f"{API_URL}/logger-names")
        st.session_state.logger_names = response.json()["logger_names"]

        # Fetch latest values for all alarms
        st.session_state.alarm_values = {}
        for alarm_id, alarm in st.session_state.alarms.items():
            try:
                response = requests.get(f"{API_URL}/alarm/{alarm_id}/value")
                if response.status_code == 200:
                    st.session_state.alarm_values[alarm_id] = response.json()["value"]
            except Exception:
                st.session_state.alarm_values[alarm_id] = None
                
    except Exception as e:
        st.error(f"Error fetching data from API: {str(e)}")

def create_alarm(alarm_data: Dict[str, Any]):
    """Create a new alarm via API"""
    try:
        response = requests.post(f"{API_URL}/alarms", json=alarm_data)
        response.raise_for_status()
        st.success("Alarm created successfully!")
        fetch_api_data()  # Refresh data
    except Exception as e:
        st.error(f"Error creating alarm: {str(e)}")

def update_alarm(alarm_id: str, alarm_data: Dict[str, Any]):
    """Update an existing alarm via API"""
    try:
        response = requests.put(f"{API_URL}/alarms/{alarm_id}", json=alarm_data)
        response.raise_for_status()
        st.success(f"Alarm {alarm_id} updated successfully!")
        fetch_api_data()  # Refresh data
    except Exception as e:
        st.error(f"Error updating alarm: {str(e)}")

def delete_alarm(alarm_id: str):
    """Delete an alarm via API"""
    try:
        print(f"Deleting alarm {alarm_id}")
        response = requests.delete(f"{API_URL}/alarms/{alarm_id}")
        response.raise_for_status()
        st.success(f"Alarm {alarm_id} deleted successfully!")
        fetch_api_data()  # Refresh data
    except Exception as e:
        st.error(f"Error deleting alarm: {str(e)}")

def test_alarm(alarm_id: str):
    """Test an alarm via API"""
    try:
        response = requests.post(f"{API_URL}/alarms/{alarm_id}/test")
        result = response.json()
        if result["triggered"]:
            st.warning("⚠️ Alarm conditions were met!")
        else:
            st.info("✅ Alarm conditions were not met.")
    except Exception as e:
        st.error(f"Error testing alarm: {str(e)}")

def test_alarms():
    """Test all alarms via API"""
    try:
        response = requests.post(f"{API_URL}/alarms/test")
        response.raise_for_status()
        st.success("Alarms tested successfully!")
    except Exception as e:
        st.error(f"Error testing alarms: {str(e)}")

def refresh_logger_names():
    """Refresh logger names via API"""
    try:
        response = requests.post(f"{API_URL}/refresh-logger-names")
        response.raise_for_status()
        st.success("Logger names refreshed successfully!")
        fetch_api_data()  # Refresh data
    except Exception as e:
        st.error(f"Error refreshing logger names: {str(e)}")

def main():
    st.set_page_config(
        page_title="Alarm Monitor Dashboard",
        page_icon="🔔",
        layout="wide"
    )

    # Initialize session state
    init_session_state()

    # Sidebar
    st.sidebar.title("🔔 Alarm Monitor")
    st.sidebar.markdown("---")

    # Test alarms button
    if st.sidebar.button("🧪 Test Alarms"):
        test_alarms()

    # Refresh data button in sidebar
    if st.sidebar.button("🔄 Refresh All Data"):
        fetch_api_data()

    # Add refresh logger names button
    if st.sidebar.button("🔄 Refresh Logger Names"):
        refresh_logger_names()

    # Display next check time in sidebar
    if st.session_state.next_check:
        st.sidebar.info(f"⏰ Next check: {st.session_state.next_check.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Display check times in sidebar
    if st.session_state.check_times:
        st.sidebar.markdown("### 📅 Check Times")
        for time in st.session_state.check_times:
            st.sidebar.text(f"• {time}")

    # Main content
    st.title("🔔 Alarm Monitor Dashboard")
    
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
                        # Create alarm data in the format expected by the API
                        alarm_data = {
                            "serial": serial_number,
                            "channel": "Pressure1",
                            "type": "BELOW",
                            "threshold1": data['threshold'],
                            "threshold2": None,
                            "enabled": True,
                            "emails": data['emails'],
                            "pozo": data.get('pozo', '')  # Optional pozo field
                        }
                        
                        try:
                            # Use the API to create the alarm
                            response = requests.post(f"{API_URL}/alarms", json=alarm_data)
                            response.raise_for_status()
                            new_alarms_count += 1
                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to create alarm for logger {serial_number}: {str(e)}")
                            continue
                
                if new_alarms_count > 0:
                    st.success(f"Successfully added {new_alarms_count} new alarms!")
                    # Refresh the alarms data
                    fetch_api_data()
                else:
                    st.info("No new alarms were added.")
            
            os.remove(temp_file_path)
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    # Create new alarm section
    with st.expander("➕ Create New Alarm", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            serial = st.text_input("Serial Number")
            channel = st.number_input("Channel", min_value=1, max_value=16)
            alarm_type = st.selectbox("Alarm Type", ALARM_TYPES)
            threshold1 = st.number_input("Threshold 1", value=0.0, format="%.2f")
        with col2:
            emails = st.text_input("Emails (comma-separated)")
            pozo = st.text_input("Pozo")
            active = st.checkbox("Enable Alarm", value=True)
            threshold2 = st.number_input("Threshold 2", value=0.0, format="%.2f")

        if st.button("Create Alarm"):
            if not serial or not channel:
                st.error("Serial number and channel are required!")
            else:
                alarm_data = {
                    "serial": serial,
                    "channel": channel,
                    "type": alarm_type,
                    "threshold1": threshold1,
                    "threshold2": threshold2,
                    "enabled": active,
                    "emails": [e.strip() for e in emails.split(",") if e.strip()],
                    "pozo": pozo
                }
                create_alarm(alarm_data)

    # Display existing alarms
    st.markdown("## Configured Alarms")
    
    # Display alarms in a table format
    if st.session_state.alarms:
        for alarm_id, alarm in st.session_state.alarms.items():
            with st.expander(
                f"🔔 {alarm.get('logger_name', 'Unknown Logger')}",
                expanded=True
            ):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown("### 📝 Configuration")
                    st.write(f"**Serial:** {alarm['serial']}")
                    st.write(f"**Channel:** {alarm['channel']}")
                    st.write(f"**Type:** {alarm['type']}")
                    st.write(f"**Thresholds:** {alarm['threshold1']}, {alarm['threshold2']}")
                    
                    # Display latest value with refresh button
                    current_value = st.session_state.alarm_values.get(alarm_id, "N/A")
                    col1_1, col1_2 = st.columns([2, 1])
                    with col1_1:
                        if not current_value:
                            st.error("No value available")
                        else:
                            st.metric(label="Latest Value", value=f"{float(current_value):.4f}")
                    with col1_2:
                        if st.button("🔄", key=f"refresh_value_{alarm_id}"):
                            try:
                                response = requests.get(f"{API_URL}/alarm/{alarm_id}/value")
                                if response.status_code == 200:
                                    new_value = response.json()["value"]
                                    st.session_state.alarm_values[alarm_id] = new_value
                                    st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Error refreshing value: {str(e)}")
                
                with col2:
                    st.markdown("### ⚙️ Settings")
                    st.write(f"**Pozo:** {alarm['pozo']}")
                    st.write(f"**Emails:** {', '.join(alarm['emails'])}")
                    active = st.checkbox("Active", value=alarm['active'], key=f"active_{alarm_id}")
                    if active != alarm['active']:
                        update_alarm(alarm_id, {"enabled": active})
                
                with col3:
                    st.markdown("### 🛠️ Actions")
                    if st.button("🧪 Test", key=f"test_{alarm_id}"):
                        test_alarm(alarm_id)
                    
                    # Delete button with confirmation
                    if st.session_state.delete_confirmation == alarm_id:
                        col3_1, col3_2 = st.columns(2)
                        with col3_1:
                            if st.button("✅ Confirm", key=f"confirm_{alarm_id}"):
                                delete_alarm(alarm_id)
                                st.session_state.delete_confirmation = None
                        with col3_2:
                            if st.button("❌ Cancel", key=f"cancel_{alarm_id}"):
                                st.session_state.delete_confirmation = None
                    else:
                        if st.button("🗑️ Delete", key=f"delete_{alarm_id}"):
                            st.session_state.delete_confirmation = alarm_id
    else:
        st.info("No alarms configured yet. Create one using the form above!")

    # Footer
    st.markdown("---")
    st.markdown("### 📊 System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Total Alarms: {len(st.session_state.alarms)}")
    with col2:
        st.write(f"Active Alarms: {sum(1 for a in st.session_state.alarms.values() if a['active'])}")

if __name__ == "__main__":
    main()