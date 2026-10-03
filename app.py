"""
Scientific Calculator  -  Professional Blue Edition (Streamlit)
-------------------------------------------------------
Run:   streamlit run pro_calculator.py
Needs: streamlit >= 1.39   (pip install -U streamlit)
"""

import ast
import html
import math
import random
import re
from decimal import Decimal

import streamlit as st

st.set_page_config(page_title="Scientific Calculator", page_icon="🧮", layout="centered")

# ════════════════════════════════════════════════════════════════════
#  1.  SAFE MATH ENGINE
# ════════════════════════════════════════════════════════════════════
BIN_TOKENS = ("+", "−", "×", "÷", "^", "mod")         # binary operators (display form)
POSTFIX = ("!", "%", "^2", "^3", "°", "×10^(", "^(1/(")  # need an operand before them


def _int(x: float) -> int:
    if x < 0 or x != int(x):
        raise ValueError("needs non-negative integer")
    return int(x)


def make_functions(angle: str) -> dict:
    k = {"DEG": math.pi / 180, "RAD": 1.0, "GRAD": math.pi / 200}[angle]
    to_rad = lambda x: x * k
    from_rad = lambda x: x / k

    def tan(x):
        r = to_rad(x)
        if abs(math.cos(r)) < 1e-12:
            raise ValueError("tan undefined")
        return math.tan(r)

    def fact(x):
        n = _int(x)
        if n > 170:
            raise OverflowError
        return float(math.factorial(n))

    def comb(n, r):
        n, r = _int(n), _int(r)
        if r > n:
            raise ValueError("r > n")
        if n > 5000:
            raise OverflowError
        return float(math.comb(n, r))

    def perm(n, r):
        n, r = _int(n), _int(r)
        if r > n:
            raise ValueError("r > n")
        if n > 5000:
            raise OverflowError
        return float(math.perm(n, r))

    return {
        "sin": lambda x: math.sin(to_rad(x)),
        "cos": lambda x: math.cos(to_rad(x)),
        "tan": tan,
        "asin": lambda x: from_rad(math.asin(x)),
        "acos": lambda x: from_rad(math.acos(x)),
        "atan": lambda x: from_rad(math.atan(x)),
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "asinh": math.asinh, "acosh": math.acosh, "atanh": math.atanh,
        "log": math.log10, "ln": math.log,
        "sqrt": math.sqrt,
        "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
        "exp": math.exp, "abs": abs,
        "floor": math.floor, "ceil": math.ceil,
        "fact": fact, "comb": comb, "perm": perm,
    }


CONSTANTS = {"pi": math.pi, "e": math.e}
BIN = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}


def prepare(expr: str, ans: float, angle: str) -> str:
    """Display expression -> Python expression."""
    s = expr.replace("mod", "§")
    s = (s.replace("×", "*").replace("÷", "/").replace("−", "-")
          .replace("π", "pi").replace("√", "sqrt").replace("^", "**"))
    s = s.replace("°", {"DEG": "", "RAD": "*(pi/180)", "GRAD": "*(10/9)"}[angle])
    s = s.replace("Ans", "(" + format(Decimal(repr(float(ans))), "f") + ")")
    s = re.sub(r"(\d+)P(\d+)", r"perm(\1,\2)", s)                # 5P2
    s = re.sub(r"(\d+)C(\d+)", r"comb(\1,\2)", s)                # 5C2
    s = re.sub(r"(\d+(?:\.\d+)?)!", r"fact(\1)", s)              # 5!
    s = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", s)              # 50%
    s = re.sub(r"\b(pi|e)(?=[\d(])", r"\1*", s)                  # pi( -> pi*(
    s = re.sub(r"(?<=[\d)])(?=[A-Za-z(])", "*", s)               # 2sin( / 3( / )(
    s = re.sub(r"(?<=\))(?=\d)", "*", s)                         # )5
    return s.replace("§", "%")


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
            and node.func.id in funcs and 1 <= len(node.args) <= 2 and not node.keywords:
        return float(funcs[node.func.id](*[_eval(a, funcs) for a in node.args]))
    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]
    raise SyntaxError("unsupported")


