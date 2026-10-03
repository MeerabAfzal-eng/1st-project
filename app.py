"""
Scientific Calculator  -  Streamlit
-----------------------------------
Run:   streamlit run scientific_calculator.py
Needs: streamlit >= 1.39   (pip install -U streamlit)

Features
  * Casio-style LCD display + fixed 5-column keypad (mobile par bhi grid nahi tootta)
  * sin cos tan, inverse (2nd), ln, log, e^x, 10^x, sqrt, x^2, x^y, n!, 1/x, %, pi, e
  * DEG / RAD mode, Ans, Memory (MC MR M+ M-), +/- , backspace, AC
  * Live preview, auto-close brackets, history
  * eval() use nahi hota - safe AST evaluator
"""

import ast
import html
import math
import re
from decimal import Decimal

import streamlit as st

st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

# ════════════════════════════════════════════════════════════════════
#  1.  SAFE MATH ENGINE
# ════════════════════════════════════════════════════════════════════
OPS = ("+", "−", "×", "÷", "^")


def make_functions(angle: str) -> dict:
    """Trig functions DEG/RAD ke hisab se."""
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
    """Display expression  ->  Python-style expression."""
    s = (
        expr.replace("×", "*").replace("÷", "/").replace("−", "-")
        .replace("π", "pi").replace("√", "sqrt").replace("^", "**")
    )
    s = s.replace("Ans", "(" + format(Decimal(repr(float(ans))), "f") + ")")
    s = re.sub(r"(\d+(?:\.\d+)?)!", r"fact(\1)", s)           # 5!   -> fact(5)
    s = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", s)           # 50%  -> (50/100)
    s = re.sub(r"\b(pi|e)(?=[\d(])", r"\1*", s)                # pi(  -> pi*(
    s = re.sub(r"(?<=[\d)])(?=[A-Za-z(])", "*", s)             # 2sin( / 2( / )(
    s = re.sub(r"(?<=\))(?=\d)", "*", s)                       # )5   -> )*5
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
    """Number -> clean text (12 significant digits)."""
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
#  2.  STATE + BUTTON LOGIC
# ════════════════════════════════════════════════════════════════════
DEFAULTS = dict(expr="", top="", fresh=False, error="", ans=0.0, mem=0.0,
                angle="DEG", inv=False, history=[])
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

# action -> (normal, 2nd)
FUNCS = {
    "SIN": ("sin(", "asin("), "COS": ("cos(", "acos("), "TAN": ("tan(", "atan("),
    "LN": ("ln(", "exp("), "LOG": ("log(", "10^("), "SQRT": ("√(", "^2"),
}
TOKEN_END = re.compile(r"(?:asin\(|acos\(|atan\(|sin\(|cos\(|tan\(|ln\(|log\(|exp\(|√\(|Ans)$")


def insert(t: str):
    s = st.session_state
    binary, postfix = t in OPS, t in ("!", "%", "^2")
    if s.fresh:                                   # result ke baad naya number => naya start
        if not (binary or postfix):
            s.expr = ""
        s.fresh = False
    e = s.expr
    if binary:
        if not e and t != "−":
            e = "Ans"
        if e and e[-1] in OPS:
            if t == "−" and e[-1] in "×÷^":
                pass                              # 5×−3 allowed
            else:
                e = e[:-1]                        # operator replace
        if e.endswith("(") and t != "−":
            return
    elif postfix and (not e or e[-1] in OPS or e.endswith("(")):
        return
    s.expr = e + t


def press_digit(d: str):
    s = st.session_state
    if s.fresh:
        s.expr, s.fresh = "", False
    if re.search(r"(?<![\d.])0$", s.expr):        # 007 -> 7
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
    """evaluate + friendly error. Returns float or None (error set)."""
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
    else:                                         # + − × ÷
        insert(a)


# ════════════════════════════════════════════════════════════════════
#  3.  LOOK  (Casio-style body, LCD, keys)
# ════════════════════════════════════════════════════════════════════
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Semi+Condensed:wght@500;700&display=swap');

.stApp { background:#14171a; }
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }

/* calculator body = page ka main container */
.block-container {
  max-width:430px; margin:1.2rem auto; padding:1.1rem 1rem 1.3rem !important;
  background:linear-gradient(170deg,#32373d,#25292e);
  border-radius:26px; border:1px solid #444b53;
  box-shadow:0 30px 60px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.08);
}

/* grid ko mobile par bhi wrap na hone do */
div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.4rem !important; }
div[data-testid="stColumn"], div[data-testid="column"] {
  min-width:0 !important; flex:1 1 0 !important; width:auto !important;
}
div[data-testid="stVerticalBlock"] { gap:.4rem; }

