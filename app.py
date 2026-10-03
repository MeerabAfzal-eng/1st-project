import streamlit as st
import math

st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

st.markdown("""
    <style>
    .calculator-screen {
        background-color: #0e1117;
        color: #00ffcc;
        font-size: 32px;
        font-weight: bold;
        text-align: right;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #31333F;
        margin-bottom: 15px;
        min-height: 70px;
    }
    .stButton>button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧮 Scientific Calculator")

# Session state ko initialize karna taaki calculation yaad rahe
if "calc_input" not in st.session_state:
    st.session_state.calc_input = ""

def btn_click(val):
    if val == "C":
        st.session_state.calc_input = ""
    elif val == "⌫":
        st.session_state.calc_input = st.session_state.calc_input[:-1]
    elif val == "=":
        try:
            # Safe evaluation for math operations
            expression = st.session_state.calc_input
            expression = expression.replace('×', '*').replace('÷', '/')
            expression = expression.replace('sin(', 'math.sin(math.radians(')
            expression = expression.replace('cos(', 'math.cos(math.radians(')
            expression = expression.replace('tan(', 'math.tan(math.radians(')
            expression = expression.replace('log(', 'math.log10(')
            expression = expression.replace('ln(', 'math.log(')
            expression = expression.replace('√(', 'math.sqrt(')
            expression = expression.replace('^', '**')
            
            # Agar bracket open hain to close karna
            open_brackets = expression.count('(') - expression.count(')')
            if open_brackets > 0:
                expression += ')' * open_brackets
                
            result = eval(expression)
            st.session_state.calc_input = str(result)
        except Exception:
            st.session_state.calc_input = "Error"
    elif val in ["sin", "cos", "tan", "log", "ln", "√"]:
        st.session_state.calc_input += f"{val}("
    else:
        st.session_state.calc_input += str(val)

# Keyboard input support ke liye text input
user_input = st.text_input("Keyboard Input (Type here or use GUI buttons below):", value=st.session_state.calc_input, key="keyboard_box")

# Agar user ne keyboard se type kiya ho to state update karein
if user_input != st.session_state.calc_input:
    st.session_state.calc_input = user_input

st.markdown(f'<div class="calculator-screen">{st.session_state.calc_input if st.session_state.calc_input else "0"}</div>', unsafe_allow_html=True)

# Calculator Buttons Layout
buttons = [
    ["C", "⌫", "(", ")"],
    ["sin", "cos", "tan", "÷"],
    ["log", "ln", "√", "^"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["0", ".", "="]
]

for row in buttons:
    cols = st.columns(len(row))
    for i, btn in enumerate(row):
        if btn == "=":
            if cols[i].button(btn, key=f"btn_{btn}", use_container_width=True):
                btn_click(btn)
                st.rerun()
        else:
            if cols[i].button(btn, key=f"btn_{btn}", use_container_width=True):
                btn_click(btn)
                st.rerun()
