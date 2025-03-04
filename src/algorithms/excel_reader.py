import pandas as pd
import json

def find_header_row(file_path, column_name):
    """
    Finds the row index where the specified column name appears.

    Args:
        file_path (str): Path to the CSV file.
        column_name (str): The name of the column to search for.

    Returns:
        int: The row index if found, else None.
    """
    df_raw = pd.read_csv(file_path, encoding="utf-8", header=None)
    for index, row in df_raw.iterrows():
        if column_name in row.values:
            return index
    return None

def read_excel_thresholds(file_path):
    """
    Reads a CSV file and extracts serial numbers and their thresholds.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        dict: Dictionary with serial numbers as keys and thresholds as values.
    """
    column_name = "NUM. DE SERIE DATALOGGER"
    header_row = find_header_row(file_path, column_name)

    if header_row is None:
        print(f"Error: Column '{column_name}' not found in the file.")
        return None

    # Read CSV with the correct header row
    df = pd.read_csv(file_path, encoding="utf-8", header=header_row)

    threshold_dict = {}
    for index, row in df.iterrows():
        try:
            serial_number = str(row[column_name])
            if serial_number.startswith('XLG'):
                serial_number = serial_number[3:]  # Remove 'XLG'

            # Handle possible column name variations
            threshold_column = "Threshold" if "Threshold" in df.columns else "Treshhold"
            
            # Check if threshold exists and is not NaN
            if threshold_column in row and pd.notna(row[threshold_column]):
                threshold = float(row[threshold_column])
            else:
                threshold = -1.0  # Set to -1 if threshold is missing or NaN
            
            threshold_dict[serial_number] = threshold
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error processing row {index + 1}: {str(e)}")
            continue

    return threshold_dict

# Example usage
file_path = "archivo.csv"
thresholds = read_excel_thresholds(file_path)

# Write JSON file
with open('thresholds.json', 'w') as f:
    json.dump(thresholds, f)    