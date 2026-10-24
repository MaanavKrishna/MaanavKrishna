#!/usr/bin/env python3
"""Build the SVG graphics used by the profile README.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Design: Swiss editorial. Paper, ink and one ultramarine accent, a bento grid of
project tiles, a split-flap "now shipping" board, and a tools x projects matrix.
Every SVG embeds a subset of the fonts in scripts/fonts so type renders the same
everywhere. Tiles paint their own background; section headers are transparent
and use a blue that reads on both GitHub light and dark mode.
"""
import base64
import io
import math
import os
import random
from collections import defaultdict
from xml.dom import minidom
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")

# ---------------------------------------------------------------- tokens
PAPER = "#F2EFE7"
INK = "#0C0C0C"
COBALT = "#1F3BFF"
GRAY = "#86827A"
HEAD = "#5A72FF"      # section headers and accents on ink: readable on light and dark
DIM = "#8E8A82"       # muted text on ink

THEMES = {
    "paper": dict(bg=PAPER, fg=INK, mut=GRAY, line="#D2CDC1", grid="#E2DED3", acc=COBALT, on_acc=PAPER,
                  panel=INK, panel_fg=PAPER, panel_mut=DIM, hl="#8C9CFF"),
    "ink": dict(bg=INK, fg=PAPER, mut=DIM, line="#2C2C2C", grid="#1A1A1A", acc=HEAD, on_acc=PAPER,
                panel="#1D1D1D", panel_fg=PAPER, panel_mut=DIM, hl="#8C9CFF"),
    "cobalt": dict(bg=COBALT, fg=PAPER, mut="#BCC5FF", line="#5069FF", grid="#2E49FF", acc=PAPER, on_acc=COBALT,
                   panel=INK, panel_fg=PAPER, panel_mut=DIM, hl="#8C9CFF"),
}

FONTS = {  # css class -> (file, family, weight, style, fallback)
    "fx": ("inter-tight-latin-800-normal.woff2", "MK Display", 800, "normal", "'Helvetica Neue', Arial, sans-serif"),
    "fh": ("inter-tight-latin-700-normal.woff2", "MK Heading", 700, "normal", "'Helvetica Neue', Arial, sans-serif"),
    "fb": ("inter-tight-latin-500-normal.woff2", "MK Body", 500, "normal", "'Helvetica Neue', Arial, sans-serif"),
    "fs": ("instrument-serif-latin-400-italic.woff2", "MK Serif", 400, "italic", "Georgia, serif"),
    "fm": ("jetbrains-mono-latin-400-normal.woff2", "MK Mono", 400, "normal", "ui-monospace, Menlo, Consolas, monospace"),
    "fmb": ("jetbrains-mono-latin-700-normal.woff2", "MK Mono Bold", 700, "normal", "ui-monospace, Menlo, Consolas, monospace"),
}

BASE_CSS = """
.plot{stroke-dasharray:1;stroke-dashoffset:1;animation:plot 2.2s cubic-bezier(.65,0,.25,1) forwards}
@keyframes plot{to{stroke-dashoffset:0}}
.fade{opacity:0;animation:fade .8s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.3,1.6,.5,1) both}
@keyframes pop{from{transform:scale(0)}to{transform:scale(1)}}
@keyframes pulse{0%,100%{opacity:.3}50%{opacity:1}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}
.spin{transform-box:fill-box;transform-origin:center}
"""

# ---------------------------------------------------------------- font helpers
_tt = {}


def tt(cls):
    if cls not in _tt:
        _tt[cls] = TTFont(os.path.join(FONT_DIR, FONTS[cls][0]))
    return _tt[cls]


def measure(text, cls, size, ls=0.0):
    f = tt(cls)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = sum(hmtx[cmap[ord(c)]][0] if ord(c) in cmap else upm * 0.6 for c in text)
    return w * size / upm + ls * len(text)


def fit(text, cls, size, max_w, ls=0.0):
    while size > 8 and measure(text, cls, size, ls) > max_w:
        size -= 0.5
    return size


