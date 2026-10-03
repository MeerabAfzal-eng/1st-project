import streamlit as st
import math

# Page configuration
st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

# Custom CSS for a real calculator compact grid
st.markdown("""
    <style>
    /* Main container padding */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Calculator screen styling */
    .stMarkdown > div.css-1r6slbo.e1nzirve0 {
        background-color: #0e1117 !important;
        color: #00ffcc !important;
        font-size: 32px !important;
        font-family: monospace !important;
        font-weight: bold !important;
        text-align: right !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border: 2px solid #4f46e5 !important;
        margin-bottom: 15px !important;
    }
    /* A simpler, more robust screen selector for Streamlit elements */
    div[data-testid="stMarkdownContainer"] > div.calc-display {
        background-color: #0e1117;
        color: #00ffcc;
        font-size: 32px;
        font-family: monospace;
        font-weight: bold;
        text-align: right;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #4f46e5;
        margin-bottom: 15px;
        min-height: 70px;
    }

    /* Compact button styling to force grid shape */
    div.stButton > button {
        width: 100% !important;
        height: 45px !important; /* Reduced height for compactness */
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: 1px solid #d1d5db !important;
        background-color: #f3f4f6 !important;
        color: #1f2937 !important;
        margin: 0px !important; /* Removes any default margins */
        padding: 2px !important;
    }
    div.stButton > button:hover {
        background-color: #e0e7ff !important;
        border-color: #4f46e5 !important;
        color: #4f46e5 !important;
    }
    /* Override for special '=' button color */
    div.stButton[data-testid="stButton-key_equal_button"] > button {
        background-color: #4f46e5 !important;
        color: white !important;
        border-color: #4f46e5 !important;
    }
    div.stButton[data-testid="stButton-key_equal_button"] > button:hover {
        background-color: #4338ca !important;
    }
    
    /* Adjust spacing between columns to make it tight */
    .row-widget.stHorizontal {
        gap: 5px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧮 Scientific Calculator")

# Initialize session state
if "calc_input" not in st.session_state:
    st.session_state.calc_input = ""

# Button click handler
def btn_pressed(val):
    if val == "C":
        st.session_state.calc_input = ""
    elif val == "⌫":
        st.session_state.calc_input = st.session_state.calc_input[:-1]
    elif val == "=":
        try:
            expr = st.session_state.calc_input
            expr = expr.replace('×', '*').replace('÷', '/')
            expr = expr.replace('sin(', 'math.sin(math.radians(')
            expr = expr.replace('cos(', 'math.cos(math.radians(')
            expr = expr.replace('tan(', 'math.tan(math.radians(')
            expr = expr.replace('log(', 'math.log10(')
            expr = expr.replace('ln(', 'math.log(')
            expr = expr.replace('√(', 'math.sqrt(')
            expr = expr.replace('^', '**')
            
            # Automatically close brackets
            open_brackets = expr.count('(') - expr.count(')')
            if open_brackets > 0:
                expr += ')' * open_brackets
                
            result = eval(expr)
            st.session_state.calc_input = str(result)
        except Exception:
            st.session_state.calc_input = "Error"
    elif val in ["sin", "cos", "tan", "log", "ln", "√"]:
        st.session_state.calc_input += f"{val}("
    else:
        st.session_state.calc_input += str(val)

# Screen Display
st.markdown(f'<div class="calc-display">{st.session_state.calc_input if st.session_state.calc_input else "0"}</div>', unsafe_allow_html=True)

# Button Layout Definitions (Standard Scientific Layout)
buttons_grid = [
    ["C", "⌫", "(", ")"],
    ["sin", "cos", "tan", "÷"],
    ["log", "ln", "√", "^"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "="]
]

# Render the grid using columns with tight gaps
for row in buttons_grid:
    cols = st.columns(len(row))
    for i, btn_label in enumerate(row):
        if btn_label == "=":
            # Special key for the '=' button
            if cols[i].button(btn_label, key="equal_button"):
                btn_pressed(btn_label)
                st.rerun()
        else:
            if cols[i].button(btn_label, key=f"btn_{btn_label}"):
                btn_pressed(btn_label)
                st.rerun()
