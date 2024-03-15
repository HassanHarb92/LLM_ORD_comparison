import streamlit as st
import pandas as pd
import json
import os
import copy

# Assuming your read_json function remains the same
def read_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def print_dicts_css(dict1, dict2):
    # Your recursive_print function remains the same
    def recursive_print(dict1, dict2, prefix=""):
        rows = []
        if isinstance(dict1, dict) and isinstance(dict2, dict):
            keys_sorted = sorted(dict1, key=lambda k: list(dict1.keys()).index(k))
            for key in keys_sorted:
                rows += recursive_print(dict1.get(key, "-"), dict2.get(key, "-"), prefix=prefix + str(key) + ": ")
        elif isinstance(dict1, list) and isinstance(dict2, list):
            for idx, (val1, val2) in enumerate(zip(dict1, dict2)):
                rows += recursive_print(val1, val2, prefix=prefix + f"[{idx}]: ")
        else:
            is_same = dict1 == dict2
            rows.append({"Path": f"{prefix}", "Ground Truth": str(dict1), "LLM Result": str(dict2), "Is Same": is_same})
        return rows
    
    return recursive_print(dict1, dict2)

st.set_page_config(layout="wide")
st.title('LLM ORD Reaction Parser')
st.markdown('## JSON Comparison Result')

# 1. List available JSON files
directory = '.'  # Specify the directory containing your JSON files
json_files = [f for f in os.listdir(directory) if f.endswith('.json')]

# 2. Create dropdowns for file selection
col1, col2 = st.columns(2)
with col1:
    selected_json1 = st.selectbox('Select the first JSON file:', json_files, index=0)  # Default to first file
with col2:
    selected_json2 = st.selectbox('Select the second JSON file:', json_files, index=1 if len(json_files) > 1 else 0)  # Default to second file

# 3. Load and compare the selected JSON files
json1 = read_json(selected_json1)
json2 = read_json(selected_json2)

# Assuming json1 and json2 are lists and you want the 'input_text' from the first item
if isinstance(json1, list) and len(json1) > 0:
    ground_truth_text = json1[0].get('input_text', 'No input_text found in JSON 1')
else:
    ground_truth_text = 'JSON 1 is not a list or is empty'

if isinstance(json2, list) and len(json2) > 0:
    llm_result_text = json2[0].get('input_text', 'No input_text found in JSON 2')
else:
    llm_result_text = 'JSON 2 is not a list or is empty'


rows = print_dicts_css(json1, json2)
df = pd.DataFrame(rows)
df['Path'] = df['Path'].str.replace(r'\[0\]:', '', regex=True)
perc_true = ((df["Is Same"].sum() - 1) / (df.shape[0]-1)) * 100
col1, col2 = st.columns(2)  # Creates two columns

with col1:  # With the first column
    st.text_area("Ground Truth", ground_truth_text, height=300)

with col2:  # With the second column
    st.text_area("LLM Result", llm_result_text, height=300)

# Streamlit UI

# Display the percent accuracy
#st.info(f"Percent accuracy: {perc_true:.2f}%")

# Conditional Formatting Workaround: Highlight mismatches
def highlight_mismatches(s):
    is_mismatch = s["Is Same"] == False
    return ['background-color: #F7FE2E' if is_mismatch else '' for _ in s]

# Assuming you've already prepared your DataFrame 'df'

# Calculate percent accuracy as before
if 'Path' in df.columns and df.iloc[0]['Path'] == 'input_text:':
    perc_true = ((df.iloc[1:]["Is Same"].sum()) / (df.shape[0] - 1)) * 100
    # Drop the first row as it's labeled 'input_text'
    df = df.drop(df.index[0]).reset_index(drop=True)
else:
    perc_true = ((df["Is Same"].sum()) / df.shape[0]) * 100

st.markdown(f"## Percent accuracy: {perc_true:.2f}%")
df = df[~df["Path"].str.contains("input_text", na=False)]

# Function to apply conditional formatting and return HTML

