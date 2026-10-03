import ast
import html
import math
import re
from decimal import Decimal
import streamlit as st

st.set_page_config(page_title="Pro Scientific Calculator", page_icon="🧮", layout="centered")

# ════════════════════════════════════════════════════════════════════
#  1. SAFE MATH ENGINE
# ════════════════════════════════════════════════════════════════════
OPS = ("+", "−", "×", "÷", "^")

def make_functions(angle: str) -> dict:
    deg = angle == "DEG"
    to_rad = math.radians if deg else (lambda x: x)
    from_rad = math.degrees if deg else (lambda x: x)

    def tan(x):
        r = to_rad(x)
        if abs(math.cos(r)) < 1e-12:
            raise ValueError("tan undefined")
        return math.tan(r)

    def fact(x):
        if x < 0 or x != int(x) or x > 170:
            raise ValueError("factorial domain")
        return float(math.factorial(int(x)))

    return {
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": tan,
        "asin": lambda x: from_rad(math.asin(x)),
        "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "log": math.log10,
        "ln": math.log,
        "sqrt": math.sqrt,
        "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
        "exp": math.exp,
        "abs": abs,
        "fact": fact,
    }

CONSTANTS = {"pi": math.pi, "e": math.e}
BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
}

def prepare(expr: str, ans: float) -> str:
    s = (
        expr.replace("×", "*").replace("÷", "/").replace("−", "-")
        .replace("π", "pi").replace("√", "sqrt").replace("^", "**")
    )
    s = s.replace("Ans", "(" + format(Decimal(repr(float(ans))), "f") + ")")
    s = re.sub(r"(\d+(?:\.\d+)?)!", r"fact(\1)", s)
    s = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", s)
    s = re.sub(r"\b(pi|e)(?=[\d(])", r"\1*", s)
    s = re.sub(r"(?<=[\d)])(?=[A-Za-z(])", "*", s)
    s = re.sub(r"(?<=\))(?=\d)", "*", s)
    return s

def _eval(node, funcs):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in BIN:
        a, b = _eval(node.left, funcs), _eval(node.right, funcs)
        if isinstance(node.op, ast.Pow) and abs(b) > 10000:
            raise OverflowError
        res = BIN[type(node.op)](a, b)
        if isinstance(res, complex):
            raise ValueError("complex result")
        return res
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand, funcs)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in funcs and len(node.args) == 1 and not node.keywords:
        return float(funcs[node.func.id](_eval(node.args[0], funcs)))
    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]
    raise SyntaxError("unsupported")

def evaluate(expr: str, angle: str, ans: float) -> float:
    tree = ast.parse(prepare(expr, ans), mode="eval")
    val = _eval(tree.body, make_functions(angle))
    if math.isnan(val) or math.isinf(val):
        raise OverflowError
    return 0.0 if abs(val) < 1e-12 else val

