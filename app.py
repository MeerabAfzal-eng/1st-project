import streamlit as st
import math

# Page Configuration
st.set_page_config(
    page_title="Professional Scientific Calculator",
    page_icon="🧮",
    layout="centered"
)

# Professional CSS Styling (Modern Dark Theme & Clean Buttons)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .calculator-title {
        text-align: center;
        color: #1f2937;
        font-weight: 700;
        margin-bottom: 20px;
    }
    .calc-screen {
        background: linear-gradient(135deg, #1e1e2f 0%, #11111d 100%);
        color: #00ffcc;
        font-size: 36px;
        font-family: monospace;
        font-weight: bold;
        text-align: right;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #4f46e5;
        box-shadow: inset 0 4px 6px rgba(0,0,0,0.5);
        margin-bottom: 25px;
        word-wrap: break-word;
        word-break: break-all;
    }
    /* Professional button styling */
    .stButton > button {
        width: 100%;
        height: 55px;
        font-size: 20px;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        background-color: #ffffff;
        color: #1f2937;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #4f46e5;
        color: #ffffff;
        border: 1px solid #4f46e5;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='calculator-title'>🧮 Professional Scientific Calculator</h1>", unsafe_allow_html=True)

# Session State Initialization
if "expression" not in st.session_state:
    st.session_state.expression = ""

# Button Click Logic
def handle_click(val):
    if val == "C":
        st.session_state.expression = ""
    elif val == "⌫":
        st.session_state.expression = st.session_state.expression[:-1]
    elif val == "=":
        try:
            expr = st.session_state.expression
            # Safe replacements for evaluation
            expr = expr.replace('×', '*').replace('÷', '/')
            expr = expr.replace('sin(', 'math.sin(math.radians(')
            expr = expr.replace('cos(', 'math.cos(math.radians(')
            expr = expr.replace('tan(', 'math.tan(math.radians(')
            expr = expr.replace('log(', 'math.log10(')
            expr = expr.replace('ln(', 'math.log(')
            expr = expr.replace('√(', 'math.sqrt(')
            expr = expr.replace('^', '**')
            
            # Close unclosed brackets automatically
            open_b = expr.count('(') - expr.count(')')
            if open_b > 0:
                expr += ')' * open_b
                
            res = eval(expr)
            st.session_state.expression = str(res)
        except Exception:
            st.session_state.expression = "Error"
    elif val in ["sin", "cos", "tan", "log", "ln", "√"]:
        st.session_state.expression += f"{val}("
    else:
        st.session_state.expression += str(val)

# Keyboard Input Box for PC typing
user_typing = st.text_input("Type Expression (PC Keyboard Support):", value=st.session_state.expression, key="text_input_box")

if user_typing != st.session_state.expression:
    st.session_state.expression = user_typing

# Display Screen
display_val = st.session_state.expression if st.session_state.expression else "0"
st.markdown(f'<div class="calc-screen">{display_val}</div>', unsafe_allow_html=True)

# Calculator Keypad Layout
buttons_layout = [
    ["C", "⌫", "(", ")"],
    ["sin", "cos", "tan", "÷"],
    ["log", "ln", "√", "^"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "="]
]

# Render Buttons in Grid
for row in buttons_layout:
    cols = st.columns(len(row))
    for i, btn in enumerate(row):
        if cols[i].button(btn, key=f"key_{btn}"):
            handle_click(btn)
            st.rerun()
