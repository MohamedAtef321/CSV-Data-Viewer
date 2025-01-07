import streamlit as st
import pandas as pd
import os
import csv
from pathlib import Path
import re
import csv
import pandas as pd

# Create data directory if it doesn't exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

slicer_length = 10**6
st.session_state.start_row = 0
st.session_state.end_row = slicer_length//10

# Functions Definition
def detect_delimiter(file_path):
    with open(file_path, 'r') as file:
        # Read the first line to detect the delimiter
        first_line = file.readline()
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(first_line).delimiter
        return delimiter

def extract_error_line_number(error_message):
    match = re.search(r"line (\d+)", error_message)
    if match:
        return int(match.group(1))
    else:
        return None

@st.cache_data
def read_file_without_errors(file_path, delimiter=None, skip_rows=[], offset=0, nrows=None):
    while True:
        if delimiter is None:
            delimiter = detect_delimiter(file_path)
        try:
            if nrows is not None:
                data = pd.read_csv(file_path, sep=delimiter, skiprows=list(range(offset)).extend([x+1 for x in skip_rows]), nrows=nrows)
            else:
                data = pd.read_csv(file_path, sep=delimiter, skiprows=list(range(offset)).extend([x+1 for x in skip_rows]))
        except pd.errors.ParserError as pe :
            error_line = extract_error_line_number(str(pe))
            print(f"Error in line {error_line}")
            skip_rows.append(error_line)
            data = read_file_without_errors(file_path, delimiter, skip_rows, offset, nrows)
        return data
    
@st.cache_data
def load_csv(file_path, offset=0, nrows=None):
    try:
        return read_file_without_errors(file_path, offset=offset, nrows=nrows)
    except Exception as e:
        st.error(f"Error loading file ({file_path}) : {str(e)}")
        return None

def get_csv_files():
    return [f for f in data_dir.glob("*.csv")]

