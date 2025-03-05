import pandas as pd
import json
import os

def find_header_row(file_path, column_name):
    """
    Finds the row index where the specified column name appears.

    Args:
        file_path (str): Path to the CSV or Excel file.
        column_name (str): The name of the column to search for.

    Returns:
        int: The row index if found, else None.
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.csv':
        df_raw = pd.read_csv(file_path, encoding="utf-8", header=None)
    elif file_ext in ['.xlsx', '.xls']:
        df_raw = pd.read_excel(file_path, header=None)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Please use CSV or Excel files.")
    
    for index, row in df_raw.iterrows():
        if column_name in row.values:
            return index
    return None

def read_excel_thresholds(file_path):
    """
    Reads a CSV or Excel file and extracts serial numbers and their thresholds.

    Args:
        file_path (str): Path to the CSV or Excel file.

    Returns:
        dict: Dictionary with serial numbers as keys and thresholds as values.
    """
    column_name = "NUM. DE SERIE DATALOGGER"
    header_row = find_header_row(file_path, column_name)

    if header_row is None:
        print(f"Error: Column '{column_name}' not found in the file.")
        return None

    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext == '.csv':
        df = pd.read_csv(file_path, encoding="utf-8", header=header_row)
    elif file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, header=header_row)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Please use CSV or Excel files.")

    threshold_dict = {}
    for index, row in df.iterrows():
        try:
            if pd.isna(row[column_name]):
                print(f"Skipping row {index + 1}: Serial number is NaN")
                continue
                
            serial_number = str(row[column_name])
            if serial_number.startswith('XLG'):
                serial_number = serial_number[3:]  # Remove 'XLG'

            threshold_column = "Threshold" if "Threshold" in df.columns else "Treshhold"
            
            if threshold_column in row and pd.notna(row[threshold_column]):
                threshold = float(row[threshold_column])
            else:
                threshold = -1.0  # Set to -1 if threshold is missing or NaN
            
            threshold_dict[serial_number] = threshold
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error processing row {index + 1}: {str(e)}")
            continue

    return threshold_dict