/* LCD */
.lcd {
  background:linear-gradient(180deg,#a9b698,#bac6a8);
  border-radius:10px; padding:.45rem .9rem .7rem; margin-bottom:.7rem;
  border:3px solid #1b1e22; box-shadow:inset 0 3px 8px rgba(0,0,0,.35);
  min-height:132px; color:#1d2619; font-family:'Share Tech Mono',monospace;
}
.lcd-flags { display:flex; gap:.5rem; height:1.15rem; font-size:.72rem; font-weight:700; letter-spacing:.04em; }
.lcd-flags span { background:#1d2619; color:#bac6a8; padding:0 .4rem; border-radius:3px; line-height:1.15rem; }
.lcd-top { text-align:right; min-height:1.6rem; font-size:1.05rem; opacity:.7; overflow-wrap:anywhere; }
.lcd-top.err { opacity:1; font-weight:700; }
.lcd-main { text-align:right; font-weight:400; line-height:1.1; overflow-wrap:anywhere; }

/* keys */
div[class*="st-key-"] button {
  width:100%; height:2.85rem; padding:0; border:0 !important; border-radius:9px;
  background:var(--bg) !important; color:var(--fg) !important;
  font-family:'Barlow Semi Condensed',sans-serif; font-size:1.12rem; font-weight:700;
  box-shadow:0 3px 0 var(--edge), 0 6px 8px rgba(0,0,0,.35);
  transition:transform .06s, box-shadow .06s, filter .15s;
}
div[class*="st-key-"] button p { color:var(--fg) !important; font-size:inherit; font-weight:inherit; }
div[class*="st-key-"] button:hover { filter:brightness(1.12); }
div[class*="st-key-"] button:active { transform:translateY(3px); box-shadow:0 0 0 var(--edge); }
div[class*="st-key-"] button:focus:not(:active) { outline:2px solid #f2c94c; outline-offset:2px; }

div[class*="st-key-num_"] { --bg:#e6e3da; --fg:#1b1d20; --edge:#a9a69d; }
div[class*="st-key-fn_"]  { --bg:#4a5159; --fg:#f2f2f2; --edge:#2b3035; }
div[class*="st-key-op_"]  { --bg:#2f353b; --fg:#ffffff; --edge:#16191c; }
div[class*="st-key-mem_"] { --bg:#3a4047; --fg:#c9ced4; --edge:#1d2125; }
div[class*="st-key-mem_"] button { font-size:.95rem; }
div[class*="st-key-tog_"] { --bg:#3a4047; --fg:#f2c94c; --edge:#1d2125; }
div[class*="st-key-act_"] { --bg:#e4572e; --fg:#ffffff; --edge:#9c3417; }
div[class*="st-key-eq_"]  { --bg:#2a6fdb; --fg:#ffffff; --edge:#18448c; }
"""


def lcd_html() -> str:
    s = st.session_state
    expr = s.expr or "0"
    n = len(expr)
    size = 2.7 if n <= 9 else 2.1 if n <= 14 else 1.6 if n <= 24 else 1.2

    top, cls = s.top if s.fresh else "", ""
    if s.error:
        top, cls = s.error, " err"
    elif not s.fresh and s.expr and not re.fullmatch(r"[\d.]+", s.expr):
        val = None
        try:
            val = evaluate(close_brackets(s.expr), s.angle, s.ans)
        except Exception:
            pass
        if val is not None and fmt(val) != s.expr:
            top = "= " + fmt(val)

    flags = [s.angle]
    if s.inv:
        flags.append("2nd")
    if s.mem != 0:
        flags.append("M")
    flag_html = "".join(f"<span>{f}</span>" for f in flags)
    return (
        f'<div class="lcd"><div class="lcd-flags">{flag_html}</div>'
        f'<div class="lcd-top{cls}">{html.escape(top)}</div>'
        f'<div class="lcd-main" style="font-size:{size}rem">{html.escape(expr)}</div></div>'
    )


# (kind, action) rows — kind sirf colour decide karta hai
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
INV_KEY = "tog_10"   # row 1, col 0

STATIC_LABELS = {
    "PI": "π", "E": "e", "POW": "xʸ", "FACT": "n!", "RECIP": "1/x", "DEL": "⌫",
    "ANS": "Ans", "SIGN": "±", "INV": "2nd",
}
DYN_LABELS = {  # (normal, 2nd)
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
#  4.  RENDER
# ════════════════════════════════════════════════════════════════════
st.markdown(STYLE, unsafe_allow_html=True)
if st.session_state.inv:
    st.markdown(
        f"<style>div.st-key-{INV_KEY} button{{background:#f2c94c !important;"
        f"color:#1b1d20 !important;}} div.st-key-{INV_KEY} button p{{color:#1b1d20 !important;}}</style>",
        unsafe_allow_html=True,
    )

st.markdown(lcd_html(), unsafe_allow_html=True)

for r, row in enumerate(GRID):
    cols = st.columns(5)
    for c, (kind, action) in enumerate(row):
        cols[c].button(label(action), key=f"{kind}_{r}{c}", on_click=press,
                       args=(action,), use_container_width=True)

with st.expander("🕘 History"):
    if st.session_state.history:
        for ex, res in st.session_state.history[:15]:
            st.markdown(f"`{ex}` = **{res}**")
        st.button("Clear history", key="act_clear_hist",
                  on_click=lambda: st.session_state.history.clear())
    else:
        st.caption("Abhi koi calculation nahi hui.")