def dataframe_to_html_with_style(df):
    # Clone the DataFrame for styling
    styled_df = df.copy()
    
    # Apply conditional formatting
    styled_df['Is Same'] = styled_df['Is Same'].map(lambda x: 'Yes' if x else 'No')
    styled_df['LLM Result'] = styled_df.apply(
        lambda row: f'<span style="background-color:#F7FE2E;">{row["LLM Result"]}</span>' if row['Is Same'] == 'No' else row['LLM Result'], axis=1)
    
    # Remove specified substrings from the "Path" column
    removals = ["output_reaction_inputs", "output_reaction_conditions"]
    for removal in removals:
        styled_df['Path'] = styled_df['Path'].str.replace(removal + ":", "", regex=False).str.strip()

    # Sort the DataFrame by the "Path" column in alphabetical order
    styled_df = styled_df.sort_values(by='Path')
    
    # Convert to HTML
    return styled_df.to_html(escape=False)

view_option = st.radio(
    "Choose a visualization option:",
    ('Table View', 'Tree View')
)

def display_tree_view(obj1, obj2, path=''):
    # Handle case when both are dictionaries
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        for key in sorted(set(obj1.keys()).union(obj2.keys())):
            val1 = obj1.get(key, "N/A")
            val2 = obj2.get(key, "N/A")
            new_path = f"{path}.{key}" if path else key
            if isinstance(val1, (dict, list)) and isinstance(val2, (dict, list)):
                with st.expander(f"{new_path}", expanded=True):
                    display_tree_view(val1, val2, new_path)
            elif val1 != val2:
                st.markdown(f"**{new_path}:** `{val1}` ≠ `{val2}`", unsafe_allow_html=True)
            else:
                st.text(f"{new_path}: {val1}")
    # Handle case when both are lists
    elif isinstance(obj1, list) and isinstance(obj2, list):
        for index, (val1, val2) in enumerate(zip(obj1, obj2)):
            new_path = f"{path}[{index}]"
            if isinstance(val1, (dict, list)) and isinstance(val2, (dict, list)):
                with st.expander(f"{new_path}", expanded=True):
                    display_tree_view(val1, val2, new_path)
            elif val1 != val2:
                st.markdown(f"**{new_path}:** `{val1}` ≠ `{val2}`", unsafe_allow_html=True)
            else:
                st.text(f"{new_path}: {val1}")
    # Handle case when types don't match or other types
    else:
        st.markdown(f"**{path}:** `{obj1}` ≠ `{obj2}`", unsafe_allow_html=True)

import streamlit as st
import streamlit as st
import copy

# Define the annotate_differences function to compare json1 against json2
# and annotate json2 with the differences
def annotate_differences(base, compare, path=""):
    if isinstance(base, dict) and isinstance(compare, dict):
        for key in compare:
            if key in base:
                if base[key] != compare[key]:
                    if isinstance(base[key], (dict, list)) and isinstance(compare[key], (dict, list)):
                        annotate_differences(base[key], compare[key], path=f"{path}.{key}" if path else key)
                    else:
                        compare[key] = f"{compare[key]} (***DIFFERENCE***)"
            else:
                compare[key] = f"{compare[key]} (***ADDITIONAL***)"
        for key in base:
            if key not in compare:
                compare[key] = "***MISSING***"
    elif isinstance(base, list) and isinstance(compare, list):
        min_len = min(len(base), len(compare))
        for i in range(min_len):
            if base[i] != compare[i]:
                if isinstance(base[i], (dict, list)) and isinstance(compare[i], (dict, list)):
                    annotate_differences(base[i], compare[i], path=f"{path}[{i}]")
                else:
                    compare[i] = f"{compare[i]} (***DIFFERENCE***)"
        if len(compare) > len(base):
            for i in range(len(base), len(compare)):
                compare[i] = f"{compare[i]} (***ADDITIONAL***)"
        elif len(compare) < len(base):
            compare.extend(["***MISSING***"] * (len(base) - len(compare)))
    else:
        if base != compare:
            return f"{compare} (***DIFFERENCE***)"

# Adjusted "Tree View" option
if view_option == 'Table View':
    html = dataframe_to_html_with_style(df)
    st.markdown(html, unsafe_allow_html=True)
elif view_option == 'Tree View':
    json1 = read_json(selected_json1)
    json2 = read_json(selected_json2)
    
    # Annotate json2 based on differences from json1
    annotated_json2 = copy.deepcopy(json2)
    annotate_differences(json1, annotated_json2)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original JSON (json1)")
        st.json(json1)
    with col2:
        st.subheader("Annotated JSON (json2)")
        st.json(annotated_json2)

