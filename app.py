import streamlit as st
import math

st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

# Custom CSS for Professional Grid Calculator
st.markdown("""
    <style>
    .calc-display {
        background-color: #0e1117;
        color: #00ffcc;
        font-size: 32px;
        font-family: monospace;
        font-weight: bold;
        text-align: right;
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #4f46e5;
        margin-bottom: 20px;
    }
    /* Button styling to look like a real calculator */
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        background-color: #f3f4f6;
        color: #1f2937;
        border: 1px solid #d1d5db;
    }
    div.stButton > button:hover {
        background-color: #4f46e5 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧮 Scientific Calculator")

# Session state for calculation string
if "calc_val" not in st.session_state:
    st.session_state.calc_val = ""

# Function to handle button logic
def press(val):
    if val == "C":
        st.session_state.calc_val = ""
    elif val == "⌫":
        st.session_state.calc_val = st.session_state.calc_val[:-1]
    elif val == "=":
        try:
            expr = st.session_state.calc_val
            expr = expr.replace('×', '*').replace('÷', '/')
            expr = expr.replace('sin(', 'math.sin(math.radians(')
            expr = expr.replace('cos(', 'math.cos(math.radians(')
            expr = expr.replace('tan(', 'math.tan(math.radians(')
            expr = expr.replace('log(', 'math.log10(')
            expr = expr.replace('ln(', 'math.log(')
            expr = expr.replace('√(', 'math.sqrt(')
            expr = expr.replace('^', '**')
            
            # Balance brackets
            op_b = expr.count('(') - expr.count(')')
            if op_b > 0:
                expr += ')' * op_b
                
            res = eval(expr)
            st.session_state.calc_val = str(res)
        except Exception:
            st.session_state.calc_val = "Error"
    elif val in ["sin", "cos", "tan", "log", "ln", "√"]:
        st.session_state.calc_val += f"{val}("
    else:
        st.session_state.calc_val += str(val)

# Screen Output
display_text = st.session_state.calc_val if st.session_state.calc_val else "0"
st.markdown(f'<div class="calc-display">{display_text}</div>', unsafe_allow_html=True)

# Calculator Keypad Layout
rows = [
    ["C", "⌫", "(", ")"],
    ["sin", "cos", "tan", "÷"],
    ["log", "ln", "√", "^"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "="]
]

# Render rows properly using columns
for row in rows:
    cols = st.columns(len(row))
    for i, key in enumerate(row):
        if cols[i].button(key, key=f"calc_btn_{key}"):
            press(key)
            st.rerun()
