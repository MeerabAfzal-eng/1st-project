
import streamlit as st
import math
import re
from datetime import datetime

# ============================================================
# SCIENTIFIC CALCULATOR - STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Scientific Calculator",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ------------------------- State ----------------------------

DEFAULTS = {
    "expression": "",
    "result": "",
    "memory": 0.0,
    "answer": 0.0,
    "angle_mode": "DEG",
    "history": [],
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# -------------------------- CSS -----------------------------

st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}

    .stApp {
        background: #eef2f7;
    }

    .block-container {
        max-width: 560px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .calculator {
        background: #20242b;
        border: 1px solid #343a44;
        border-radius: 26px;
        padding: 22px;
        box-shadow: 0 18px 45px rgba(20, 25, 35, 0.25);
    }

    .brand {
        color: #f5f7fa;
        font-size: 25px;
        font-weight: 700;
        letter-spacing: .3px;
        margin-bottom: 14px;
    }

    .brand span {
        color: #58d68d;
    }

    .display {
        background: #11151a;
        border: 2px solid #3c4652;
        border-radius: 15px;
        min-height: 105px;
        padding: 12px 16px;
        margin-bottom: 12px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        overflow: hidden;
    }

    .display-expression {
        color: #aeb7c2;
        font-size: 16px;
        min-height: 25px;
        text-align: right;
        white-space: nowrap;
        overflow-x: auto;
    }

    .display-result {
        color: #f8fafc;
        font-size: 36px;
        font-weight: 600;
        line-height: 1.15;
        text-align: right;
        white-space: nowrap;
        overflow-x: auto;
    }

    .mode {
        color: #58d68d;
        font-size: 12px;
        font-weight: 700;
        text-align: right;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 8px;
    }

    div.stButton > button {
        width: 100%;
        min-height: 48px;
        border-radius: 11px;
        border: 1px solid #454d59;
        background: #2b3038;
        color: #f4f6f8;
        font-size: 16px;
        font-weight: 600;
        transition: all .12s ease;
    }

    div.stButton > button:hover {
        border-color: #58d68d;
        color: #ffffff;
        background: #343b45;
    }

    div.stButton > button:active {
        transform: scale(.97);
    }

    /* Accent buttons */
    .accent div.stButton > button {
        background: #58d68d;
        border-color: #58d68d;
        color: #11151a;
    }

    .accent div.stButton > button:hover {
        background: #73e2a0;
        border-color: #73e2a0;
        color: #11151a;
    }

    /* Operator / utility buttons */
    .operator div.stButton > button {
        background: #3a414c;
    }

    .danger div.stButton > button {
        color: #ff8f8f;
    }

    .tiny div.stButton > button {
        min-height: 38px;
        font-size: 13px;
    }

    .history-title {
        color: #c7ced7;
        font-size: 14px;
        font-weight: 700;
        margin: 14px 0 7px;
    }

    .history-item {
        background: #171b21;
        border-radius: 9px;
        padding: 7px 10px;
        margin: 5px 0;
        color: #cbd2da;
        font-size: 13px;
        overflow-x: auto;
    }

    .help {
        color: #7f8995;
        text-align: center;
        font-size: 12px;
        margin-top: 12px;
    }

    /* Hide Streamlit button keyboard focus outline */
    button:focus {
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------- Math engine ------------------------

def to_rad(x):
    return math.radians(x) if st.session_state.angle_mode == "DEG" else x

def from_rad(x):
    return math.degrees(x) if st.session_state.angle_mode == "DEG" else x

def fmt(x):
    if isinstance(x, bool):
        return str(x)
    if abs(x) < 1e-12:
        x = 0.0
    if float(x).is_integer():
        return str(int(x))
    return f"{x:.12g}"

def safe_factorial(x):
    if x < 0 or not float(x).is_integer():
        raise ValueError("Factorial needs a non-negative integer.")
    return math.factorial(int(x))

def make_namespace():
    a = st.session_state.angle_mode
    return {
        # Constants
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,

        # Basic
        "abs": abs,
        "round": round,

        # Powers / roots
        "sqrt": math.sqrt,
        "cbrt": getattr(math, "cbrt", lambda x: math.copysign(abs(x) ** (1/3), x)),
        "pow": pow,

        # Logs / exponential
        "ln": math.log,
        "log": math.log10,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,

        # Trigonometry
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": lambda x: math.tan(to_rad(x)),
        "asin": lambda x: from_rad(math.asin(x)),
        "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),

        # Hyperbolic
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,

        # Other scientific functions
        "factorial": safe_factorial,
        "floor": math.floor,
        "ceil": math.ceil,
        "degrees": math.degrees,
        "radians": math.radians,

        # Calculator memory / previous answer
        "Ans": st.session_state.answer,
        "M": st.session_state.memory,
    }

ALLOWED_NAMES = set(make_namespace().keys())

def prepare_expression(expr):
    """Convert calculator-style syntax to safe Python expression."""
    expr = expr.strip()
    if not expr:
        raise ValueError("Enter an expression.")

    # Visual symbols -> Python
    replacements = {
        "×": "*",
        "÷": "/",
        "−": "-",
        "π": "pi",
        "√": "sqrt",
        "²": "**2",
        "³": "**3",
        "^": "**",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)

    # Percent: 50% -> (50/100)
    expr = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', expr)

    # Factorial: 5! -> factorial(5)
    # Repeated factorial such as 3!! is intentionally not accepted.
    expr = re.sub(r'(\d+(?:\.\d+)?)!', r'factorial(\1)', expr)

    # Reject suspicious characters before eval.
    if not re.fullmatch(r"[0-9a-zA-Z_+\-*/().,\s%]*", expr):
        raise ValueError("Invalid character in expression.")

    # Only allow known function/constant names.
    names = re.findall(r"[A-Za-z_]\w*", expr)
    unknown = [name for name in names if name not in ALLOWED_NAMES]
    if unknown:
        raise ValueError(f"Unknown function/name: {unknown[0]}")

    return expr

def calculate(expr):
    prepared = prepare_expression(expr)
    value = eval(
        prepared,
        {"__builtins__": {}},
        make_namespace(),
    )
    if isinstance(value, complex) or not math.isfinite(float(value)):
        raise ValueError("Math error.")
    return float(value)

# ----------------------- Actions ----------------------------

def add_text(value):
    st.session_state.expression += value
    st.session_state.result = ""

def clear_all():
    st.session_state.expression = ""
    st.session_state.result = ""

def backspace():
    st.session_state.expression = st.session_state.expression[:-1]
    st.session_state.result = ""

def do_equals():
    expr = st.session_state.expression
    try:
        value = calculate(expr)
        result = fmt(value)
        st.session_state.result = result
        st.session_state.answer = value
        st.session_state.history.insert(0, {
            "expression": expr,
            "result": result,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        st.session_state.history = st.session_state.history[:12]
    except Exception as exc:
        st.session_state.result = f"Error: {exc}"

def unary(function_name):
    if not st.session_state.expression:
        return
    st.session_state.expression = f"{function_name}({st.session_state.expression})"
    st.session_state.result = ""

def square():
    if st.session_state.expression:
        st.session_state.expression = f"({st.session_state.expression})**2"
        st.session_state.result = ""

def cube():
    if st.session_state.expression:
        st.session_state.expression = f"({st.session_state.expression})**3"
        st.session_state.result = ""

def reciprocal():
    if st.session_state.expression:
        st.session_state.expression = f"1/({st.session_state.expression})"
        st.session_state.result = ""

def toggle_sign():
    if st.session_state.expression:
        st.session_state.expression = f"-({st.session_state.expression})"
        st.session_state.result = ""

def toggle_angle():
    st.session_state.angle_mode = "RAD" if st.session_state.angle_mode == "DEG" else "DEG"

def memory_clear():
    st.session_state.memory = 0.0

def memory_add():
    try:
        value = calculate(st.session_state.expression or str(st.session_state.answer))
        st.session_state.memory += value
    except Exception:
        pass

def memory_subtract():
    try:
        value = calculate(st.session_state.expression or str(st.session_state.answer))
        st.session_state.memory -= value
    except Exception:
        pass

def memory_recall():
    st.session_state.expression += fmt(st.session_state.memory)

def use_answer():
    st.session_state.expression += fmt(st.session_state.answer)

def clear_history():
    st.session_state.history = []

# ------------------------- UI -------------------------------

st.markdown('<div class="calculator">', unsafe_allow_html=True)

st.markdown(
    '<div class="brand">🧮 <span>Scientific</span> Calculator</div>',
    unsafe_allow_html=True,
)

# Display
display_expr = st.session_state.expression or "0"
display_result = st.session_state.result or "0"

st.markdown(
    f"""
    <div class="display">
        <div class="mode">{st.session_state.angle_mode} MODE</div>
        <div class="display-expression">{display_expr}</div>
        <div class="display-result">{display_result}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Memory row
cols = st.columns(5)
memory_buttons = [
    ("MC", memory_clear),
    ("MR", memory_recall),
    ("M+", memory_add),
    ("M−", memory_subtract),
    ("Ans", use_answer),
]
for col, (label, func) in zip(cols, memory_buttons):
    with col:
        st.button(label, key=f"mem_{label}", on_click=func, use_container_width=True)

# Scientific functions
rows = [
    [
        ("sin", lambda: add_text("sin(")),
        ("cos", lambda: add_text("cos(")),
        ("tan", lambda: add_text("tan(")),
        ("sin⁻¹", lambda: add_text("asin(")),
        ("cos⁻¹", lambda: add_text("acos(")),
        ("tan⁻¹", lambda: add_text("atan(")),
    ],
    [
        ("sinh", lambda: add_text("sinh(")),
        ("cosh", lambda: add_text("cosh(")),
        ("tanh", lambda: add_text("tanh(")),
        ("ln", lambda: add_text("ln(")),
        ("log", lambda: add_text("log(")),
        ("√", lambda: add_text("sqrt(")),
    ],
    [
        ("x²", square),
        ("x³", cube),
        ("xʸ", lambda: add_text("^")),
        ("1/x", reciprocal),
        ("x!", lambda: add_text("!")),
        ("10ˣ", lambda: add_text("10^")),
    ],
    [
        ("π", lambda: add_text("π")),
        ("e", lambda: add_text("e")),
        ("(", lambda: add_text("(")),
        (")", lambda: add_text(")")),
        ("%", lambda: add_text("%")),
        ("±", toggle_sign),
    ],
]

for row_index, row in enumerate(rows):
    cols = st.columns(6)
    for col, (label, func) in zip(cols, row):
        with col:
            st.button(
                label,
                key=f"scientific_{row_index}_{label}",
                on_click=func,
                use_container_width=True,
            )

# Main calculator keypad
keypad = [
    [("AC", clear_all, "danger"), ("⌫", backspace, "operator"), ("DEG/RAD", toggle_angle, "operator"), ("÷", lambda: add_text("÷"), "operator")],
    [("7", lambda: add_text("7"), ""), ("8", lambda: add_text("8"), ""), ("9", lambda: add_text("9"), ""), ("×", lambda: add_text("×"), "operator")],
    [("4", lambda: add_text("4"), ""), ("5", lambda: add_text("5"), ""), ("6", lambda: add_text("6"), ""), ("−", lambda: add_text("−"), "operator")],
    [("1", lambda: add_text("1"), ""), ("2", lambda: add_text("2"), ""), ("3", lambda: add_text("3"), ""), ("+", lambda: add_text("+"), "operator")],
    [("0", lambda: add_text("0"), ""), (".", lambda: add_text("."), ""), ("=", do_equals, "accent"), ("ENTER", do_equals, "accent")],
]

for row_index, row in enumerate(keypad):
    cols = st.columns(4)
    for col, (label, func, cls) in zip(cols, row):
        with col:
            if cls:
                st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            st.button(
                label,
                key=f"key_{row_index}_{label}",
                on_click=func,
                use_container_width=True,
            )
            if cls:
                st.markdown("</div>", unsafe_allow_html=True)

# Close calculator shell
st.markdown("</div>", unsafe_allow_html=True)

# History
if st.session_state.history:
    st.markdown('<div class="history-title">Calculation History</div>', unsafe_allow_html=True)
    for item in st.session_state.history:
        st.markdown(
            f'<div class="history-item">{item["expression"]} = <b>{item["result"]}</b> '
            f'<span style="opacity:.55">· {item["time"]}</span></div>',
            unsafe_allow_html=True,
        )

    if st.button("Clear History", key="clear_history"):
        clear_history()
        st.rerun()

st.markdown(
    '<div class="help">Tip: use ^ for powers, % for percentage, and DEG/RAD to change angle mode.</div>',
    unsafe_allow_html=True,
)