def fmt(val: float) -> str:
    val = float(f"{val:.12g}")
    if val == 0:
        return "0"
    if abs(val) >= 1e15 or abs(val) < 1e-9:
        mant, exp = f"{val:.10g}".split("e") if "e" in f"{val:.10g}" else (f"{val:.10e}".split("e"))
        mant = mant.rstrip("0").rstrip(".") if "." in mant else mant
        return f"{mant}×10^{int(exp)}"
    text = format(Decimal(f"{val:.12g}"), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text

def close_brackets(expr: str) -> str:
    return expr + ")" * max(0, expr.count("(") - expr.count(")"))

# ════════════════════════════════════════════════════════════════════
#  2. STATE + ACTIONS
# ════════════════════════════════════════════════════════════════════
DEFAULTS = dict(expr="", top="", fresh=False, error="", ans=0.0, mem=0.0,
                angle="DEG", inv=False, history=[])
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

FUNCS = {
    "SIN": ("sin(", "asin("), "COS": ("cos(", "acos("), "TAN": ("tan(", "atan("),
    "LN": ("ln(", "exp("), "LOG": ("log(", "10^("), "SQRT": ("√(", "^2"),
}
TOKEN_END = re.compile(r"(?:asin\(|acos\(|atan\(|sin\(|cos\(|tan\(|ln\(|log\(|exp\(|√\(|Ans)$")

def insert(t: str):
    s = st.session_state
    binary, postfix = t in OPS, t in ("!", "%", "^2")
    if s.fresh:
        if not (binary or postfix):
            s.expr = ""
        s.fresh = False
    e = s.expr
    if binary:
        if not e and t != "−":
            e = "Ans"
        if e and e[-1] in OPS:
            if t == "−" and e[-1] in "×÷^":
                pass
            else:
                e = e[:-1]
        if e.endswith("(") and t != "−":
            return
    elif postfix and (not e or e[-1] in OPS or e.endswith("(")):
        return
    s.expr = e + t

def press_digit(d: str):
    s = st.session_state
    if s.fresh:
        s.expr, s.fresh = "", False
    if re.search(r"(?<![\d.])0$", s.expr):
        s.expr = s.expr[:-1]
    s.expr += d

def press_dot():
    s = st.session_state
    if s.fresh:
        s.expr, s.fresh = "", False
    seg = re.search(r"[\d.]*$", s.expr).group(0)
    if "." in seg:
        return
    s.expr += "." if seg else "0."

def press_bracket(b: str):
    s = st.session_state
    if b == ")":
        if s.expr.count("(") <= s.expr.count(")") or s.expr.endswith("("):
            return
        s.fresh = False
        s.expr += ")"
    else:
        insert("(")

def is_wrapped(e: str) -> bool:
    if not (e.startswith("−(") and e.endswith(")")):
        return False
    depth = 0
    for i, ch in enumerate(e[1:], 1):
        depth += (ch == "(") - (ch == ")")
        if depth == 0:
            return i == len(e) - 1
    return False

def press_sign():
    s = st.session_state
    s.fresh = False
    e = close_brackets(s.expr)
    if not e or e == "−":
        s.expr = "" if e == "−" else "−"
    elif is_wrapped(e):
        s.expr = e[2:-1]
    else:
        s.expr = f"−({e})"

def run(expr: str):
    s = st.session_state
    try:
        return evaluate(close_brackets(expr), s.angle, s.ans)
    except ZeroDivisionError:
        s.error = "Cannot divide by zero"
    except OverflowError:
        s.error = "Overflow"
    except ValueError:
        s.error = "Math error"
    except (SyntaxError, TypeError):
        s.error = "Syntax error"
    except Exception:
        s.error = "Error"
    return None

def press_equal():
    s = st.session_state
    if not s.expr:
        return
    full = close_brackets(s.expr)
    val = run(full)
    if val is None:
        return
    text = fmt(val)
    s.history.insert(0, (full, text))
    del s.history[30:]
    s.ans, s.top, s.expr, s.fresh = val, f"{full} =", text, True

def press_memory(a: str):
    s = st.session_state
    if a == "MC":
        s.mem = 0.0
    elif a == "MR":
        if s.mem != 0:
            txt = fmt(s.mem)
            insert(f"({txt})" if s.mem < 0 else txt)
    else:
        val = run(s.expr) if s.expr else s.ans
        if val is not None:
            s.mem += val if a == "M+" else -val

def press_delete():
    s = st.session_state
    if s.fresh:
        s.expr, s.fresh, s.top = "", False, ""
        return
    new = TOKEN_END.sub("", s.expr)
    s.expr = new if new != s.expr else s.expr[:-1]

def press(a: str):
    s = st.session_state
    s.error = ""
    if a == "AC":
        s.expr, s.top, s.fresh = "", "", False
    elif a == "DEL":
        press_delete()
    elif a == "=":
        press_equal()
    elif a == "ANGLE":
        s.angle = "RAD" if s.angle == "DEG" else "DEG"
    elif a == "INV":
        s.inv = not s.inv
    elif a in ("MC", "MR", "M+", "M−"):
        press_memory(a)
    elif a == "SIGN":
        press_sign()
    elif a in FUNCS:
        insert(FUNCS[a][s.inv])
        s.inv = False
    elif a == "PI":
        insert("π")
    elif a == "E":
        insert("e")
    elif a == "POW":
        insert("^")
    elif a == "FACT":
        insert("!")
    elif a == "RECIP":
        insert("1/(")
    elif a == "ANS":
        insert("Ans")
    elif a == "%":
        insert("%")
    elif a == ".":
        press_dot()
    elif a.isdigit():
        press_digit(a)
    elif a in "()":
        press_bracket(a)
    else:
        insert(a)

# ════════════════════════════════════════════════════════════════════
#  3. ULTRA-MODERN SMOOTH & GLOWING UI STYLING
# ════════════════════════════════════════════════════════════════════
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

.stApp { 
    background: radial-gradient(circle at 50% 10%, #1e2530 0%, #0d1117 100%);
    font-family: 'Outfit', sans-serif;
}
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }

/* Main Container Card */
.block-container {
    max-width: 440px; 
    margin: 1.5rem auto; 
    padding: 1.5rem 1.2rem 1.8rem !important;
    background: rgba(26, 31, 38, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 32px; 
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.7), 0 0 40px rgba(79, 70, 229, 0.15);
}

/* Responsive Grid Adjustments */
div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 8px !important; }
div[data-testid="stColumn"], div[data-testid="column"] {
    min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}