def subset_b64(cls, chars):
    f = TTFont(os.path.join(FONT_DIR, FONTS[cls][0]))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "tnum"]
    s = subset.Subsetter(opts)
    s.populate(text=chars + " ")
    s.subset(f)
    buf = io.BytesIO()
    f.flavor = "woff2"
    f.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def T(x, y, s, cls, size, fill, anchor=None, ls=None, extra="", classes=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    c = f"{cls} {classes}".strip()
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{c}" font-size="{size}" fill="{fill}"{a}{l} {extra}>{escape(s)}</text>'


def doc(W, H, body, css="", label=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{escape(label)}"><style>/*FONTS*/{BASE_CSS}{css}</style>{body}</svg>')


def write(name, svg):
    """Embed exactly the glyphs each text element uses, then save."""
    dom = minidom.parseString(svg)
    chars = defaultdict(set)

    def walk(node, cls):
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == "style":
                return
            for k in node.getAttribute("class").split():
                if k in FONTS:
                    cls = k
            for ch in node.childNodes:
                walk(ch, cls)
        elif node.nodeType == node.TEXT_NODE and cls:
            chars[cls].update(node.data)

    walk(dom.documentElement, None)
    css = ""
    for cls in sorted(chars):
        file, fam, weight, style, fallback = FONTS[cls]
        data = subset_b64(cls, "".join(sorted(chars[cls])))
        css += (f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{data}) format('woff2');"
                f"font-weight:{weight};font-style:{style}}}.{cls}{{font-family:'{fam}',{fallback}}}")
    with open(os.path.join(OUT, name), "w") as fh:
        fh.write(svg.replace("/*FONTS*/", css))


# ---------------------------------------------------------------- drawing helpers
def arrow(x1, y, x2, col, w=2):
    d = 1 if x2 > x1 else -1
    return (f'<path d="M{x1},{y}H{x2}M{x2-9*d},{y-6}L{x2},{y}L{x2-9*d},{y+6}" fill="none" stroke="{col}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def check(cx, cy, col, s=1.0, w=3):
    return (f'<path d="M{cx-8*s},{cy} l{6*s},{6*s} l{11*s},{-12*s}" fill="none" stroke="{col}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def cross(cx, cy, col, s=6, w=3):
    return (f'<path d="M{cx-s},{cy-s}L{cx+s},{cy+s}M{cx+s},{cy-s}L{cx-s},{cy+s}" stroke="{col}" stroke-width="{w}" '
            f'stroke-linecap="round"/>')


def open_icon(cx, cy, t, r=24):
    return (f'<g transform="translate({cx},{cy})"><circle r="{r}" fill="none" stroke="{t["fg"]}" stroke-width="1.5" stroke-opacity=".35"/>'
            f'<path class="nudge" d="M-6,6 L6,-6 M-4,-6 H6 V4" fill="none" stroke="{t["fg"]}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/></g>')


NUDGE = ".nudge{animation:nudge 2.6s ease-in-out infinite}@keyframes nudge{0%,70%,100%{transform:none}80%{transform:translate(2.5px,-2.5px)}}"


def phone(x, y, w, h, t, plot=True):
    cls = ' pathLength="1" class="plot"' if plot else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(w, h)*0.18:.0f}" fill="{t["bg"]}" stroke="{t["fg"]}" '
            f'stroke-width="2.5"{cls}/>')


def dot_grid(pid, step, col):
    return f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.5" fill="{col}"/></pattern>'


def place(art, x, y, w, h, bw=600, bh=340):
    s = min(w / bw, h / bh)
    ox = x + (w - bw * s) / 2
    oy = y + (h - bh * s) / 2
    return f'<g transform="translate({ox:.1f},{oy:.1f}) scale({s:.4f})">{art}</g>'


# ================================================================ ART (local bw x 340 box)
def art_aftershock(t, bw=600):
    n = int((bw - 40) / 4) + 1
    c = bw / 2
    pts = []
    for i in range(n):
        x = 20 + i * 4
        q = math.exp(-((x - c) / 40) ** 2)
        y = 112 + math.sin(i * 1.9) * (3 + 58 * q) + math.sin(i * 0.5) * 2
        pts.append(f"{x},{y:.1f}")
    seis = "M" + " L".join(pts)
    s = bw - 130
    runs = ""
    for i in range(3):
        x = 156 + i * 40
        runs += (f'<g class="run" style="animation-delay:{0.22*i:.2f}s"><rect x="{x}" y="216" width="30" height="30" rx="4" fill="none" '
                 f'stroke="{t["fg"]}" stroke-width="2"/>{cross(x+15, 231, t["fg"], 5.5, 2.5)}</g>')
    for i in range(3):
        x = s + i * 40
        runs += (f'<g class="run" style="animation-delay:{1.3+0.22*i:.2f}s"><rect x="{x}" y="216" width="30" height="30" rx="4" '
                 f'fill="{t["acc"]}"/>{check(x+15, 232, t["on_acc"], .85, 2.8)}</g>')
    a1, a2 = 292, s - 86
    return f"""
{T(20, 24, "PROD / CHECKOUT-API", "fm", 11, t["mut"], ls=1)}
<line x1="20" y1="112" x2="{bw-20}" y2="112" stroke="{t["line"]}" stroke-dasharray="2 5"/>
<path d="{seis}" pathLength="1" class="seis" fill="none" stroke="{t["fg"]}" stroke-width="2" stroke-linejoin="round"/>
<g class="mark"><line x1="{c}" y1="52" x2="{c}" y2="172" stroke="{t["acc"]}" stroke-width="2"/>
<rect x="{c-44}" y="32" width="88" height="24" rx="12" fill="{t["acc"]}"/>{T(c, 49, "INC-12", "fmb", 12, t["on_acc"], "middle", 1)}</g>
{T(20, 226, "a3f9c1^", "fmb", 12, t["fg"])}{T(20, 248, "before the fix", "fs", 18, t["mut"])}
{runs}
{T((a1+a2)/2, 214, "time travel", "fs", 18, t["mut"], "middle")}{arrow(a1, 231, a2, t["fg"])}
{T(s-72, 226, "a3f9c1", "fmb", 12, t["fg"])}{T(s-72, 248, "the fix", "fs", 18, t["mut"])}
<line x1="20" y1="296" x2="{bw-20}" y2="296" stroke="{t["line"]}"/>
{T(20, 322, "tests/aftershock/test_inc_12.py", "fm", 11, t["mut"])}{T(bw-20, 322, "ADMITTED: FAILS BEFORE, PASSES ON", "fmb", 11, t["acc"], "end", 1.2)}"""


AFTERSHOCK_CSS = """.seis{stroke-dasharray:1;stroke-dashoffset:1;animation:seis 7s cubic-bezier(.6,0,.3,1) infinite}
@keyframes seis{0%{stroke-dashoffset:1}40%,92%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}
.mark{opacity:0;animation:mark 7s infinite}@keyframes mark{0%,22%{opacity:0}26%,92%{opacity:1}100%{opacity:0}}
.run{opacity:0;animation:run 7s infinite}@keyframes run{0%,42%{opacity:0;transform:translateY(6px)}48%,92%{opacity:1;transform:none}100%{opacity:0}}"""


def art_pyweb(t, bw=600):
    code = [("from pyweb import App, server", "fg"), ("@server", "hl"), ("def sign(name: str) -> list:", "fg"),
            ("    ENTRIES.append(name)", "mut"), ("def submit():", "fg"), ("    entries = sign(name)", "mut"), ("<button>Sign</button>", "mut")]
    ys = [86, 114, 136, 158, 192, 214, 248]
    colmap = {"fg": t["panel_fg"], "hl": t["hl"], "mut": t["panel_mut"]}
    lines = "".join(f'<g class="fade" style="animation-delay:{0.1*i:.2f}s">' + T(36, y, c, "fm", 12, colmap[k]) + "</g>"
                    for i, ((c, k), y) in enumerate(zip(code, ys)))
    return f"""
<rect x="16" y="16" width="304" height="268" rx="14" fill="{t["panel"]}"/>
<circle cx="38" cy="40" r="5" fill="{t["panel_mut"]}"/><circle cx="56" cy="40" r="5" fill="{t["panel_mut"]}"/><circle cx="74" cy="40" r="5" fill="{t["hl"]}"/>
{T(302, 45, "app.pyweb", "fm", 11, t["panel_mut"], "end")}
{lines}
<path id="ps" d="M320,124 H350 V86 H380" fill="none" stroke="{t["fg"]}" stroke-width="1.5" stroke-dasharray="4 4"/>
<path id="pb" d="M320,204 H350 V226 H380" fill="none" stroke="{t["fg"]}" stroke-width="1.5" stroke-dasharray="4 4"/>
<rect x="-5" y="-5" width="10" height="10" fill="{t["acc"]}"><animateMotion dur="2s" repeatCount="indefinite"><mpath href="#ps"/></animateMotion></rect>
<rect x="-5" y="-5" width="10" height="10" fill="{t["acc"]}"><animateMotion dur="2s" begin="1s" repeatCount="indefinite"><mpath href="#pb"/></animateMotion></rect>
<rect x="380" y="30" width="204" height="112" rx="12" fill="none" stroke="{t["fg"]}" stroke-width="2"/>
{T(398, 58, "SERVER", "fmb", 11, t["fg"], ls=2)}{T(398, 92, "sign() becomes", "fh", 17, t["fg"])}{T(398, 114, "a typed RPC", "fh", 17, t["fg"])}
<rect x="380" y="170" width="204" height="112" rx="12" fill="{t["acc"]}"/>
{T(398, 198, "BROWSER", "fmb", 11, t["on_acc"], ls=2)}{T(398, 232, "submit() becomes", "fh", 17, t["on_acc"])}{T(398, 254, "312 bytes of JS", "fh", 17, t["on_acc"])}
{T(16, 322, "one .pyweb file, split line by line by the compiler", "fs", 18, t["mut"])}"""


def art_hum(t, bw=600):
    bars = ""
    for i in range(26):
        x = 22 + i * 11.5
        h = 20 + 96 * abs(math.sin(i * 0.43)) * (0.55 + 0.45 * math.sin(i * 0.2 + 1))
        bars += (f'<rect class="eq" x="{x:.1f}" y="{124-h/2:.0f}" width="6" height="{h:.0f}" rx="3" fill="{t["fg"]}" '
                 f'style="animation-delay:-{(i*0.11) % 1.3:.2f}s"/>')
    chips, x = "", 20
    for label, p, style in [("I want that", "72%", "solid"), ("too loud", "21%", "line"), ("maybe", "", "dash")]:
        txt = label + ("  " + p if p else "")
        w = measure(txt, "fh", 15) + 28
        if style == "solid":
            chips += f'<rect x="{x}" y="252" width="{w:.0f}" height="36" rx="18" fill="{t["fg"]}"/>' + T(x + 14, 275, txt, "fh", 15, t["bg"])
        elif style == "line":
            chips += f'<rect x="{x}" y="252" width="{w:.0f}" height="36" rx="18" fill="none" stroke="{t["fg"]}" stroke-width="1.5"/>' + T(x + 14, 275, txt, "fh", 15, t["fg"])
        else:
            chips += f'<rect x="{x}" y="252" width="{w:.0f}" height="36" rx="18" fill="none" stroke="{t["mut"]}" stroke-width="1.5" stroke-dasharray="4 4"/>' + T(x + 14, 275, txt, "fh", 15, t["mut"])
        x += w + 10
    cx, cy, r = 482, 124, 52
    ring = "FIRST PLACE  /  ML EMPOWERMENT BUILD CHALLENGE 3.0  /  "
    size = fit(ring, "fmb", 12, 2 * math.pi * r * 0.98, 1)
    return f"""
{T(20, 24, "LISTENING / ON-DEVICE", "fm", 11, t["mut"], ls=1)}
{bars}
<g class="head"><line x1="18" y1="60" x2="18" y2="188" stroke="{t["acc"]}" stroke-width="2.5"/><circle cx="18" cy="56" r="6" fill="{t["acc"]}"/></g>
<circle cx="{cx}" cy="{cy}" r="{r+24}" fill="{t["acc"]}"/>
<g class="spin seal"><circle cx="{cx}" cy="{cy}" r="{r}" fill="none"/><path id="sp" d="M{cx-r},{cy} a{r},{r} 0 1,1 {2*r},0 a{r},{r} 0 1,1 {-2*r},0" fill="none"/>
<text class="fmb" font-size="{size}" fill="{t["on_acc"]}" letter-spacing="1"><textPath href="#sp">{escape(ring)}</textPath></text></g>
<circle cx="{cx}" cy="{cy}" r="{r-14}" fill="none" stroke="{t["on_acc"]}" stroke-opacity=".5"/>
{T(cx, cy+12, "1st", "fx", 38, t["on_acc"], "middle", -1.5)}
{T(20, 236, "CONFORMAL SET: SAYS MAYBE INSTEAD OF BLUFFING", "fm", 10, t["mut"], ls=.5)}
{chips}
{T(20, 324, "90% on 4,703 held-out clips. Audio never leaves the device.", "fs", 17, t["mut"])}"""


HUM_CSS = """.eq{transform-box:fill-box;transform-origin:center;animation:eq 1.3s ease-in-out infinite alternate}
@keyframes eq{from{transform:scaleY(.2)}to{transform:scaleY(1)}}
.head{animation:head 4.4s linear infinite}@keyframes head{from{transform:translateX(0)}to{transform:translateX(300px)}}
.seal{animation:spin 22s linear infinite}"""


def art_cadabra(t, bw=600):
    c = bw / 2
    balls = ""
    for dx, r, col, d in [(-68, 13, t["fg"], 0), (0, 11, t["acc"], -.4), (62, 15, t["fg"], -.8)]:
        balls += f'<circle class="ball" cx="{c+dx}" cy="{196-r}" r="{r}" fill="{col}" style="animation-delay:{d}s"/>'
    left, right = 62, bw - 62
    ideas = ""
    for txt, x, d in [("laser sharks", left, 0), ("zero gravity", right, -1.4), ("disco floor", left, -2.8), ("more chaos", right, -4.2)]:
        ideas += f'<g class="idea" style="animation-delay:{d}s">' + T(x, 208, txt, "fs", 20, t["fg"], "middle") + "</g>"
    sticks = ""
    for x, d in [(left, 0), (right, -.6)]:
        sticks += (phone(x - 24, 226, 48, 78, t) + f'<circle cx="{x}" cy="265" r="12" fill="none" stroke="{t["fg"]}" stroke-width="1.5"/>'
                   f'<circle class="stick" cx="{x}" cy="265" r="5" fill="{t["acc"]}" style="animation-delay:{d}s"/>')
    votes = ""
    if bw > 700:
        for k, (lab, pct) in enumerate([("Ring Out", .62), ("Paint Wars", .24), ("Overload", .14)]):
            y = 70 + k * 46
            vx = c + 200
            votes += (T(vx, y, lab, "fh", 14, t["fg"]) + f'<rect x="{vx}" y="{y+8}" width="150" height="8" rx="4" fill="{t["line"]}"/>'
                      f'<rect class="vote" x="{vx}" y="{y+8}" width="{150*pct:.0f}" height="8" rx="4" fill="{t["acc"] if k == 0 else t["fg"]}" style="animation-delay:{.3*k:.1f}s"/>'
                      + T(vx + 160, y + 16, f"{int(pct*100)}%", "fm", 11, t["mut"]))
        votes = T(c + 200, 44, "THE ROOM VOTES", "fm", 10, t["mut"], ls=1.5) + votes
    return f"""
{T(20, 24, "IDEA STORM / VOTE / BUILD", "fm", 11, t["mut"], ls=1)}
<rect x="{c-150}" y="46" width="300" height="176" rx="12" fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="2.5" pathLength="1" class="plot"/>
<path d="M{c-18},222 V238 H{c+18} V222 M{c-42},244 H{c+42}" fill="none" stroke="{t["fg"]}" stroke-width="2.5" stroke-linecap="round"/>
{T(c-134, 70, "RING OUT", "fmb", 11, t["fg"], ls=1.5)}{T(c+134, 70, "GRAVITY x0.4", "fm", 10, t["acc"], "end", 1)}
<line x1="{c-134}" y1="196" x2="{c+134}" y2="196" stroke="{t["fg"]}" stroke-width="2"/>
<rect class="crate" x="{c+98}" y="170" width="24" height="24" rx="3" fill="none" stroke="{t["fg"]}" stroke-width="2.5"/>
{balls}{sticks}{ideas}{votes}
{T(c, 326, "three AI pitches, one vote, a playable game in seconds", "fs", 18, t["mut"], "middle")}"""


CADABRA_CSS = """.ball{animation:bounce .85s cubic-bezier(.45,0,.55,1) infinite alternate}
@keyframes bounce{from{transform:translateY(0)}to{transform:translateY(-96px)}}
.crate{transform-box:fill-box;transform-origin:center;animation:spin 3.2s linear infinite}
.idea{opacity:0;animation:rise 5.6s ease-in infinite}
@keyframes rise{0%{opacity:0;transform:translateY(16px)}12%,45%{opacity:1}75%,100%{opacity:0;transform:translateY(-130px)}}
.stick{animation:wig 1.3s ease-in-out infinite alternate}@keyframes wig{from{transform:translate(-5px,3px)}to{transform:translate(5px,-4px)}}
.vote{transform-box:fill-box;transform-origin:left;animation:vote 4s cubic-bezier(.2,.8,.2,1) infinite}
@keyframes vote{0%{transform:scaleX(0)}40%,90%{transform:scaleX(1)}100%{transform:scaleX(1);opacity:.4}}"""


def art_deadlock(t, bw=600):
    A, B, C = (110, 214), (300, 84), (490, 214)
    loop = f"M{A[0]},{A[1]} Q160,110 {B[0]},{B[1]} Q440,110 {C[0]},{C[1]} Q300,320 {A[0]},{A[1]}"
    faint = [(28, 96), (572, 96), (40, 298), (560, 298)]
    fe = "".join(f'<line x1="{x}" y1="{y}" x2="{A[0] if x < 300 else C[0]}" y2="{A[1] if x < 300 else C[1]}" stroke="{t["mut"]}" stroke-dasharray="2 5"/>'
                 f'<circle cx="{x}" cy="{y}" r="6" fill="{t["bg"]}" stroke="{t["mut"]}" stroke-width="1.5"/>' for x, y in faint)

    def node(p, label, key=False):
        ring = (f'<circle class="spin kring" cx="{p[0]}" cy="{p[1]}" r="34" fill="none" stroke="{t["acc"]}" stroke-width="2" stroke-dasharray="5 6"/>') if key else ""
        ly = p[1] + 50 if p[1] > 150 else p[1] - 32
        return (f'{ring}<circle cx="{p[0]}" cy="{p[1]}" r="21" fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="2.5"/>'
                f'<circle cx="{p[0]}" cy="{p[1]}" r="7" fill="{t["fg"]}"/>' + T(p[0], ly, label, "fh", 16, t["fg"], "middle"))
    dots = "".join(f'<circle r="6" fill="{t["fg"]}"><animateMotion dur="4.5s" begin="-{k*1.5}s" repeatCount="indefinite"><mpath href="#loop"/></animateMotion></circle>' for k in range(3))
    return f"""
{T(20, 24, "3 CAN TRADE WHERE 2 CAN'T", "fm", 11, t["mut"], ls=1)}
{fe}
<path id="loop" d="{loop}" pathLength="1" class="plot" fill="none" stroke="{t["acc"]}" stroke-width="3"/>
{dots}
{node(A, "Studio North", True)}{node(B, "Motionhaus")}{node(C, "Wordcraft")}
{T(184, 132, "video", "fs", 18, t["mut"], "middle")}{T(416, 132, "copy", "fs", 18, t["mut"], "middle")}{T(300, 250, "design", "fs", 18, t["mut"], "middle")}
{T(110, 168, "KEYSTONE", "fmb", 10, t["acc"], "middle", 1.5)}
{T(300, 326, "graph traversal finds the loop, humans approve it", "fs", 17, t["mut"], "middle")}"""


DEADLOCK_CSS = ".kring{animation:spin 10s linear infinite}"


def art_countersign(t, bw=600):
    sets = [("velvet", "harbor", "comet"), ("maple", "orbit", "lantern"), ("cobalt", "river", "ember")]

    def ph(x):
        g = phone(x, 46, 136, 230, t)
        g += f'<rect x="{x+48}" y="58" width="40" height="5" rx="2.5" fill="{t["fg"]}"/>'
        g += T(x + 68, 92, "COUNTERSIGN", "fmb", 9, t["mut"], "middle", 1.5)
        for k, ws in enumerate(sets):
            g += f'<g class="w" style="animation-delay:-{(3*(3-k)) % 9}s">'
            for j, w in enumerate(ws):
                g += T(x + 68, 140 + j * 36, w, "fx", 25, t["fg"], "middle", -.8)
            g += "</g>"
        g += f'<rect x="{x+20}" y="246" width="96" height="5" rx="2.5" fill="{t["line"]}"/><rect class="tick" x="{x+20}" y="246" width="96" height="5" rx="2.5" fill="{t["acc"]}"/>'
        return g
    wave = "M" + " L".join(f"{230+i*5},{214+math.sin(i*0.9)*(14*math.sin(i*0.12)+3):.1f}" for i in range(29))
    return f"""
{ph(14)}{ph(450)}
<line x1="150" y1="104" x2="450" y2="104" stroke="{t["fg"]}" stroke-dasharray="3 5" stroke-opacity=".6"/>
{T(300, 92, "same words, every minute", "fs", 17, t["mut"], "middle")}
<path d="M300,122 L330,133 V160 C330,180 317,193 300,200 C283,193 270,180 270,160 V133 Z" fill="{t["acc"]}"/>
{check(300, 160, t["on_acc"], .85, 3)}
<path d="{wave}" fill="none" stroke="{t["fg"]}" stroke-width="2" stroke-opacity=".7"/>
<line x1="232" y1="236" x2="368" y2="196" stroke="{t["acc"]}" stroke-width="4" stroke-linecap="round"/>
{T(300, 266, "VOICE CLONE:", "fmb", 10, t["acc"], "middle", 1.5)}{T(300, 282, "NO ANSWER", "fmb", 10, t["acc"], "middle", 1.5)}
{T(300, 326, "offline, no account, nothing leaves the phone", "fs", 17, t["mut"], "middle")}"""


COUNTERSIGN_CSS = """.w{opacity:0;animation:show 9s infinite}@keyframes show{0%,30%{opacity:1}33.3%,100%{opacity:0}}
.tick{transform-box:fill-box;transform-origin:left;animation:tk 3s linear infinite}@keyframes tk{from{transform:scaleX(1)}to{transform:scaleX(0)}}"""


def art_couchpad(t, bw=600):
    phones_svg, paths, packets = "", "", ""
    for i, y in enumerate((60, 134, 208)):
        phones_svg += phone(16, y, 100, 56, t)
        phones_svg += (f'<circle cx="44" cy="{y+28}" r="13" fill="none" stroke="{t["fg"]}" stroke-width="1.5"/>'
                       f'<circle class="stick" cx="44" cy="{y+28}" r="5" fill="{t["fg"]}" style="animation-delay:-{i*.45:.2f}s"/>'
                       f'<circle cx="86" cy="{y+20}" r="6" fill="{t["acc"] if i == 0 else t["fg"]}"/><circle cx="99" cy="{y+36}" r="6" fill="{t["fg"]}"/>')
        dash = ' stroke-dasharray="5 5"' if i == 2 else ""
        paths += f'<path id="c{i}" d="M116,{y+28} C220,{y+28} 236,154 330,154" fill="none" stroke="{t["fg"]}" stroke-width="1.5" stroke-opacity=".7"{dash}/>'
        for k in range(2):
            packets += (f'<rect x="-5" y="-5" width="10" height="10" rx="2" fill="{t["acc"]}"><animateMotion dur="1.7s" begin="-{i*0.55+k*0.85:.2f}s" '
                        f'repeatCount="indefinite"><mpath href="#c{i}"/></animateMotion></rect>')
    qr = "".join(f'<rect x="{536+(j % 5)*6}" y="{72+(j//5)*6}" width="5" height="5" fill="{t["fg"]}" fill-opacity="{1 if (j*7) % 3 else .15}"/>' for j in range(25))
    return f"""
{T(20, 24, "SCAN / JOIN / PLAY", "fm", 11, t["mut"], ls=1)}
{paths}{packets}{phones_svg}
<rect x="330" y="56" width="254" height="180" rx="12" fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="2.5" pathLength="1" class="plot"/>
<path d="M440,236 V250 H474 V236 M416,256 H498" fill="none" stroke="{t["fg"]}" stroke-width="2.5" stroke-linecap="round"/>
{qr}{T(346, 80, "ROOM K7QX", "fmb", 11, t["fg"], ls=1.5)}
<circle class="p1" cx="410" cy="170" r="11" fill="{t["acc"]}"/><circle class="p2" cx="490" cy="156" r="11" fill="{t["fg"]}"/><circle class="p3" cx="450" cy="204" r="10" fill="none" stroke="{t["fg"]}" stroke-width="3"/>
{T(300, 326, "WebRTC, with a relay when the direct path is blocked", "fs", 17, t["mut"], "middle")}"""


COUCHPAD_CSS = """.stick{animation:wig 1.2s ease-in-out infinite alternate}@keyframes wig{from{transform:translate(-5px,3px)}to{transform:translate(5px,-4px)}}
.p1{animation:m1 2.4s ease-in-out infinite alternate}.p2{animation:m2 2s ease-in-out infinite alternate}.p3{animation:m3 2.8s ease-in-out infinite alternate}
@keyframes m1{to{transform:translate(60px,-40px)}}@keyframes m2{to{transform:translate(-60px,30px)}}@keyframes m3{to{transform:translate(80px,-14px)}}"""


def art_aeropulse(t, bw=600):
    xs = list(range(30, 571, 30))
    ys = [226 - 24 * math.sin(i * 0.5) - i * 3.6 + 7 * math.sin(i * 1.4) for i in range(len(xs))]
    line = "M" + " L".join(f"{x},{y:.1f}" for x, y in zip(xs, ys))
    ticks = "".join(f'<line x1="{x}" y1="276" x2="{x}" y2="282" stroke="{t["fg"]}"/>' for x in xs[::3])
    return f"""
<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{t["acc"]}" stroke-opacity=".4" stroke-width="2"/></pattern></defs>
{T(20, 24, "DEL-BOM  /  1-2 WEEKS OUT", "fm", 11, t["mut"], ls=1)}
<rect class="fade" x="30" y="150" width="540" height="56" fill="url(#hatch)" style="animation-delay:.3s"/>
<line x1="30" y1="150" x2="570" y2="150" stroke="{t["acc"]}" stroke-opacity=".5" stroke-dasharray="3 4"/>
<line x1="30" y1="206" x2="570" y2="206" stroke="{t["acc"]}" stroke-opacity=".5" stroke-dasharray="3 4"/>
{T(36, 166, "USUAL", "fmb", 10, t["acc"], ls=1.5)}
<line x1="30" y1="276" x2="570" y2="276" stroke="{t["fg"]}" stroke-width="2"/>{ticks}
<path d="{line}" pathLength="1" class="plot" fill="none" stroke="{t["fg"]}" stroke-width="2.6" stroke-linejoin="round"/>
<circle cx="{xs[-1]}" cy="{ys[-1]:.1f}" r="13" fill="{t["acc"]}" fill-opacity=".25" style="animation:pulse 1.6s infinite"/>
<circle cx="{xs[-1]}" cy="{ys[-1]:.1f}" r="6" fill="{t["acc"]}"/>
<g class="fade" style="animation-delay:2.2s"><rect x="{xs[-1]-118}" y="{ys[-1]-46:.0f}" width="104" height="28" rx="14" fill="{t["fg"]}"/>{T(xs[-1]-66, ys[-1]-27, "HIGH TODAY", "fmb", 10, t["bg"], "middle", 1.2)}</g>
<path id="arc" d="M24,104 Q300,14 586,70" fill="none" stroke="{t["mut"]}" stroke-dasharray="2 7"/>
<g><animateMotion dur="7s" repeatCount="indefinite" rotate="auto"><mpath href="#arc"/></animateMotion>
<path d="M-15,0 L10,-2.5 L17,0 L10,2.5 Z M-2,-1.5 L-9,-13 L-3,-13 L6,-1.5 Z M-2,1.5 L-9,13 L-3,13 L6,1.5 Z M-15,0 L-19,-7 L-15,-7 L-10,-1 Z M-15,0 L-19,7 L-15,7 L-10,1 Z" fill="{t["fg"]}"/></g>
{T(30, 302, "90 DAYS AGO", "fm", 10, t["mut"])}{T(570, 302, "TODAY", "fm", 10, t["mut"], "end")}
{T(300, 330, "usual = the middle half of the last 90 days", "fs", 17, t["mut"], "middle")}"""


def art_dueproof(t, bw=600):
    doc_lines = "".join(f'<rect x="38" y="{92+i*20}" width="{w}" height="5" rx="2.5" fill="{t["mut"]}" fill-opacity=".55"/>'
                        for i, w in enumerate([150, 136, 160, 96, 154, 148, 120, 144, 90]))
    rows = [("Reply to notice", "23 NOV", True), ("Personal hearing", "02 DEC", False), ("Amount demanded", "RS 4.1L", False)]
    reg = ""
    for i, (lab, val, hl) in enumerate(rows):
        y = 124 + i * 40
        reg += (f'<line x1="296" y1="{y+14}" x2="568" y2="{y+14}" stroke="{t["line"]}"/>'
                + (f'<rect x="296" y="{y-11}" width="4" height="16" fill="{t["acc"]}"/>' if hl else "")
                + T(308, y, lab, "fh" if hl else "fb", 15, t["fg"] if hl else t["mut"])
                + T(568, y, val, "fmb", 12, t["acc"] if hl else t["fg"], "end", 1))
    return f"""
{T(20, 24, "GST NOTICE  /  ENGLISH + 22 INDIAN LANGUAGES", "fm", 11, t["mut"], ls=1)}
<path d="M20,46 L184,46 L220,82 L220,296 L20,296 Z" fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="2" pathLength="1" class="plot"/>
<path d="M184,46 V82 H220" fill="none" stroke="{t["fg"]}" stroke-width="2"/>
{doc_lines}
<rect class="box" x="32" y="144" width="174" height="34" rx="3" fill="none" stroke="{t["acc"]}" stroke-width="2.5" pathLength="1"/>
<g class="fade" style="animation-delay:1.6s"><rect x="150" y="128" width="58" height="18" rx="9" fill="{t["acc"]}"/>{T(179, 141, "EXACT", "fmb", 9, t["on_acc"], "middle", 1.2)}</g>
<path class="lead" d="M206,161 C244,161 252,124 290,124" fill="none" stroke="{t["acc"]}" stroke-width="2" stroke-dasharray="5 5"/>
<rect x="280" y="52" width="304" height="244" rx="12" fill="none" stroke="{t["fg"]}" stroke-width="2"/>
{T(296, 82, "REGISTER  /  WHAT IS OWED", "fmb", 11, t["fg"], ls=1.5)}
{reg}
<rect x="296" y="244" width="272" height="34" rx="17" fill="{t["acc"]}"/>{T(432, 266, "30 DAYS, COUNTED FROM RECEIPT", "fmb", 10, t["on_acc"], "middle", 1)}
{T(300, 330, "every entry is outlined on the page it came from", "fs", 17, t["mut"], "middle")}"""


DUEPROOF_CSS = """.box{stroke-dasharray:1;stroke-dashoffset:1;animation:box 4.5s cubic-bezier(.6,0,.3,1) infinite}
@keyframes box{0%{stroke-dashoffset:1;opacity:1}30%,88%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}
.lead{animation:flow 1s linear infinite}@keyframes flow{to{stroke-dashoffset:-20}}"""


# ================================================================ TILES
def tile(name, size, theme, idx, kind, title, desc, tags, art_fn, css=""):
    t = THEMES[theme]
    W, H = (1300, 720) if size == "wide" else (640, 720)
    tag_str = "  /  ".join(x.upper() for x in tags)
    idx_col = t["fg"] if theme == "cobalt" else t["acc"]
    body = f'<defs>{dot_grid("dg", 24, t["grid"])}<clipPath id="clip"><rect width="{W}" height="{H}" rx="30"/></clipPath></defs>'
    body += f'<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{t["bg"]}"/>'
    if size == "wide":
        body += f'<rect width="{W}" height="540" fill="url(#dg)"/>'
        body += T(56, 76, idx, "fmb", 14, idx_col, ls=1) + T(96, 76, kind.upper(), "fm", 14, t["mut"], ls=1.5)
        body += open_icon(W - 64, 66, t)
        body += place(art_fn(t, 1000), 56, 112, W - 112, 410, bw=1000)
        body += f'<line x1="56" y1="556" x2="{W-56}" y2="556" stroke="{t["line"]}"/>'
        body += T(50, 652, title, "fx", 88, t["fg"], ls=-3.8)
        dx = 50 + measure(title, "fx", 88, -3.8) + 44
        maxw = W - 56 - dx
        body += T(dx, 612, desc[0], "fb", fit(desc[0], "fb", 23, maxw), t["fg"])
        body += T(dx, 642, desc[1], "fb", fit(desc[1], "fb", 23, maxw), t["mut"])
        body += T(dx, 682, tag_str, "fm", 13, t["mut"], ls=1)
    else:
        body += T(40, 72, idx, "fmb", 14, idx_col, ls=1) + T(80, 72, kind.upper(), "fm", 13, t["mut"], ls=1.5)
        body += open_icon(W - 56, 62, t)
        body += place(art_fn(t), 34, 104, W - 68, 352)
        body += f'<line x1="40" y1="478" x2="{W-40}" y2="478" stroke="{t["line"]}"/>'
        body += T(37, 556, title, "fx", fit(title, "fx", 68, W - 80, -2.8), t["fg"], ls=-2.8)
        body += T(40, 598, desc[0], "fb", fit(desc[0], "fb", 21, W - 80), t["fg"])
        body += T(40, 626, desc[1], "fb", fit(desc[1], "fb", 21, W - 80), t["mut"])
        body += T(40, 680, tag_str, "fm", fit(tag_str, "fm", 12, W - 80, 1), t["mut"], ls=1)
    body += "</g>"
    if theme == "paper":
        body += f'<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="29.5" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>'
    write(name, doc(W, H, body, css + NUDGE, f"{title}: {' '.join(desc)}"))


def sih_banner():
    W, H = 1600, 230
    body = f'<rect width="{W}" height="{H}" rx="30" fill="{INK}"/>'
    body += T(56, 74, "08 + 09", "fmb", 14, HEAD, ls=1) + T(140, 74, "STARTED AT SMART INDIA HACKATHON  /  NOW OPEN SOURCE", "fm", 14, DIM, ls=1.5)
    body += T(52, 170, "Built for India,", "fx", 80, PAPER, ls=-3.2)
    body += T(52 + measure("Built for India,", "fx", 80, -3.2) + 22, 170, "twice.", "fs", 92, HEAD)
    body += T(W - 56, 140, "Two national problem statements,", "fs", 27, DIM, "end")
    body += T(W - 56, 174, "two projects you can run today.", "fs", 27, PAPER, "end")
    write("sih-banner.svg", doc(W, H, body, "", "Built for India, twice. Started at Smart India Hackathon, now open source."))


def sih_half(name, idx, origin, title, desc, tags, art_fn, css=""):
    t = THEMES["paper"]
    W, H = 790, 640
    tag_str = "  /  ".join(x.upper() for x in tags)
    body = f'<defs>{dot_grid("dg", 24, t["grid"])}<clipPath id="clip"><rect width="{W}" height="{H}" rx="30"/></clipPath></defs>'
    body += f'<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{PAPER}"/><rect width="{W}" height="452" fill="url(#dg)"/>'
    body += T(40, 70, idx, "fmb", 14, COBALT, ls=1) + T(80, 70, origin.upper(), "fm", 13, GRAY, ls=1.5)
    body += open_icon(W - 56, 60, t)
    body += place(art_fn(t), 34, 100, W - 68, 336)
    body += f'<line x1="40" y1="460" x2="{W-40}" y2="460" stroke="{t["line"]}"/>'
    body += T(37, 532, title, "fx", 62, INK, ls=-2.6)
    body += T(40, 572, desc[0], "fb", fit(desc[0], "fb", 21, W - 80), INK)
    body += T(40, 600, desc[1], "fb", fit(desc[1], "fb", 21, W - 80), GRAY)
    body += T(W - 40, 532, tag_str, "fm", fit(tag_str, "fm", 12, W - 80 - measure(title, "fx", 62, -2.6) - 30, 1), GRAY, "end", 1)
    body += "</g>"
    body += f'<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="29.5" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>'
    write(name, doc(W, H, body, css + NUDGE, f"{title}: {' '.join(desc)}"))


# ================================================================ HERO with split-flap board
def hero():
    W, H = 1600, 780
    t = THEMES["cobalt"]
    rnd = random.Random(7)
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    rows = [("AFTERSHOCK", "LIVE"), ("PYWEB", "ON PYPI"), ("HUM", "1ST PLACE"), ("CADABRA", "FIRE TV"),
            ("DEADLOCK", "V0.3.0"), ("COUNTERSIGN", "LIVE")]
    bx, by, bw, bh = 892, 128, 652, 440
    slot, tw, th = 28, 25, 40
    board = (f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="20" fill="{INK}"/>'
             + T(bx + 28, by + 44, "NOW SHIPPING", "fmb", 14, PAPER, ls=2)
             + f'<circle cx="{bx + 28 + measure("NOW SHIPPING", "fmb", 14, 2) + 14:.0f}" cy="{by+39}" r="5" fill="{HEAD}" style="animation:pulse 1.4s infinite"/>'
             + T(bx + bw - 28, by + 44, "BOARD 01  /  CHENNAI", "fm", 12, "#7C7972", "end", 1.5)
             + T(bx + 28, by + 84, "PROJECT", "fm", 10, "#7C7972", ls=2) + T(bx + 28 + 12 * slot, by + 84, "STATUS", "fm", 10, "#7C7972", ls=2)
             + f'<line x1="{bx+28}" y1="{by+96}" x2="{bx+bw-28}" y2="{by+96}" stroke="#262626"/>')
    for r, (name, status) in enumerate(rows):
        y = by + 114 + r * 52
        text = name.ljust(11) + " " + status.ljust(9)
        for c, ch in enumerate(text):
            x = bx + 28 + c * slot
            is_status = c >= 12
            win = status == "1ST PLACE" and is_status
            board += f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="4" fill="{COBALT if win else "#242424"}"/>'
            if ch != " ":
                d = r * 0.32 + c * 0.045
                seq = [rnd.choice(alpha) for _ in range(3)] + [ch]
                col = PAPER if (not is_status or win) else "#C9C5BC"
                g = f'<g class="flip" style="animation-delay:{d:.2f}s">'
                for k, s in enumerate(seq):
                    g += T(x + tw / 2, y + 28.5, s, "fmb", 20, col, "middle", extra=f'style="animation-delay:{d:.2f}s"', classes=f"c{k}")
                board += g + "</g>"
            board += f'<line x1="{x}" y1="{y+th/2}" x2="{x+tw}" y2="{y+th/2}" stroke="{INK}" stroke-width="1.5"/>'
    proofs = [("1", "st", "ML Empowerment Build Challenge 3.0"), ("6", "", "hackathon builds shipped"),
              ("2", "x", "Smart India Hackathons"), ("80", "+", "public repositories")]
    proof_svg, defs = "", ""
    for i, (num, suf, lab) in enumerate(proofs):
        x0 = 56 + i * 382
        defs += f'<clipPath id="o{i}"><rect x="{x0}" y="652" width="220" height="80"/></clipPath>'
        size, LH = 72, 84
        x, odo = x0, ""
        for j, ch in enumerate(num):
            target = int(ch)
            seq = list(range(10)) + list(range(target + 1))
            cw = measure("0", "fx", size, -3)
            col = "".join(T(x + cw / 2, 714 + k * LH, str(dg), "fx", size, PAPER, "middle") for k, dg in enumerate(seq))
            odo += f'<g class="odo" style="--d:-{(len(seq)-1)*LH}px;animation-delay:{0.5+0.15*i+0.1*j:.2f}s">{col}</g>'
            x += cw
        x -= (measure("0", "fx", size, -3) - measure(num[-1], "fx", size, -3)) / 2
        proof_svg += f'<g clip-path="url(#o{i})">{odo}</g>'
        if suf:
            proof_svg += f'<g class="fade" style="animation-delay:{1.8+0.15*i:.2f}s">' + T(x + 4, 714 if suf != "st" else 682, suf, "fx", 44 if suf != "st" else 30, t["mut"] if suf == "st" else PAPER) + "</g>"
        proof_svg += T(x0, 752, lab.upper(), "fm", fit(lab.upper(), "fm", 12, 330, 1), t["mut"], ls=1)
        if i:
            proof_svg += f'<line x1="{x0-26}" y1="660" x2="{x0-26}" y2="756" stroke="{t["line"]}"/>'
    cols = "".join(f'<line x1="{56 + k*124}" y1="0" x2="{56 + k*124}" y2="{H}" stroke="{PAPER}" stroke-opacity=".07"/>' for k in range(13))
    body = f"""<defs>{defs}<clipPath id="clip"><rect width="{W}" height="{H}" rx="30"/></clipPath>
<clipPath id="l1"><rect x="0" y="120" width="880" height="200"/></clipPath><clipPath id="l2"><rect x="0" y="320" width="880" height="190"/></clipPath></defs>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="{COBALT}"/>{cols}
{T(56, 66, "MAANAV KRISHNA", "fmb", 14, PAPER, ls=2)}
{T(800, 66, "CSE  /  SRMIST  /  CLASS OF 2029", "fm", 13, t["mut"], "middle", 2)}
{T(1544, 66, "CHENNAI, IN  13.03 N 80.18 E", "fm", 13, t["mut"], "end", 2)}
<line x1="56" y1="92" x2="1544" y2="92" stroke="{PAPER}" stroke-opacity=".3"/>
<g clip-path="url(#l1)"><g class="rise">{T(46, 300, "Maanav", "fx", 208, PAPER, ls=-11)}</g></g>
<g clip-path="url(#l2)"><g class="rise" style="animation-delay:.12s">{T(46, 482, "Krishna", "fx", 208, PAPER, ls=-11)}</g></g>
<g class="fade" style="animation-delay:.5s">{T(58, 556, "builds systems that hold up", "fs", 44, PAPER)}{T(58, 604, "when no one is watching.", "fs", 44, t["mut"])}</g>
{board}
<g transform="translate({bx},{by+bh+30})"><circle cx="7" cy="-5" r="6" fill="{PAPER}" style="animation:pulse 1.4s infinite"/>{T(24, 0, "OPEN TO INTERNSHIPS AND RESEARCH COLLABORATIONS", "fmb", 13, PAPER, ls=1.5)}</g>
<line x1="56" y1="636" x2="1544" y2="636" stroke="{PAPER}" stroke-opacity=".3"/>
{proof_svg}
</g>"""
    css = """.rise{animation:rise 1.2s cubic-bezier(.2,.8,.2,1) both}@keyframes rise{from{transform:translateY(210px)}to{transform:none}}
.c0,.c1,.c2,.c3{animation-duration:14s;animation-iteration-count:infinite;animation-fill-mode:both;animation-timing-function:steps(1)}
.c0{animation-name:c0}.c1{animation-name:c1}.c2{animation-name:c2}.c3{animation-name:c3}
@keyframes c0{0%{opacity:1}1%,100%{opacity:0}}
@keyframes c1{0%{opacity:0}1%{opacity:1}2%,100%{opacity:0}}
@keyframes c2{0%,1%{opacity:0}2%{opacity:1}3%,100%{opacity:0}}
@keyframes c3{0%,2%{opacity:0}3%,100%{opacity:1}}
.flip{transform-box:fill-box;transform-origin:center;animation:flip 14s infinite both}
@keyframes flip{0%,1%,2%,3%,100%{transform:scaleY(1)}.5%,1.5%,2.5%{transform:scaleY(.15)}}
.odo{animation:odo 2s cubic-bezier(.15,.85,.25,1) both}@keyframes odo{from{transform:translateY(0)}to{transform:translateY(var(--d))}}"""
    write("hero.svg", doc(W, H, body, css, "Maanav Krishna builds systems that hold up when no one is watching. CSE at SRMIST, class of 2029, Chennai. Now shipping: Aftershock (live), PyWeb (on PyPI), Hum (1st place), Cadabra (Fire TV), Deadlock (v0.3.0), Countersign (live). Open to internships."))


# ================================================================ section headers (transparent)
def header(name, idx, title, note):
    W, H = 1600, 132
    tw = measure(title, "fx", 60, -2.4)
    body = (T(4, 88, title, "fx", 60, HEAD, ls=-2.4)
            + T(4 + tw + 18, 88, idx, "fmb", 16, HEAD, ls=1)
            + T(W - 4, 86, note.upper(), "fm", 13, GRAY, "end", 2)
            + f'<rect x="4" y="112" width="{W-8}" height="1.5" fill="{GRAY}" fill-opacity=".45"/>'
            + f'<rect class="bar" x="4" y="110.5" width="{tw:.0f}" height="4.5" fill="{HEAD}"/>')
    css = ".bar{transform-box:fill-box;transform-origin:left;animation:bar 1.4s cubic-bezier(.65,0,.25,1) both}@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    write(name, doc(W, H, body, css, title))


# ================================================================ "also built" rows
def row(name, idx, title, desc, stack, icon, css=""):
    t = THEMES["paper"]
    W, H = 1600, 124
    body = (f'<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="22" fill="{t["bg"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
            + T(44, 72, idx, "fmb", 14, t["acc"], ls=1)
            + T(104, 78, title, "fx", 40, t["fg"], ls=-1.5)
            + T(470, 76, desc, "fb", fit(desc, "fb", 21, 600), t["mut"])
            + T(1110, 74, stack.upper(), "fm", 12, t["mut"], ls=1.2)
            + f'<g transform="translate(1418,62)">{icon(t)}</g>'
            + open_icon(W - 62, 62, t))
    write(name, doc(W, H, body, css + NUDGE, f"{title}: {desc}"))


def rows():
    def ic_devhub(t):
        g = ""
        for i, (a, b) in enumerate([(26, 18), (14, 34), (36, 24)]):
            x = -36 + i * 26
            g += f'<rect class="g" x="{x}" y="{18-a}" width="10" height="{a}" fill="{t["fg"]}" style="animation-delay:-{i*.3:.1f}s"/>'
            g += f'<rect class="g" x="{x+11}" y="{18-b}" width="10" height="{b}" fill="{t["acc"]}" style="animation-delay:-{i*.3+.5:.1f}s"/>'
        return g
    row("row-devhub.svg", "10", "DevHub", "GitHub discovery: search, compare and save devs and repos.", "Next.js / Prisma / Postgres", ic_devhub,
        ".g{transform-box:fill-box;transform-origin:bottom;animation:gr 2s ease-in-out infinite alternate}@keyframes gr{from{transform:scaleY(.4)}to{transform:scaleY(1)}}")

    def ic_bartr(t):
        return (f'<g class="spin sw"><path d="M-22,-8 A24,24 0 0 1 22,-8" fill="none" stroke="{t["fg"]}" stroke-width="5"/><path d="M14,-18 L23,-6 L9,-3" fill="none" stroke="{t["fg"]}" stroke-width="5"/>'
                f'<path d="M22,8 A24,24 0 0 1 -22,8" fill="none" stroke="{t["acc"]}" stroke-width="5"/><path d="M-14,18 L-23,6 L-9,3" fill="none" stroke="{t["acc"]}" stroke-width="5"/></g>')
    row("row-bartr.svg", "11", "bartr", "Shopify for campus barter: sell, swap or give away.", "Next.js 15 / React 19", ic_bartr,
        ".sw{animation:spin 6s linear infinite}")

    def ic_zero(t):
        g, y = "", 0
        for i, d in enumerate([-10, 14, -8, -16, 12]):
            o, c = y, y + d
            x = -34 + i * 15
            up = c < o
            g += f'<line x1="{x+4}" y1="{min(o,c)-8}" x2="{x+4}" y2="{max(o,c)+7}" stroke="{t["fg"]}" stroke-width="1.5"/>'
            fill = f'fill="{t["bg"]}" stroke="{t["fg"]}" stroke-width="1.5"' if up else f'fill="{t["acc"]}"'
            g += f'<rect class="cd" x="{x}" y="{min(o,c)}" width="8" height="{abs(c-o)}" {fill} style="animation-delay:{i*.2:.1f}s"/>'
            y = c
        return f'<g transform="translate(0,6)">{g}</g>'
    row("row-zerobot.svg", "12", "ZeroBot", "Intraday trading bot for Zerodha with risk rules.", "Python / KiteConnect", ic_zero,
        ".cd{animation:pulse 2.2s ease-in-out infinite}")

    def ic_web3(t):
        g = "".join(f'<circle class="ring" cx="0" cy="0" r="12" fill="none" stroke="{t["fg"]}" stroke-width="1.5" style="animation-delay:-{k}s"/>' for k in range(3))
        return g + f'<path d="M0,-14 L11,0 L0,14 L-11,0 Z" fill="{t["acc"]}"/>'
    row("row-web3beacon.svg", "13", "Web3Beacon", "A friendly Web3 guide whose wallet demo never signs.", "HTML / CSS / EIP-6963", ic_web3,
        ".ring{transform-box:fill-box;transform-origin:center;animation:ring 3s ease-out infinite}@keyframes ring{from{transform:scale(.6);opacity:1}to{transform:scale(3);opacity:0}}")


# ================================================================ track record (metro line)
def timeline():
    t = THEMES["paper"]
    W, H = 1600, 430
    path = "M80,170 H560 L690,300 H1520"
    stations = [(200, 170, "2025", "Smart India Hackathon", "Dueproof / Kochi Metro", False, True),
                (440, 170, "2026", "Smart India Hackathon", "AeroPulse / MoSPI", False, True),
                (820, 300, "2026", "ML Empowerment 3.0", "Hum / first place", True, False),
                (1050, 300, "2026", "ForgeHacks", "Countersign / AI x security", False, True),
                (1260, 300, "2026", "Graph Hacks", "Deadlock / FalkorDB", False, False),
                (1450, 300, "2026", "Build, Ship, Shape", "Cadabra / Fire TV", False, True)]
    st = ""
    for i, (x, y, yr, nm, pj, win, up) in enumerate(stations):
        if win:
            st += (f'<circle cx="{x}" cy="{y}" r="32" fill="{COBALT}" fill-opacity=".14" style="animation:pulse 1.8s infinite"/>'
                   f'<circle cx="{x}" cy="{y}" r="21" fill="{COBALT}"/><circle cx="{x}" cy="{y}" r="8" fill="{PAPER}"/>')
        else:
            st += f'<circle cx="{x}" cy="{y}" r="13" fill="{PAPER}" stroke="{INK}" stroke-width="5"/>'
        ty = y - 84 if up else y + 58
        tag = f"{yr}  WINNER" if win else yr
        tagw = measure(tag, "fmb", 12, 1.5) + 18
        st += (f'<g class="fade" style="animation-delay:{0.4+0.15*i:.2f}s">'
               + (f'<rect x="{x-tagw/2:.0f}" y="{ty-17}" width="{tagw:.0f}" height="24" rx="12" fill="{COBALT}"/>' if win else "")
               + T(x, ty, tag, "fmb", 12, PAPER if win else GRAY, "middle", 1.5)
               + T(x, ty + 30, nm, "fh", fit(nm, "fh", 23, 215), INK, "middle", -.4)
               + T(x, ty + 54, pj, "fs", 19, GRAY, "middle") + "</g>")
    body = f"""<defs>{dot_grid("dg", 24, t["grid"])}<clipPath id="clip"><rect width="{W}" height="{H}" rx="30"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{PAPER}"/><rect width="{W}" height="{H}" fill="url(#dg)"/></g>
<rect x=".75" y=".75" width="{W-1.5}" height="{H-1.5}" rx="29.5" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>
<rect x="44" y="40" width="80" height="30" rx="15" fill="{INK}"/>{T(84, 60, "LINE H", "fmb", 12, PAPER, "middle", 1.5)}
{T(140, 60, "THE HACKATHON LINE  /  6 STOPS SO FAR", "fm", 12, GRAY, ls=1.5)}
<g transform="translate(1300,46)"><rect width="38" height="14" rx="7" fill="{COBALT}"/>{T(50, 13, "next stop: yours", "fs", 21, INK)}</g>
<path d="{path}" fill="none" stroke="{INK}" stroke-width="16" stroke-linejoin="round" stroke-linecap="round" pathLength="1" class="plot"/>
<path id="metro" d="{path}" fill="none"/>
<g><animateMotion dur="10s" repeatCount="indefinite" rotate="auto"><mpath href="#metro"/></animateMotion><rect x="-24" y="-7" width="48" height="14" rx="7" fill="{COBALT}"/></g>
{st}"""
    write("timeline.svg", doc(W, H, body, "", "The hackathon line: Smart India Hackathon 2025 (Dueproof, then called Traceline), Smart India Hackathon 2026 (AeroPulse), ML Empowerment 3.0 (Hum, first place), ForgeHacks (Countersign), Graph Hacks (Deadlock), Amazon Build, Ship, Shape (Cadabra)."))


# ================================================================ tools x projects matrix
def matrix():
    projects = ["Aftershock", "PyWeb", "Hum", "Cadabra", "Deadlock", "Countersign", "couchpad", "AeroPulse", "Dueproof"]
    uses = [
        ("Python", {"PyWeb", "Hum", "AeroPulse", "Dueproof"}),
        ("TypeScript", {"Aftershock", "Cadabra", "Deadlock", "Countersign", "couchpad"}),
        ("Next.js / React", {"Aftershock", "AeroPulse"}),
        ("FastAPI", {"AeroPulse"}),
        ("PostgreSQL / Redis", {"PyWeb"}),
        ("FalkorDB / Cypher", {"Deadlock"}),
        ("PyTorch / ONNX", {"Hum"}),
        ("OCR / IndicTrans2", {"Dueproof"}),
        ("LLM APIs", {"Aftershock", "Cadabra", "Deadlock", "Countersign"}),
        ("WebRTC", {"Cadabra", "couchpad"}),
        ("Docker / Vercel", {"Aftershock", "Deadlock", "Countersign", "AeroPulse"}),
    ]
    W = 1600
    x0, cw = 420, 112
    y0, rh = 190, 50
    H = y0 + len(uses) * rh + 50
    body = f'<rect width="{W}" height="{H}" rx="30" fill="{INK}"/>'
    lead = "What I reach for,"
    body += T(52, 84, lead, "fx", 46, PAPER, ls=-1.8)
    body += T(52 + measure(lead, "fx", 46, -1.8) + 14, 84, "and where it shipped.", "fs", 50, DIM)
    body += T(W - 52, 80, f"{len(uses)} TOOLS  x  {len(projects)} PROJECTS", "fm", 12, DIM, "end", 2)
    for j, p in enumerate(projects):
        cx = x0 + j * cw + cw / 2
        body += T(cx, 160, p.upper(), "fm", fit(p.upper(), "fm", 11, cw - 8, .5), DIM, "middle", .5)
    body += f'<line x1="52" y1="174" x2="{W-52}" y2="174" stroke="#2C2C2C"/>'
    for i, (tool, used) in enumerate(uses):
        y = y0 + i * rh + 24
        body += T(52, y + 7, tool, "fh", 22, PAPER, ls=-.3)
        body += T(W - 52, y + 6, f"{len(used)}", "fmb", 14, HEAD, "end")
        for j, p in enumerate(projects):
            cx = x0 + j * cw + cw / 2
            if p in used:
                body += f'<circle class="pop" cx="{cx}" cy="{y}" r="10" fill="{HEAD}" style="animation-delay:{0.3+0.04*(i+j):.2f}s"/>'
            else:
                body += f'<circle cx="{cx}" cy="{y}" r="2.5" fill="#3A3A3A"/>'
        body += f'<line x1="52" y1="{y+25}" x2="{W-52}" y2="{y+25}" stroke="#1E1E1E"/>'
    write("toolkit.svg", doc(W, H, body, "", "Tools by project: Python, TypeScript, Next.js and React, FastAPI, PostgreSQL and Redis, FalkorDB, PyTorch and ONNX, LLM APIs, WebRTC, Docker and Vercel."))


# ================================================================ closing CTA
def cta():
    W, H = 1600, 560
    email = "maanavkrishna@gmail.com"
    status = "OPEN TO INTERNSHIPS  /  SWE, ML, QUANT"
    body = f"""<defs><clipPath id="clip"><rect width="{W}" height="{H}" rx="30"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{INK}"/>
{T(56, 76, "CONTACT", "fmb", 14, HEAD, ls=2)}
{T(52, 226, "Let's build something", "fs", 128, PAPER, ls=-2)}
{T(52, 350, "hard and honest.", "fs", 128, HEAD, ls=-2)}
<line x1="56" y1="420" x2="{W-56}" y2="420" stroke="#2C2C2C"/>
{T(56, 488, email, "fh", 38, PAPER, ls=-.8)}
<rect class="ul" x="56" y="502" width="{measure(email, "fh", 38, -.8):.0f}" height="3" fill="{HEAD}"/>
<g transform="translate({W-56},478)"><circle cx="{-measure(status, "fmb", 14, 1.5) - 22:.0f}" cy="-5" r="6" fill="{HEAD}" style="animation:pulse 1.4s infinite"/>
{T(0, 0, status, "fmb", 14, PAPER, "end", 1.5)}</g>
{T(W-56, 508, "Chennai, India", "fs", 22, DIM, "end")}
</g>"""
    css = ".ul{transform-box:fill-box;transform-origin:left;animation:ul 1.6s cubic-bezier(.65,0,.25,1) .6s both}@keyframes ul{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    write("cta.svg", doc(W, H, body, css, "Let's build something hard and honest. maanavkrishna@gmail.com. Open to internships in SWE, ML and quant."))


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    hero()
    tile("tile-aftershock.svg", "wide", "ink", "01", "Dev tools / GitHub App", "Aftershock",
         ("Every production incident becomes a regression test.", "Git history proves it fails before the fix and passes on it."),
         ["Next.js", "TypeScript", "LLMs", "Sandboxes"], art_aftershock, AFTERSHOCK_CSS)
    tile("tile-pyweb.svg", "narrow", "cobalt", "02", "Framework / on PyPI", "PyWeb",
         ("Full-stack web apps in one Python file.", "No JavaScript toolchain."),
         ["Python", "Compiler", "SSR", "Typed RPC"], art_pyweb)
    tile("tile-hum.svg", "narrow", "paper", "03", "Assistive ML / 1st place", "Hum",
         ("An interpreter for people who speak", "in sounds instead of words."),
         ["ONNX", "CNN", "Conformal", "Offline"], art_hum, HUM_CSS)
    tile("tile-cadabra.svg", "wide", "paper", "04", "Fire TV / generative games", "Cadabra",
         ("The room throws in ideas and votes on AI pitches.", "A playable physics game is running seconds later."),
         ["TypeScript", "Bedrock", "WebRTC", "Physics"], art_cadabra, CADABRA_CSS)
    tile("tile-deadlock.svg", "narrow", "paper", "05", "Graph AI / Graph Hacks", "Deadlock",
         ("Finds hidden trade loops in a network.", "AI representatives negotiate the terms."),
         ["FalkorDB", "Cypher", "Claude"], art_deadlock, DEADLOCK_CSS)
    tile("tile-countersign.svg", "narrow", "ink", "06", "AI x security / ForgeHacks", "Countersign",
         ("AI can fake a voice. It can't fake", "the rolling secret your family shares."),
         ["TypeScript", "AI agents", "PWA"], art_countersign, COUNTERSIGN_CSS)
    tile("tile-couchpad.svg", "narrow", "cobalt", "07", "Open source / MIT", "couchpad",
         ("Every phone in the room becomes", "a game controller. No app install."),
         ["TypeScript", "WebRTC", "WebSocket"], art_couchpad, COUCHPAD_CSS)
    sih_banner()
    sih_half("tile-aeropulse.svg", "08", "SIH 2026 / SIH26056 / MoSPI", "AeroPulse",
             ("Is your flight fare high today? An open index", "of Indian domestic airfares, 40 routes, daily."),
             ["Python", "FastAPI", "Next.js"], art_aeropulse)
    sih_half("tile-dueproof.svg", "09", "SIH 2025 / SIH25080 / was Traceline", "Dueproof",
             ("Every due date in your notices, with proof", "from the page. 22 Indian languages, self-hosted."),
             ["Python", "OCR", "IndicTrans2"], art_dueproof, DUEPROOF_CSS)
    rows()
    timeline()
    matrix()
    cta()
    for f, i, t, n in [("h-work.svg", "01", "Selected work", "9 projects, all shipped"),
                       ("h-more.svg", "02", "Also built", "smaller, still real"),
                       ("h-trail.svg", "03", "Track record", "6 hackathons, 1 win"),
                       ("h-tools.svg", "04", "Toolkit", "tools by project"),
                       ("h-activity.svg", "05", "Activity", "live from github")]:
        header(f, i, t, n)
    print("\n".join(sorted(f"{os.path.getsize(os.path.join(OUT, f))//1024:>4} KB  {f}" for f in os.listdir(OUT))))


if __name__ == "__main__":
    main()