def app():



    # Set page configuration
    # st.set_page_config(page_title="CSV Data Viewer", layout="wide")

    # Custom CSS for button alignment and colors
    st.markdown("""
        <style>
        .stButton {
            margin-top: 25px;
        }
        .stButton > button[data-baseweb="button"] {
            background-color: #00cc00;
            border-color: #00cc00;
        }
        .stButton > button[data-baseweb="button"]:hover {
            background-color: #009900;
            border-color: #009900;
        }
        </style>
        """, unsafe_allow_html=True)



        
    # File selection
    csv_files = get_csv_files()
    if csv_files:
        selected_file = st.selectbox(
            "Select CSV file",
            options=csv_files,
            format_func=lambda x: x.name
        )
    else:
        st.info("No CSV files available. Please upload one.")
        selected_file = None


    if selected_file:
        # Create a range slider for start and end row indices
        start_end_indices = st.slider(
            "Select Start and End Row Indices",
            0,  # Minimum value (start of DataFrame)
            slicer_length,  # Maximum value (end of DataFrame)
            (st.session_state.start_row, st.session_state.end_row),  # Default start and end values
        )

        # Extract start and end row indices from the slider
        st.session_state.start_row, st.session_state.end_row = start_end_indices
        
        # col1, col2 = st.columns(2)
        # st.session_state.start_row = col1.number_input(
        #     "Start Row",
        #     min_value=0,
        #     max_value=slicer_length,
        #     value=st.session_state.start_row,
        #     step=1
        # )
        # st.session_state.end_row = col2.number_input(
        #     "End Row",
        #     min_value=st.session_state.start_row,
        #     max_value=slicer_length,
        #     value=st.session_state.end_row,
        #     step=1
        # )
        # st.write(f"Selected Rows from {st.session_state.start_row} to {st.session_state.end_row}.")

        df = load_csv(selected_file, offset=st.session_state.start_row, nrows=st.session_state.end_row - st.session_state.start_row + 1)
        
        if df is not None:
            # Filter section
            st.subheader("Filter Data")
            
            # Initialize session state for filters if not exists
            if 'active_filters' not in st.session_state:
                st.session_state.active_filters = []
                st.session_state.filter_values = {}
                st.session_state.filter_none = {}
            
            # Add/Clear filter buttons
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("Add Filter"):
                    st.session_state.active_filters.append(len(st.session_state.active_filters))
            with col2:
                if st.button("Clear Filters", type="secondary"):
                    st.session_state.active_filters = []
                    st.session_state.filter_values = {}
                    st.session_state.filter_none = {}
            
            # Display active filters
            for filter_id in st.session_state.active_filters[:]:  # Create a copy of the list to iterate
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    with col1:
                        selected_column = st.selectbox(
                            f"Select column for filter {filter_id + 1}",
                            options=df.columns,
                            key=f"col_{filter_id}"
                        )

                    with col2:
                        if selected_column:
                            if df[selected_column].dtype in ['object', 'string']:
                                # For text columns
                                unique_values = df[selected_column].unique()
                                st.session_state.filter_values[filter_id] = {
                                    'column': selected_column,
                                    'value': st.multiselect(
                                        f"Filter values for {selected_column}",
                                        options=unique_values,
                                        key=f"val_{filter_id}"
                                    ),
                                    'type': 'categorical'
                                }
                            elif df[selected_column].dtype in ['int64', 'float64']:
                                # For numeric columns
                                min_val, max_val = float(df[selected_column].min()), float(df[selected_column].max())
                                st.session_state.filter_values[filter_id] = {
                                    'column': selected_column,
                                    'value': st.slider(
                                        f"Range for {selected_column}",
                                        min_val, max_val,
                                        (min_val, max_val),
                                        key=f"val_{filter_id}"
                                    ),
                                    'type': 'numeric'
                                }

                    # New Selectbox to filter non-null values
                    with col3:
                        non_null_option = st.selectbox(
                            label="Data",
                            options=["All", "Exists", "Doesn't exist"],
                            key=f"non_null_{filter_id}",
                            # label_visibility="collapsed"
                        )
                        # Apply non-null filtering if selected
                        if non_null_option == "Exists":
                            df = df[df[selected_column].notna()]
                        elif non_null_option == "Doesn't exist":
                            df = df[df[selected_column].isna()]
                    with col4:
                        if st.button("Remove", key=f"remove_{filter_id}", type="primary", help="Remove this filter"):
                            st.session_state.active_filters.remove(filter_id)
                            if filter_id in st.session_state.filter_values:
                                del st.session_state.filter_values[filter_id]
                                
            # Search button
            if st.button("Search", type="primary", use_container_width=True, key="search_button"):
                filtered_df = df.copy()
                
                # Apply all active filters
                for filter_id, filter_info in st.session_state.filter_values.items():
                    if filter_info['value']:  # If filter is set
                        col = filter_info['column']
                        if filter_info['type'] == 'numeric':
                            filtered_df = filtered_df[
                                (filtered_df[col] >= filter_info['value'][0]) & 
                                (filtered_df[col] <= filter_info['value'][1])
                            ]
                        elif filter_info['type'] == 'categorical':
                            if filter_info['value']:  # If any values selected
                                filtered_df = filtered_df[filtered_df[col].isin(filter_info['value'])]
                
                # Display data
                filtered_df.reset_index(drop=True, inplace=True)
                st.subheader("Data Preview")
                st.write(f"Filtered Data ({filtered_df.shape[0]} rows)")
                st.dataframe(filtered_df)

                # Download button
                if not filtered_df.empty:
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="Download filtered data as CSV",
                        data=csv,
                        file_name="filtered_data.csv",
                        mime="text/csv"
                    )

import json

# Load the password from config.json
def load_password():
    try:
        with open("config.json", "r") as file:
            config = json.load(file)
            return config.get("password")
    except FileNotFoundError:
        st.error("Configuration file 'config.json' not found.")
        return None

# Retrieve the password
APP_PASSWORD = load_password()

# Set page configuration
st.set_page_config(page_title="CSV Data Viewer", layout="wide")

# Main content
st.title("📑 CSV Data Viewer")
if APP_PASSWORD:
    password = st.text_input("Enter the password:", type="password")

    if password == APP_PASSWORD:
        st.success("Access granted! 🎉")
        # Place the main content of your app here
        app()
    else:
        if password:
            st.error("Access denied. Please enter the correct password.")