div[data-testid="stVerticalBlock"] { gap: 8px; }

/* Premium Futuristic LCD */
.lcd {
    background: linear-gradient(145deg, #0f172a, #090d16);
    border-radius: 18px; 
    padding: 1rem 1.2rem; 
    margin-bottom: 1.2rem;
    border: 2px solid rgba(0, 255, 204, 0.25);
    box-shadow: inset 0 4px 15px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 255, 204, 0.08);
    font-family: 'JetBrains Mono', monospace;
}
.lcd-flags { 
    display: flex; 
    gap: 0.5rem; 
    margin-bottom: 0.3rem;
}
.lcd-flags span { 
    background: rgba(0, 255, 204, 0.12); 
    color: #00ffcc; 
    padding: 2px 8px; 
    border-radius: 6px; 
    font-size: 0.75rem; 
    font-weight: 700;
    border: 1px solid rgba(0, 255, 204, 0.3);
}
.lcd-in { 
    text-align: right; 
    min-height: 1.8rem; 
    color: #94a3b8; 
    overflow-wrap: anywhere; 
    font-size: 1.1rem;
}
.lcd-res { 
    text-align: right; 
    color: #f8fafc; 
    overflow-wrap: anywhere; 
    font-weight: 700; 
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
}
.lcd-res.live { color: #00ffcc; opacity: 0.7; }
.lcd-res.err { color: #f43f5e; text-shadow: 0 0 10px rgba(244, 63, 94, 0.4); }

/* Buttons Glow & Smooth Interactive Design */
div[class*="st-key-"] button {
    width: 100%; 
    height: 3.1rem; 
    padding: 0; 
    border-radius: 14px !important;
    background: var(--bg) !important; 
    color: var(--fg) !important;
    font-family: 'Outfit', sans-serif; 
    font-size: 1.1rem; 
    font-weight: 600;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
div[class*="st-key-"] button p { color: var(--fg) !important; font-size: inherit; font-weight: inherit; }
div[class*="st-key-"] button:hover { 
    filter: brightness(1.2); 
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4), 0 0 12px rgba(255, 255, 255, 0.1);
}
div[class*="st-key-"] button:active { 
    transform: translateY(2px) scale(0.97); 
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
}

/* Soft Color Palette for Buttons */
div[class*="st-key-num_"] { --bg: #27303f; --fg: #f1f5f9; }
div[class*="st-key-fn_"]  { --bg: #334155; --fg: #38bdf8; }
div[class*="st-key-op_"]  { --bg: #1e293b; --fg: #f43f5e; }
div[class*="st-key-mem_"] { --bg: #334155; --fg: #cbd5e1; }
div[class*="st-key-mem_"] button { font-size: 0.9rem; }
div[class*="st-key-tog_"] { --bg: #334155; --fg: #fbbf24; }
div[class*="st-key-act_"] { --bg: #e11d48; --fg: #ffffff; }
div[class*="st-key-eq_"]  { 
    --bg: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; 
    --fg: #ffffff; 
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.5);
}
"""

def lcd_html() -> str:
    s = st.session_state
    if s.fresh:
        inp = s.top[:-2] if s.top.endswith(" =") else s.top
        inp, res, res_cls = inp + " =", s.expr, ""
    else:
        inp, res, res_cls = s.expr, "", " live"
        if s.expr and not re.fullmatch(r"[\d.]+", s.expr):
            try:
                v = evaluate(close_brackets(s.expr), s.angle, s.ans)
                if fmt(v) != s.expr:
                    res = fmt(v)
            except Exception:
                pass
        if not s.expr:
            res, res_cls = "0", ""

    if s.error:
        res, res_cls = s.error, " err"

    n_in = len(inp)
    in_size = 1.3 if n_in <= 16 else 1.0 if n_in <= 26 else 0.85
    n_res = len(res)
    res_size = 2.4 if n_res <= 9 else 1.9 if n_res <= 14 else 1.4 if n_res <= 24 else 1.0
    if s.error:
        res_size = 1.2

    flags = [s.angle]
    if s.inv:
        flags.append("2nd")
    if s.mem != 0:
        flags.append("M")
    flag_html = "".join(f"<span>{f}</span>" for f in flags)
    return (
        f'<div class="lcd"><div class="lcd-flags">{flag_html}</div>'
        f'<div class="lcd-in" style="font-size:{in_size}rem">{html.escape(inp) or "&nbsp;"}</div>'
        f'<div class="lcd-res{res_cls}" style="font-size:{res_size}rem">{html.escape(res) or "&nbsp;"}</div></div>'
    )

GRID = [
    [("tog", "ANGLE"), ("mem", "MC"), ("mem", "MR"), ("mem", "M+"), ("mem", "M−")],
    [("tog", "INV"), ("fn", "SIN"), ("fn", "COS"), ("fn", "TAN"), ("fn", "PI")],
    [("fn", "LN"), ("fn", "LOG"), ("fn", "SQRT"), ("fn", "POW"), ("fn", "FACT")],
    [("fn", "("), ("fn", ")"), ("fn", "RECIP"), ("fn", "%"), ("fn", "E")],
    [("num", "7"), ("num", "8"), ("num", "9"), ("op", "÷"), ("act", "DEL")],
    [("num", "4"), ("num", "5"), ("num", "6"), ("op", "×"), ("act", "AC")],
    [("num", "1"), ("num", "2"), ("num", "3"), ("op", "−"), ("fn", "ANS")],
    [("num", "0"), ("num", "."), ("num", "SIGN"), ("op", "+"), ("eq", "=")],
]
INV_KEY = "tog_10"

STATIC_LABELS = {
    "PI": "π", "E": "e", "POW": "xʸ", "FACT": "n!", "RECIP": "1/x", "DEL": "⌫",
    "ANS": "Ans", "SIGN": "±", "INV": "2nd",
}
DYN_LABELS = {
    "SIN": ("sin", "sin⁻¹"), "COS": ("cos", "cos⁻¹"), "TAN": ("tan", "tan⁻¹"),
    "LN": ("ln", "eˣ"), "LOG": ("log", "10ˣ"), "SQRT": ("√", "x²"),
}

def label(action: str) -> str:
    if action == "ANGLE":
        return st.session_state.angle
    if action in DYN_LABELS:
        return DYN_LABELS[action][st.session_state.inv]
    return STATIC_LABELS.get(action, action)

# ════════════════════════════════════════════════════════════════════
#  4. RENDER UI
# ════════════════════════════════════════════════════════════════════
st.markdown(STYLE, unsafe_allow_html=True)
if st.session_state.inv:
    st.markdown(
        f"<style>div.st-key-{INV_KEY} button{{background:#fbbf24 !important;"
        f"color:#0f172a !important;}} div.st-key-{INV_KEY} button p{{color:#0f172a !important;}}</style>",
        unsafe_allow_html=True,
    )

st.markdown(lcd_html(), unsafe_allow_html=True)

for r, row in enumerate(GRID):
    cols = st.columns(5)
    for c, (kind, action) in enumerate(row):
        cols[c].button(label(action), key=f"{kind}_{r}{c}", on_click=press,
                       args=(action,), use_container_width=True)

with st.expander("🕘 Calculation History"):
    if st.session_state.history:
        for ex, res in st.session_state.history[:15]:
            st.markdown(f"`{ex}` = **{res}**")
        st.button("Clear history", key="act_clear_hist",
                  on_click=lambda: st.session_state.history.clear())
    else:
        st.caption("No history yet.")