def evaluate(expr: str, angle: str, ans: float) -> float:
    tree = ast.parse(prepare(expr, ans, angle), mode="eval")
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
        mant, exp = f"{val:.10e}".split("e")
        return f"{mant.rstrip('0').rstrip('.')}×10^{int(exp)}"
    text = format(Decimal(f"{val:.12g}"), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def close_brackets(expr: str) -> str:
    return expr + ")" * max(0, expr.count("(") - expr.count(")"))


def last_op(e: str):
    return next((o for o in BIN_TOKENS if e.endswith(o)), None)


# ════════════════════════════════════════════════════════════════════
#  2.  STATE + BUTTON LOGIC
# ════════════════════════════════════════════════════════════════════
DEFAULTS = dict(expr="", top="", fresh=False, error="", ans=0.0, mem=0.0,
                angle="DEG", inv=False, hyp=False, history=[])
for _k, _v in DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

TRIG = {"SIN": "sin", "COS": "cos", "TAN": "tan"}
ALT = {  # action -> (normal, shift)
    "LN": ("ln(", "exp("), "LOG": ("log(", "10^("), "SQRT": ("√(", "^2"),
    "POW": ("^", "^(1/("), "CUBE": ("^3", "cbrt("),
    "RECIP": ("1/(", "ceil("), "ABS": ("abs(", "floor("),
}
_NAMES = ["asinh", "acosh", "atanh", "asin", "acos", "atan", "sinh", "cosh", "tanh",
          "sin", "cos", "tan", "cbrt", "ceil", "floor", "exp", "abs", "log", "ln"]
TOKEN_END = re.compile("(?:(?:" + "|".join(_NAMES) + r")\(|√\(|Ans|mod|×10\^\(|\^\(1/\()$")


def insert(t: str):
    s = st.session_state
    binary, postfix = t in BIN_TOKENS, t in POSTFIX
    if s.fresh:                                     # '=' ke baad naya number => naya start
        if not (binary or postfix):
            s.expr = ""
        s.fresh = False
    e = s.expr
    if binary:
        if not e and t != "−":
            e = "Ans"
        prev = last_op(e)
        if prev:
            if t == "−" and prev in ("×", "÷", "^"):
                pass                                # 5×−3 allowed
            else:
                e = e[: -len(prev)]                 # operator replace
        if e.endswith("(") and t != "−":
            return
    elif postfix and (not e or last_op(e) or e.endswith("(")):
        return
    s.expr = e + t


def insert_number(txt: str):
    """Number (Ran#, MR) daalna - pehle se digit ho to × laga do."""
    s = st.session_state
    if s.fresh:
        s.expr, s.fresh = "", False
    if s.expr and (s.expr[-1] in "0123456789.)π" or s.expr.endswith(("Ans", "e"))):
        txt = "×" + txt
    s.expr += txt


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
    """Evaluate + friendly error. Returns float, ya None (error set)."""
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
            insert_number(f"({txt})" if s.mem < 0 else txt)
    else:
        val = run(s.expr) if s.expr else s.ans
        if val is not None:
            s.mem = val if a == "MS" else s.mem + (val if a == "M+" else -val)


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
        s.angle = {"DEG": "RAD", "RAD": "GRAD", "GRAD": "DEG"}[s.angle]
    elif a == "INV":
        s.inv = not s.inv
    elif a == "HYP":
        s.hyp = not s.hyp
    elif a in ("MC", "MR", "M+", "M−", "MS"):
        press_memory(a)
    elif a == "SIGN":
        press_sign()
    elif a in TRIG:
        name = ("a" if s.inv else "") + TRIG[a] + ("h" if s.hyp else "")
        insert(name + "(")
        s.inv = s.hyp = False
    elif a in ALT:
        insert(ALT[a][s.inv])
        s.inv = False
    elif a == "PI":
        insert("π")
    elif a == "E":
        insert("e")
    elif a == "FACT":
        insert("!")
    elif a == "EXP":
        insert("×10^(")
    elif a == "DEG":
        insert("°")
    elif a == "MOD":
        insert("mod")
    elif a == "ANS":
        insert("Ans")
    elif a == "RAN":
        insert_number(f"{random.random():.3f}")
    elif a in ("NPR", "NCR"):
        if re.search(r"\d$", s.expr):
            s.fresh = False
            s.expr += "P" if a == "NPR" else "C"
    elif a == ".":
        press_dot()
    elif a.isdigit():
        press_digit(a)
    elif a in ("(", ")"):
        press_bracket(a)
    else:                                           # + − × ÷ %
        insert(a)


# ════════════════════════════════════════════════════════════════════
#  3.  PROFESSIONAL BLUE LOOK
# ════════════════════════════════════════════════════════════════════
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html { scroll-behavior:smooth; }
.stApp {
  font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
  background:
    radial-gradient(900px 520px at 50% -10%, #d9e4fa 0%, transparent 62%),
    linear-gradient(180deg, #f1f5fb 0%, #e4ebf6 100%);
}
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none; }
#MainMenu, footer, [data-testid="stStatusWidget"] { visibility:hidden; }
[data-stale="true"] { opacity:1 !important; transition:none !important; }

/* body */
.block-container {
  max-width:440px; margin:2rem auto 2rem !important; padding:1rem 1.1rem 1.25rem !important;
  background:linear-gradient(180deg, #fafbfe 0%, #e8eef9 100%);
  border:1px solid #c7d4ec; border-radius:28px;
  box-shadow:0 30px 60px rgba(31,58,138,.20), 0 2px 6px rgba(31,58,138,.10),
             inset 0 1px 0 #ffffff, inset 0 -4px 0 rgba(31,58,138,.06);
}

/* upar ki patti: model label + solar panel */
.topbar { display:flex; align-items:center; justify-content:space-between; margin:.05rem .25rem .7rem; }
.topbar .model { font-size:.62rem; font-weight:600; letter-spacing:.26em; color:#7387b8; }
.topbar .solar {
  width:9.6rem; height:1.2rem; border-radius:6px;
  background:
    repeating-linear-gradient(90deg, rgba(255,255,255,.18) 0 1px, transparent 1px 1.6rem),
    linear-gradient(180deg, #3a4f93 0%, #1c2c62 100%);
  border:1px solid #16224d;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.25), 0 1px 0 #fff;
}

/* grid: mobile par bhi wrap na ho */
div[data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.42rem !important; }
div[data-testid="stColumn"], div[data-testid="column"] { min-width:0 !important; flex:1 1 0 !important; width:auto !important; }
div[data-testid="stVerticalBlock"] { gap:.42rem; }
.sep { height:1px; margin:.28rem .1rem; background:linear-gradient(90deg, transparent, #b9c8e6 20%, #b9c8e6 80%, transparent); }

/* display */
.lcd {
  background:linear-gradient(180deg, #1b2f6b 0%, #25418c 100%);
  border:1px solid #12214f; border-radius:16px;
  padding:.55rem 1rem .8rem; margin-bottom:.85rem; min-height:150px;
  box-shadow:inset 0 3px 12px rgba(0,0,0,.35), 0 0 0 4px #dde6f8, 0 0 0 5px #bccbe8;
}
.lcd-flags { display:flex; gap:.35rem; height:1.2rem; }
.lcd-flags span {
  background:rgba(255,255,255,.14); color:#d3e0ff; padding:0 .5rem; border-radius:5px;
  font-size:.64rem; font-weight:600; letter-spacing:.08em; line-height:1.2rem; text-transform:uppercase;
}
.lcd-in  { text-align:right; min-height:1.9rem; margin-top:.25rem; line-height:1.25; overflow-wrap:anywhere;
           font-family:'JetBrains Mono',ui-monospace,monospace; font-weight:400; color:#a3b9ef; }
.lcd-res { text-align:right; line-height:1.1; margin-top:.35rem; overflow-wrap:anywhere; color:#ffffff;
           font-weight:600; font-variant-numeric:tabular-nums; letter-spacing:-.01em; }
.lcd-res.live { opacity:.6; }
.lcd-res.err  { color:#ffb3bd; }
.lcd-res.pop  { animation:rise .28s ease-out; }
@keyframes rise { from {transform:translateY(8px); opacity:0;} to {transform:translateY(0); opacity:1;} }

/* keys */
div[class*="st-key-"] button {
  width:100%; height:2.6rem; padding:0; border:0 !important; border-radius:12px;
  background:var(--bg) !important; color:var(--fg) !important;
  font-family:'Inter',sans-serif; font-size:.95rem; font-weight:600; letter-spacing:-.01em;
  box-shadow:0 3px 0 var(--edge), 0 6px 10px rgba(31,58,138,.12), inset 0 1px 0 rgba(255,255,255,.55);
  transition:transform .1s ease, box-shadow .1s ease, filter .15s ease, background .15s ease;
}
div[class*="st-key-"] button p { color:var(--fg) !important; font-size:inherit; font-weight:inherit; }
div[class*="st-key-"] button:hover  { filter:brightness(1.04); transform:translateY(-1px); }
div[class*="st-key-"] button:active { transform:translateY(3px); box-shadow:0 0 0 var(--edge); }
div[class*="st-key-"] button:focus:not(:active) { outline:2px solid rgba(47,107,240,.55); outline-offset:2px; }

div[class*="st-key-num_"] { --bg:#ffffff; --fg:#1b2f66; --edge:#c3d0ea; }
div[class*="st-key-fn_"]  { --bg:#e1e9fa; --fg:#24408a; --edge:#b4c4e6; }
div[class*="st-key-ext_"] { --bg:#eef2fa; --fg:#3a4f85; --edge:#c6d1e6; }
div[class*="st-key-op_"]  { --bg:#24408a; --fg:#ffffff; --edge:#142659; }
div[class*="st-key-mem_"] { --bg:#f3f6fc; --fg:#6b7fb0; --edge:#d3dcee; }
div[class*="st-key-tog_"] { --bg:#fff6dc; --fg:#946200; --edge:#e9d08a; }
div[class*="st-key-act_"] { --bg:#e5626d; --fg:#ffffff; --edge:#b23a45; }
div[class*="st-key-eq_"]  { --bg:#2f6bf0; --fg:#ffffff; --edge:#1b46b5; }
div[class*="st-key-mem_"] button, div[class*="st-key-tog_"] button { font-size:.8rem; letter-spacing:.02em; }

/* history */
div[data-testid="stExpander"] { background:#ffffff; border:1px solid #c7d4ec !important; border-radius:14px; margin-top:.45rem; }
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] p,
div[data-testid="stExpander"] span, div[data-testid="stExpander"] svg { color:#3a4f85 !important; fill:#3a4f85; }
div[data-testid="stExpander"] code { background:#eaf0fc; color:#24408a; }
div[data-testid="stExpander"] strong { color:#1b2f66; }
</style>
"""


def lcd_html() -> str:
    """Upar: input.  Neeche: answer / live result."""
    s = st.session_state

    if s.fresh:                                     # '=' dabane ke baad
        inp, res, cls = s.top, s.expr, " pop"
    else:                                           # type karte waqt
        inp, res, cls = s.expr, "", " live"
        if s.expr and not re.fullmatch(r"[\d.]+", s.expr):
            try:
                v = evaluate(close_brackets(s.expr), s.angle, s.ans)
                if fmt(v) != s.expr:
                    res = fmt(v)
            except Exception:
                pass
        if not s.expr:
            res, cls = "0", ""
    if s.error:
        res, cls = s.error, " err"

    n = len(inp)
    in_size = 1.1 if n <= 18 else 0.95 if n <= 28 else 0.82
    m = len(res)
    res_size = 2.4 if m <= 9 else 1.85 if m <= 14 else 1.35 if m <= 24 else 1.05
    if s.error:
        res_size = 1.2

    flags = [s.angle] + (["SHIFT"] if s.inv else []) + (["hyp"] if s.hyp else []) \
        + (["M"] if s.mem != 0 else [])
    flag_html = "".join(f"<span>{f}</span>" for f in flags)
    return (
        f'<div class="lcd"><div class="lcd-flags">{flag_html}</div>'
        f'<div class="lcd-in" style="font-size:{in_size}rem">{html.escape(inp) or "&nbsp;"}</div>'
        f'<div class="lcd-res{cls}" style="font-size:{res_size}rem">{html.escape(res) or "&nbsp;"}</div></div>'
    )


GRID = [
    [("mem", "MC"), ("mem", "MR"), ("mem", "M+"), ("mem", "M−"), ("mem", "MS")],
    [("tog", "ANGLE"), ("tog", "HYP"), ("tog", "INV"), ("ext", "EXP"), ("ext", "RAN")],
    [("fn", "SIN"), ("fn", "COS"), ("fn", "TAN"), ("fn", "PI"), ("fn", "E")],
    [("fn", "LN"), ("fn", "LOG"), ("fn", "SQRT"), ("fn", "POW"), ("fn", "FACT")],
    [("fn", "CUBE"), ("fn", "RECIP"), ("fn", "ABS"), ("fn", "NPR"), ("fn", "NCR")],
    [("ext", "("), ("ext", ")"), ("ext", "%"), ("ext", "MOD"), ("ext", "DEG")],
    [("num", "7"), ("num", "8"), ("num", "9"), ("op", "÷"), ("act", "DEL")],
    [("num", "4"), ("num", "5"), ("num", "6"), ("op", "×"), ("act", "AC")],
    [("num", "1"), ("num", "2"), ("num", "3"), ("op", "−"), ("ext", "ANS")],
    [("num", "0"), ("num", "."), ("num", "SIGN"), ("op", "+"), ("eq", "=")],
]
SEPARATE_AFTER = {0, 5}      # in rows ke baad patli line aati hai (memory | science | keypad)
KEYS = {a: f"{k}_{r}{c}" for r, row in enumerate(GRID) for c, (k, a) in enumerate(row)}

STATIC_LABELS = {
    "PI": "π", "E": "e", "FACT": "n!", "DEL": "⌫", "ANS": "Ans", "SIGN": "±",
    "INV": "SHIFT", "HYP": "hyp", "EXP": "EXP", "RAN": "Ran#", "NPR": "nPr",
    "NCR": "nCr", "MOD": "mod", "DEG": "°",
}
ALT_LABELS = {  # (normal, shift)
    "LN": ("ln", "eˣ"), "LOG": ("log", "10ˣ"), "SQRT": ("√", "x²"),
    "POW": ("xʸ", "ʸ√x"), "CUBE": ("x³", "∛x"), "RECIP": ("1/x", "⌈x⌉"), "ABS": ("|x|", "⌊x⌋"),
}


def label(a: str) -> str:
    s = st.session_state
    if a == "ANGLE":
        return s.angle
    if a in TRIG:
        return TRIG[a] + ("h" if s.hyp else "") + ("⁻¹" if s.inv else "")
    if a in ALT_LABELS:
        return ALT_LABELS[a][s.inv]
    return STATIC_LABELS.get(a, a)


# ════════════════════════════════════════════════════════════════════
#  4.  RENDER  (fragment = sirf calculator rerun hota hai => smooth)
# ════════════════════════════════════════════════════════════════════
_fragment = getattr(st, "fragment", None) or getattr(st, "experimental_fragment", None) \
    or (lambda f: f)

st.markdown(STYLE, unsafe_allow_html=True)
st.markdown('<div class="topbar"><span class="model">SCIENTIFIC</span>'
            '<span class="solar"></span></div>', unsafe_allow_html=True)


@_fragment
def calculator():
    s = st.session_state
    active = [KEYS[a] for a, on in (("INV", s.inv), ("HYP", s.hyp)) if on]
    if active:
        rules = "".join(
            f"div.st-key-{k}{{--bg:#f5b942 !important;--edge:#b9811c !important;--fg:#1f1500 !important;}}"
            for k in active)
        st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)

    st.markdown(lcd_html(), unsafe_allow_html=True)

    for r, row in enumerate(GRID):
        cols = st.columns(5)
        for c, (kind, action) in enumerate(row):
            cols[c].button(label(action), key=f"{kind}_{r}{c}", on_click=press,
                           args=(action,), use_container_width=True)
        if r in SEPARATE_AFTER:
            st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

    with st.expander("History"):
        if s.history:
            for ex, res in s.history[:15]:
                st.markdown(f"`{ex}` = **{res}**")
            st.button("Clear history", key="act_clear_hist",
                      on_click=lambda: st.session_state.history.clear())
        else:
            st.caption("Abhi koi calculation nahi hui.")


calculator()
