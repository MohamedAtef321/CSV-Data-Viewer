import streamlit as st
import pandas as pd
import os
import csv
from pathlib import Path
import re

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

def read_file_without_errors(file_path, delimiter=None, skip_rows=[], nrows=None):
    while True:
        if delimiter is None:
            delimiter = detect_delimiter(file_path)
        try:
            if nrows is not None:
                data = pd.read_csv(file_path, sep=delimiter, skiprows=lambda x : x+1 in skip_rows, nrows=nrows)
            else:
                data = pd.read_csv(file_path, sep=delimiter, skiprows=lambda x : x+1 in skip_rows)
        except pd.errors.ParserError as pe :
            error_line = extract_error_line_number(str(pe))
            print(f"Error in line {error_line}")
            skip_rows.append(error_line)
            data = read_file_without_errors(file_path, delimiter, skip_rows, nrows)
        return data


# Set page configuration
st.set_page_config(page_title="CSV Data Viewer", layout="wide")

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

# Create data directory if it doesn't exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

def load_csv(file_path):
    try:
        return read_file_without_errors(file_path)
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def get_csv_files():
    return [f for f in data_dir.glob("*.csv")]

# Sidebar
with st.sidebar:
    st.title("Data Selection")
    
    # # File upload
    # uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    # if uploaded_file:
    #     try:
    #         # Save uploaded file
    #         save_path = data_dir / uploaded_file.name
    #         with open(save_path, "wb") as f:
    #             f.write(uploaded_file.getvalue())
    #         st.success(f"File {uploaded_file.name} uploaded successfully!")
    #     except Exception as e:
    #         st.error(f"Error saving file: {str(e)}")
    
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

# Main content
st.title("📑 CSV Data Viewer")

if selected_file:
    df = load_csv(selected_file)
    
    if df is not None:
        # Filter section
        st.subheader("Filter Data")
        
        # Initialize session state for filters if not exists
        if 'active_filters' not in st.session_state:
            st.session_state.active_filters = []
            st.session_state.filter_values = {}
        
        # Add/Clear filter buttons
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("Add Filter"):
                st.session_state.active_filters.append(len(st.session_state.active_filters))
        with col2:
            if st.button("Clear Filters", type="secondary"):
                st.session_state.active_filters = []
                st.session_state.filter_values = {}
        
        # Display active filters
        for filter_id in st.session_state.active_filters[:]:  # Create a copy of the list to iterate
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 0.5])
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
                
                with col3:
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
