#!/usr/bin/env python3
"""Build the SVG graphics used by the profile README.

    pip install fonttools brotli
    python3 scripts/build_assets.py

Every SVG paints its own background (so it works in GitHub light and dark mode)
and embeds a subset of the fonts in scripts/fonts, so the type renders the same
everywhere. Palette and type follow the portfolio: ink, bone, one signal orange.
"""
import base64
import io
import math
import os
from collections import defaultdict
from xml.dom import minidom
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")

# ---------------------------------------------------------------- tokens
INK = "#0E0E0C"
INK2 = "#191916"
INK3 = "#2C2B26"
BONE = "#EDE7DB"
BONE2 = "#E3DCCD"
BONE3 = "#CCC2AE"
GRAPHITE = "#6E695F"
ASH = "#A59E90"
SIGNAL = "#FF5B14"

FONTS = {  # css class -> (file, family, weight, style, fallback)
    "fd": ("bricolage-grotesque-latin-800-normal.woff2", "MK Display", 800, "normal", "'Arial Black', Arial, sans-serif"),
    "fh": ("bricolage-grotesque-latin-700-normal.woff2", "MK Display Bold", 700, "normal", "Arial, sans-serif"),
    "fb": ("instrument-sans-latin-400-normal.woff2", "MK Sans", 400, "normal", "Helvetica, Arial, sans-serif"),
    "fbb": ("instrument-sans-latin-700-normal.woff2", "MK Sans Bold", 700, "normal", "Helvetica, Arial, sans-serif"),
    "fs": ("instrument-serif-latin-400-italic.woff2", "MK Serif", 400, "italic", "Georgia, serif"),
    "fm": ("martian-mono-latin-400-normal.woff2", "MK Mono", 400, "normal", "ui-monospace, Menlo, Consolas, monospace"),
    "fmb": ("martian-mono-latin-700-normal.woff2", "MK Mono Bold", 700, "normal", "ui-monospace, Menlo, Consolas, monospace"),
}

BASE_CSS = """
.plot{stroke-dasharray:1;stroke-dashoffset:1;animation:plot 2.4s cubic-bezier(.65,0,.25,1) forwards}
@keyframes plot{to{stroke-dashoffset:0}}
.fade{opacity:0;animation:fade .9s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:.25}50%{opacity:1}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}
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


def T(x, y, s, cls, size, fill, anchor=None, ls=None, extra=""):
    a = f' text-anchor="{anchor}"' if anchor else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" fill="{fill}"{a}{l} {extra}>{escape(s)}</text>'


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
def crop(x, y, s=10, col=INK):
    return (f'<path d="M{x-s},{y}H{x+s}M{x},{y-s}V{y+s}" stroke="{col}" stroke-width="1"/>')


def arrow(x1, y, x2, col=INK, w=2):
    d = 1 if x2 > x1 else -1
    return (f'<path d="M{x1},{y}H{x2}M{x2-9*d},{y-6}L{x2},{y}L{x2-9*d},{y+6}" fill="none" stroke="{col}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def check(cx, cy, col, s=1.0):
    return (f'<path d="M{cx-8*s},{cy} l{6*s},{6*s} l{11*s},{-12*s}" fill="none" stroke="{col}" stroke-width="3" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def cross(cx, cy, col, s=7):
    return (f'<path d="M{cx-s},{cy-s}L{cx+s},{cy+s}M{cx+s},{cy-s}L{cx-s},{cy+s}" stroke="{col}" stroke-width="3" '
            f'stroke-linecap="round"/>')


def phone(x, y, w, h, extra=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(w, h)*0.16:.0f}" fill="{BONE}" stroke="{INK}" '
            f'stroke-width="2.5" pathLength="1" class="plot" {extra}/>')


def grid_pattern(pid, step, col, op):
    return (f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<path d="M{step} 0H0V{step}" fill="none" stroke="{col}" stroke-opacity="{op}"/></pattern>')


def seal(cx, cy, r, ring_text, center, sub):
    path = f"M{cx-r},{cy} a{r},{r} 0 1,1 {2*r},0 a{r},{r} 0 1,1 {-2*r},0"
    circ = 2 * math.pi * r
    size = fit(ring_text, "fmb", 13, circ * 0.98, 1)
    return f"""<g>
<circle cx="{cx}" cy="{cy}" r="{r+22}" fill="{SIGNAL}"/>
<circle cx="{cx}" cy="{cy}" r="{r-13}" fill="none" stroke="{BONE}" stroke-width="1.5"/>
<g class="sealspin" style="transform-origin:{cx}px {cy}px"><path id="sealp" d="{path}" fill="none"/>
<text class="fmb" font-size="{size}" fill="{BONE}" letter-spacing="1"><textPath href="#sealp">{escape(ring_text)}</textPath></text></g>
{T(cx, cy+12, center, "fd", 44, BONE, "middle", -1)}
{T(cx, cy+32, sub, "fmb", 9, BONE, "middle", 1.5)}
</g>"""


SEAL_CSS = ".sealspin{animation:spin 24s linear infinite}"


# ---------------------------------------------------------------- project cards
def card(name, fig, kind, title, tagline, tags, art, css="", W=840, H=560):
    tags_svg, x = "", 36
    for t in tags:
        t = t.upper()
        tags_svg += f'<rect x="{x}" y="502" width="8" height="8" fill="{SIGNAL}"/>' + T(x + 16, 511, t, "fm", 12, INK, ls=1)
        x += 16 + measure(t, "fm", 12, 1) + 24
    body = f"""
<defs>{grid_pattern("g", 24, BONE3, .6)}<clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="{BONE}"/>
<rect x="36" y="72" width="{W-72}" height="272" fill="url(#g)"/>
{crop(36, 72)}{crop(W-36, 72)}{crop(36, 344)}{crop(W-36, 344)}
{T(36, 46, "FIG. " + fig, "fmb", 13, INK, ls=1.5)}
{T(W-36, 46, kind.upper(), "fm", 12, GRAPHITE, "end", 1.5)}
<line x1="36" y1="58" x2="{W-36}" y2="58" stroke="{INK}" stroke-width="1.5"/>
<g>{art}</g>
<line x1="36" y1="358" x2="{W-36}" y2="358" stroke="{INK}" stroke-width="1.5"/>
{T(33, 424, title, "fd", fit(title, "fd", 60, W-72, -1.5), INK, ls=-1.5)}
{T(36, 462, tagline, "fb", fit(tagline, "fb", 22, W-72), GRAPHITE)}
{tags_svg}
<g transform="translate({W-36},507)"><circle r="17" fill="{INK}"/><path d="M-5,5 L5,-5 M-3,-5 H5 V3" fill="none" stroke="{BONE}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="nudge"/></g>
</g>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{INK}" stroke-width="2"/>"""
    css += ".nudge{animation:nudge 2.4s ease-in-out infinite}@keyframes nudge{0%,70%,100%{transform:none}80%{transform:translate(2px,-2px)}}"
    write(name, doc(W, H, body, css, f"{title}: {tagline}"))


def aftershock():
    pts = []
    for i in range(121):
        x = 60 + i * 6
        q = math.exp(-((x - 410) / 48) ** 2)
        y = 165 + math.sin(i * 1.9) * (4 + 62 * q) + math.sin(i * 0.5) * 2.5
        pts.append(f"{x},{y:.1f}")
    seis = "M" + " L".join(pts)
    runs = ""
    for i in range(3):
        x = 196 + i * 44
        runs += (f'<g class="run" style="animation-delay:{0.25*i:.2f}s"><rect x="{x}" y="246" width="32" height="32" '
                 f'fill="{SIGNAL}" fill-opacity=".14" stroke="{SIGNAL}" stroke-width="2"/>{cross(x+16, 262, SIGNAL, 6)}</g>')
    for i in range(3):
        x = 604 + i * 44
        runs += (f'<g class="run" style="animation-delay:{1.4+0.25*i:.2f}s"><rect x="{x}" y="246" width="32" height="32" '
                 f'fill="{INK}"/>{check(x+16, 263, BONE, .9)}</g>')
    art = f"""
{T(60, 98, "SEISMOGRAPH / PROD / CHECKOUT-API", "fm", 11, GRAPHITE, ls=1)}
<line x1="60" y1="165" x2="780" y2="165" stroke="{GRAPHITE}" stroke-dasharray="2 5"/>
<path d="{seis}" pathLength="1" class="seis" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/>
<g class="mark"><line x1="410" y1="108" x2="410" y2="222" stroke="{SIGNAL}" stroke-width="2"/>
<rect x="352" y="88" width="116" height="22" fill="{SIGNAL}"/>{T(410, 104, "INC-12", "fmb", 12, BONE, "middle", 1.5)}</g>
{T(60, 258, "a3f9c1^", "fmb", 13, INK)}{T(60, 280, "before the fix", "fs", 19, GRAPHITE)}
{runs}
{T(440, 248, "time travel", "fs", 19, GRAPHITE, "middle")}{arrow(358, 262, 524, INK)}
{T(540, 258, "a3f9c1", "fmb", 13, INK)}{T(540, 280, "the fix", "fs", 19, GRAPHITE)}
<line x1="60" y1="316" x2="780" y2="316" stroke="{INK}" stroke-opacity=".15"/>
{T(60, 334, "tests/aftershock/test_inc_12.py  /  admitted: fails before, passes on", "fm", 10, GRAPHITE, ls=.5)}
"""
    css = """.seis{stroke-dasharray:1;stroke-dashoffset:1;animation:seis 7s cubic-bezier(.6,0,.3,1) infinite}
@keyframes seis{0%{stroke-dashoffset:1}40%,92%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}
.mark{opacity:0;animation:mark 7s infinite}@keyframes mark{0%,22%{opacity:0}26%,92%{opacity:1}100%{opacity:0}}
.run{opacity:0;animation:run 7s infinite}@keyframes run{0%,42%{opacity:0;transform:translateY(6px)}48%,92%{opacity:1;transform:none}100%{opacity:0}}"""
    card("card-aftershock.svg", "01", "Dev tools / GitHub App", "Aftershock",
         "Every production incident becomes a regression test. Git history proves it.",
         ["Next.js", "TypeScript", "LLMs", "Sandboxes"], art, css)


def pyweb():
    code = [("from pyweb import App, server", INK), ("@server", SIGNAL), ("def sign(name: str) -> list:", INK),
            ("    ENTRIES.append(name)", GRAPHITE), ("def submit():", INK), ("    entries = sign(name)", GRAPHITE),
            ("<button>Sign</button>", GRAPHITE)]
    ys = [148, 176, 198, 220, 252, 274, 302]
    lines = "".join(f'<g class="fade" style="animation-delay:{0.12*i:.2f}s">' + T(80, y, c, "fm", 12.5, col) + "</g>"
                    for i, ((c, col), y) in enumerate(zip(code, ys)))
    art = f"""
<rect x="60" y="88" width="372" height="236" fill="{BONE}" stroke="{INK}" stroke-width="2" pathLength="1" class="plot"/>
<line x1="60" y1="118" x2="432" y2="118" stroke="{INK}"/>
{T(80, 108, "APP.PYWEB", "fmb", 11, INK, ls=1.5)}{T(414, 108, "ONE FILE", "fm", 10, GRAPHITE, "end", 1)}
{lines}
<path id="ps" d="M432,190 H488 V136 H548" fill="none" stroke="{INK}" stroke-width="1.5" stroke-dasharray="4 4"/>
<path id="pb" d="M432,264 H488 V264 H548" fill="none" stroke="{INK}" stroke-width="1.5" stroke-dasharray="4 4"/>
<rect x="-6" y="-6" width="12" height="12" fill="{SIGNAL}"><animateMotion dur="2.2s" repeatCount="indefinite"><mpath href="#ps"/></animateMotion></rect>
<rect x="-6" y="-6" width="12" height="12" fill="{SIGNAL}"><animateMotion dur="2.2s" begin="1.1s" repeatCount="indefinite"><mpath href="#pb"/></animateMotion></rect>
{T(488, 210, "compile", "fs", 17, GRAPHITE, "middle")}
<rect x="548" y="92" width="236" height="96" fill="{BONE}" stroke="{INK}" stroke-width="2"/>
<rect x="548" y="92" width="236" height="26" fill="{INK}"/>{T(562, 110, "OUT/01  SERVER", "fmb", 11, BONE, ls=1.5)}
{T(562, 148, "sign() becomes typed RPC", "fbb", 17, INK)}{T(562, 174, "validated, SSR, live queries", "fs", 17, GRAPHITE)}
<rect x="548" y="220" width="236" height="96" fill="{BONE}" stroke="{INK}" stroke-width="2"/>
<rect x="548" y="220" width="236" height="26" fill="{SIGNAL}"/>{T(562, 238, "OUT/02  BROWSER", "fmb", 11, BONE, ls=1.5)}
{T(562, 276, "submit() becomes 312 B JS", "fbb", 17, INK)}{T(562, 302, "reactive, no JS toolchain", "fs", 17, GRAPHITE)}
"""
    card("card-pyweb.svg", "02", "Web framework / on PyPI", "PyWeb",
         "Full-stack web apps in one Python file. The compiler splits browser from server.",
         ["Python", "Compiler", "SSR", "Typed RPC"], art)


def hum():
    bars = ""
    for i in range(36):
        x = 62 + i * 11.5
        h = 22 + 92 * abs(math.sin(i * 0.41)) * (0.55 + 0.45 * math.sin(i * 0.19 + 1))
        bars += (f'<rect class="eq" x="{x:.1f}" y="{168-h/2:.0f}" width="6" height="{h:.0f}" fill="{INK}" '
                 f'style="animation-delay:-{(i*0.11)%1.3:.2f}s"/>')
    chips = ""
    x = 62
    for label, p, style in [("I want that", "72%", "solid"), ("too loud", "21%", "line"), ("maybe", "", "dash")]:
        txt = label + ("   " + p if p else "")
        w = measure(txt, "fbb", 16) + 30
        if style == "solid":
            chips += f'<rect x="{x}" y="276" width="{w:.0f}" height="36" fill="{INK}"/>' + T(x + 15, 299, txt, "fbb", 16, BONE)
        elif style == "line":
            chips += f'<rect x="{x}" y="276" width="{w:.0f}" height="36" fill="none" stroke="{INK}" stroke-width="2"/>' + T(x + 15, 299, txt, "fbb", 16, INK)
        else:
            chips += f'<rect x="{x}" y="276" width="{w:.0f}" height="36" fill="none" stroke="{GRAPHITE}" stroke-width="1.5" stroke-dasharray="4 4"/>' + T(x + 15, 299, txt, "fbb", 16, GRAPHITE)
        x += w + 12
    art = f"""
{T(62, 98, "LISTENING / ON-DEVICE / AUDIO NEVER LEAVES", "fm", 11, GRAPHITE, ls=1)}
{bars}
<g class="head"><line x1="56" y1="108" x2="56" y2="228" stroke="{SIGNAL}" stroke-width="2.5"/><rect x="50" y="102" width="12" height="12" fill="{SIGNAL}"/></g>
{T(62, 262, "CONFORMAL SET  /  says maybe instead of bluffing", "fm", 11, GRAPHITE, ls=.5)}
{chips}
{seal(690, 176, 60, "FIRST PLACE  /  ML EMPOWERMENT BUILD CHALLENGE 3.0  /  ", "1st", "PLACE")}
"""
    css = """.eq{transform-box:fill-box;transform-origin:center;animation:eq 1.3s ease-in-out infinite alternate}
@keyframes eq{from{transform:scaleY(.18)}to{transform:scaleY(1)}}
.head{animation:head 4.5s linear infinite}@keyframes head{from{transform:translateX(0)}to{transform:translateX(414px)}}""" + SEAL_CSS
    card("card-hum.svg", "03", "Assistive ML / in the browser", "Hum",
         "A personal interpreter for people who communicate with sounds instead of words.",
         ["ONNX", "CNN", "Conformal", "Offline-first"], art, css)


def cadabra():
    balls = ""
    for x, r, col, d in [(330, 15, INK, 0), (408, 12, SIGNAL, -.4), (482, 17, INK, -.8)]:
        balls += f'<circle class="ball" cx="{x}" cy="{276-r}" r="{r}" fill="{col}" style="animation-delay:{d}s"/>'
    ideas = ""
    for t, x, d in [("laser sharks", 130, 0), ("zero gravity", 712, -1.4), ("disco floor", 130, -2.8)]:
        ideas += f'<g class="idea" style="animation-delay:{d}s">' + T(x, 236, t, "fs", 22, INK, "middle") + "</g>"
    art = f"""
{T(60, 98, "IDEA STORM", "fm", 11, GRAPHITE, ls=1)}
<rect x="250" y="96" width="340" height="200" fill="{BONE}" stroke="{INK}" stroke-width="2.5" pathLength="1" class="plot"/>
<path d="M400,296 V312 H440 V296 M372,318 H468" fill="none" stroke="{INK}" stroke-width="2.5"/>
{T(266, 118, "RING OUT", "fmb", 11, INK, ls=1.5)}{T(574, 118, "GRAVITY x0.4", "fm", 10, SIGNAL, "end", 1)}
<line x1="268" y1="276" x2="572" y2="276" stroke="{INK}" stroke-width="2"/>
<rect class="crate" x="530" y="248" width="26" height="26" fill="none" stroke="{INK}" stroke-width="2.5"/>
{balls}
{phone(102, 252, 56, 84)}{phone(684, 252, 56, 84)}
<circle cx="130" cy="294" r="13" fill="none" stroke="{INK}" stroke-width="1.5"/><circle class="stick" cx="130" cy="294" r="5" fill="{SIGNAL}"/>
<circle cx="712" cy="294" r="13" fill="none" stroke="{INK}" stroke-width="1.5"/><circle class="stick" cx="712" cy="294" r="5" fill="{SIGNAL}" style="animation-delay:-.6s"/>
{ideas}
"""
    css = """.ball{animation:bounce .85s cubic-bezier(.45,0,.55,1) infinite alternate}
@keyframes bounce{from{transform:translateY(0)}to{transform:translateY(-110px)}}
.crate{transform-box:fill-box;transform-origin:center;animation:spin 3.2s linear infinite}
.idea{opacity:0;animation:rise 4.2s ease-in infinite}
@keyframes rise{0%{opacity:0;transform:translateY(18px)}15%,55%{opacity:1}100%{opacity:0;transform:translateY(-120px)}}
.stick{animation:wig 1.3s ease-in-out infinite alternate}@keyframes wig{from{transform:translate(-5px,3px)}to{transform:translate(5px,-4px)}}"""
    card("card-cadabra.svg", "04", "Fire TV / generative games", "Cadabra",
         "The room throws in ideas, AI pitches three games, a physics game is built in seconds.",
         ["TypeScript", "Bedrock", "WebRTC", "Physics"], art, css)


def deadlock():
    A, B, C = (190, 262), (420, 128), (650, 262)
    loop = (f"M{A[0]},{A[1]} Q{250},{150} {B[0]},{B[1]} Q{590},{150} {C[0]},{C[1]} Q{420},{352} {A[0]},{A[1]}")
    faint = [(78, 132), (770, 128), (96, 320), (748, 318)]
    fe = "".join(f'<line x1="{x}" y1="{y}" x2="{A[0] if x < 420 else C[0]}" y2="{A[1] if x < 420 else C[1]}" stroke="{GRAPHITE}" stroke-dasharray="2 5"/>'
                 f'<circle cx="{x}" cy="{y}" r="7" fill="{BONE}" stroke="{GRAPHITE}" stroke-width="1.5"/>' for x, y in faint)

    def node(p, label, key=False):
        ring = (f'<circle class="kring" cx="{p[0]}" cy="{p[1]}" r="36" fill="none" stroke="{SIGNAL}" stroke-width="2" '
                f'stroke-dasharray="6 6" style="transform-origin:{p[0]}px {p[1]}px"/>') if key else ""
        ly = p[1] + 52 if p[1] > 200 else p[1] - 34
        return (f'{ring}<circle cx="{p[0]}" cy="{p[1]}" r="22" fill="{BONE}" stroke="{INK}" stroke-width="2.5"/>'
                f'<circle cx="{p[0]}" cy="{p[1]}" r="7" fill="{INK}"/>' + T(p[0], ly, label, "fbb", 16, INK, "middle"))
    art = f"""
{T(60, 98, "3 CAN TRADE WHERE 2 CAN'T", "fm", 11, GRAPHITE, ls=.5)}
{fe}
<path id="loop" d="{loop}" pathLength="1" class="plot" fill="none" stroke="{SIGNAL}" stroke-width="3"/>
<circle r="6" fill="{INK}"><animateMotion dur="4.5s" repeatCount="indefinite"><mpath href="#loop"/></animateMotion></circle>
<circle r="6" fill="{INK}"><animateMotion dur="4.5s" begin="-1.5s" repeatCount="indefinite"><mpath href="#loop"/></animateMotion></circle>
<circle r="6" fill="{INK}"><animateMotion dur="4.5s" begin="-3s" repeatCount="indefinite"><mpath href="#loop"/></animateMotion></circle>
{node(A, "Studio North", True)}{node(B, "Motionhaus")}{node(C, "Wordcraft")}
{T(272, 180, "video", "fs", 18, GRAPHITE, "middle")}{T(568, 180, "copy", "fs", 18, GRAPHITE, "middle")}{T(420, 296, "design", "fs", 18, GRAPHITE, "middle")}
{T(190, 214, "KEYSTONE", "fmb", 10, SIGNAL, "middle", 1.5)}
"""
    css = ".kring{animation:spin 10s linear infinite}"
    card("card-deadlock.svg", "05", "Graph AI / FalkorDB", "Deadlock",
         "Finds the hidden trade loops in a network. AI representatives negotiate the terms.",
         ["TypeScript", "FalkorDB", "Cypher", "Claude agents"], art, css)


def countersign():
    sets = [("velvet", "harbor", "comet"), ("maple", "orbit", "lantern"), ("cobalt", "river", "ember")]

    def ph(x):
        g = phone(x, 86, 150, 240)
        g += f'<rect x="{x+55}" y="98" width="40" height="5" fill="{INK}"/>'
        g += T(x + 75, 132, "COUNTERSIGN", "fmb", 9, GRAPHITE, "middle", 1.5)
        for k, ws in enumerate(sets):
            g += f'<g class="w" style="animation-delay:-{(3*(3-k)) % 9}s">'
            for j, w in enumerate(ws):
                g += T(x + 75, 182 + j * 36, w, "fd", 27, INK, "middle", -.5)
            g += "</g>"
        g += f'<rect x="{x+22}" y="292" width="106" height="5" fill="{BONE3}"/><rect class="tick" x="{x+22}" y="292" width="106" height="5" fill="{SIGNAL}"/>'
        return g
    wave = "M" + " L".join(f"{330+i*6},{238+math.sin(i*0.9)*(16*math.sin(i*0.12)+4):.1f}" for i in range(31))
    art = f"""
{ph(70)}{ph(620)}
<line x1="220" y1="150" x2="620" y2="150" stroke="{INK}" stroke-dasharray="3 5"/>
{T(420, 140, "same words, every minute, offline", "fs", 19, GRAPHITE, "middle")}
<path d="M420,168 L452,180 V210 C452,232 438,246 420,254 C402,246 388,232 388,210 V180 Z" fill="{INK}"/>
{check(420, 210, BONE, .9)}
<path d="{wave}" fill="none" stroke="{INK}" stroke-width="2" transform="translate(0,46)"/>
<line x1="330" y1="300" x2="510" y2="270" stroke="{SIGNAL}" stroke-width="4" stroke-linecap="round"/>
{T(420, 330, "VOICE CLONE: NO ANSWER", "fmb", 10, SIGNAL, "middle", 1.5)}
"""
    css = """.w{opacity:0;animation:show 9s infinite}@keyframes show{0%,30%{opacity:1}33.3%,100%{opacity:0}}
.tick{transform-box:fill-box;transform-origin:left;animation:tk 3s linear infinite}@keyframes tk{from{transform:scaleX(1)}to{transform:scaleX(0)}}"""
    card("card-countersign.svg", "06", "AI x security / ForgeHacks 2026", "Countersign",
         "AI can fake a voice. It can't fake the rolling secret your family shares.",
         ["TypeScript", "AI agents", "Speech", "Offline PWA"], art, css)


def aeropulse():
    xs = list(range(80, 761, 34))
    ys = [262 - 26 * math.sin(i * 0.5) - i * 3.6 + 7 * math.sin(i * 1.4) for i in range(len(xs))]
    line = "M" + " L".join(f"{x},{y:.1f}" for x, y in zip(xs, ys))
    area = line + f" L{xs[-1]},316 L{xs[0]},316 Z"
    ticks = "".join(f'<line x1="{x}" y1="316" x2="{x}" y2="322" stroke="{INK}"/>' for x in xs[::4])
    art = f"""
<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{INK}" stroke-opacity=".22" stroke-width="1.5"/></pattern></defs>
{T(60, 98, "CPI / AIRFARE / 11 SOURCES / QUALITY 0-100", "fm", 11, GRAPHITE, ls=1)}
<line x1="80" y1="316" x2="780" y2="316" stroke="{INK}" stroke-width="2"/>{ticks}
<path d="{area}" fill="url(#hatch)" class="fade" style="animation-delay:1.6s"/>
<path d="{line}" pathLength="1" class="plot" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linejoin="round"/>
<circle cx="{xs[-1]}" cy="{ys[-1]:.1f}" r="13" fill="{SIGNAL}" fill-opacity=".25" style="animation:pulse 1.6s infinite"/>
<circle cx="{xs[-1]}" cy="{ys[-1]:.1f}" r="6" fill="{SIGNAL}"/>
<path id="arc" d="M70,150 Q420,40 790,128" fill="none" stroke="{GRAPHITE}" stroke-dasharray="2 7"/>
<g><animateMotion dur="7s" repeatCount="indefinite" rotate="auto"><mpath href="#arc"/></animateMotion>
<path d="M-15,0 L10,-2.5 L17,0 L10,2.5 Z M-2,-1.5 L-9,-13 L-3,-13 L6,-1.5 Z M-2,1.5 L-9,13 L-3,13 L6,1.5 Z M-15,0 L-19,-7 L-15,-7 L-10,-1 Z M-15,0 L-19,7 L-15,7 L-10,1 Z" fill="{INK}"/></g>
{T(80, 340, "T+1", "fm", 10, GRAPHITE)}{T(760, 340, "T+45", "fm", 10, GRAPHITE, "end")}
{T(420, 340, "fixed products: route / carrier / cabin / fare / window", "fs", 16, GRAPHITE, "middle")}
"""
    card("card-aeropulse.svg", "07", "Smart India Hackathon 2026 / SIH26056", "AeroPulse",
         "A prototype airfare price index for MoSPI, built to feed India's CPI.",
         ["Python", "FastAPI", "Next.js", "Docker"], art)


def traceline():
    doc_lines = ""
    widths = [190, 172, 204, 120, 196, 186, 150, 182, 110]
    for i, w in enumerate(widths):
        doc_lines += f'<rect x="92" y="{128+i*20}" width="{w}" height="5" fill="{GRAPHITE}" fill-opacity=".55"/>'
    bullets = ""
    for i, (t, hl) in enumerate([("Bogie inspection overdue", False), ("Track 3 maintenance window", True), ("Vendor invoice approved", False)]):
        y = 156 + i * 38
        bullets += (f'<rect x="478" y="{y-10}" width="9" height="9" fill="{SIGNAL if hl else INK}"/>' +
                    T(498, y, t, "fbb" if hl else "fb", 17, INK if hl else GRAPHITE))
    art = f"""
{T(60, 98, "KOCHI METRO / MALAYALAM + ENGLISH / OCR", "fm", 11, GRAPHITE, ls=1)}
<path d="M72,108 L280,108 L320,148 L320,330 L72,330 Z" fill="{BONE}" stroke="{INK}" stroke-width="2" pathLength="1" class="plot"/>
<path d="M280,108 V148 H320" fill="none" stroke="{INK}" stroke-width="2"/>
{doc_lines}
<rect class="hl" x="86" y="200" width="214" height="46" fill="{SIGNAL}" fill-opacity=".22" stroke="{SIGNAL}" stroke-width="1.5"/>
<path class="lead" d="M300,222 C380,222 390,194 470,194" fill="none" stroke="{SIGNAL}" stroke-width="2" stroke-dasharray="5 5"/>
<rect x="460" y="110" width="320" height="220" fill="{BONE}" stroke="{INK}" stroke-width="2"/>
<rect x="460" y="110" width="320" height="26" fill="{INK}"/>{T(474, 128, "SUMMARY  /  FOR ENGINEERS", "fmb", 11, BONE, ls=1.5)}
{bullets}
<rect x="478" y="282" width="284" height="32" fill="{INK}"/>{T(620, 303, "ACTION  inspect bogie  due Fri", "fm", 11, BONE, "middle", .5)}
"""
    css = """.hl{transform-box:fill-box;transform-origin:left;animation:sweep 3.6s cubic-bezier(.6,0,.3,1) infinite}
@keyframes sweep{0%{transform:scaleX(0);opacity:1}35%,85%{transform:scaleX(1);opacity:1}100%{transform:scaleX(1);opacity:0}}
.lead{animation:flow 1s linear infinite}@keyframes flow{to{stroke-dashoffset:-20}}"""
    card("card-traceline.svg", "08", "Smart India Hackathon 2025 / SIH25080", "Traceline",
         "PDF in, role-specific summaries out. Every point links back to its source paragraph.",
         ["Python", "FastAPI", "Tesseract", "LLMs"], art, css)


def couchpad():
    phones_svg, paths, packets = "", "", ""
    for i, y in enumerate((100, 176, 252)):
        phones_svg += phone(70, y, 108, 60)
        phones_svg += (f'<circle cx="100" cy="{y+30}" r="14" fill="none" stroke="{INK}" stroke-width="1.5"/>'
                       f'<circle class="stick" cx="100" cy="{y+30}" r="5" fill="{INK}" style="animation-delay:-{i*.45:.2f}s"/>'
                       f'<circle cx="146" cy="{y+22}" r="6" fill="{SIGNAL if i == 0 else INK}"/><circle cx="160" cy="{y+38}" r="6" fill="{INK}"/>')
        dash = ' stroke-dasharray="5 5"' if i == 2 else ""
        paths += f'<path id="c{i}" d="M178,{y+30} C320,{y+30} 340,200 470,200" fill="none" stroke="{INK}" stroke-width="1.5"{dash}/>'
        for k in range(2):
            packets += (f'<rect x="-5" y="-5" width="10" height="10" fill="{SIGNAL}"><animateMotion dur="1.7s" begin="-{i*0.55+k*0.85:.2f}s" '
                        f'repeatCount="indefinite"><mpath href="#c{i}"/></animateMotion></rect>')
    qr = "".join(f'<rect x="{724+(j % 5)*7}" y="{116+(j//5)*7}" width="6" height="6" fill="{INK}" fill-opacity="{1 if (j*7) % 3 else .12}"/>' for j in range(25))
    art = f"""
{T(60, 92, "SCAN / JOIN / PLAY  -  NO APP INSTALL", "fm", 11, GRAPHITE, ls=1)}
{paths}{packets}{phones_svg}
<rect x="470" y="104" width="300" height="190" fill="{BONE}" stroke="{INK}" stroke-width="2.5" pathLength="1" class="plot"/>
<path d="M600,294 V310 H640 V294 M572,316 H668" fill="none" stroke="{INK}" stroke-width="2.5"/>
{qr}{T(486, 126, "ROOM K7QX", "fmb", 11, INK, ls=1.5)}
<circle class="p1" cx="560" cy="220" r="11" fill="{SIGNAL}"/><circle class="p2" cx="650" cy="206" r="11" fill="{INK}"/><circle class="p3" cx="600" cy="252" r="11" fill="none" stroke="{INK}" stroke-width="3"/>
{T(320, 336, "webrtc datachannel  /  websocket relay when blocked", "fs", 16, GRAPHITE, "middle")}
"""
    css = """.stick{animation:wig 1.2s ease-in-out infinite alternate}@keyframes wig{from{transform:translate(-6px,3px)}to{transform:translate(6px,-4px)}}
.p1{animation:m1 2.4s ease-in-out infinite alternate}.p2{animation:m2 2s ease-in-out infinite alternate}.p3{animation:m3 2.8s ease-in-out infinite alternate}
@keyframes m1{to{transform:translate(60px,-40px)}}@keyframes m2{to{transform:translate(-70px,30px)}}@keyframes m3{to{transform:translate(100px,-14px)}}"""
    card("card-couchpad.svg", "09", "Open-source library / MIT", "couchpad",
         "Every phone in the room becomes a game controller. Extracted from Cadabra.",
         ["TypeScript", "WebRTC", "WebSocket", "1 dependency"], art, css)


# ---------------------------------------------------------------- mini cards
def mini(name, fig, title, lines, tags, art, css=""):
    W, H = 840, 300
    tags_svg, x = "", 290
    for t in tags:
        t = t.upper()
        tags_svg += f'<rect x="{x}" y="232" width="8" height="8" fill="{SIGNAL}"/>' + T(x + 16, 241, t, "fm", 12, INK, ls=1)
        x += 16 + measure(t, "fm", 12, 1) + 22
    body = f"""
<defs>{grid_pattern("g", 20, BONE3, .6)}<clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{BONE}"/>
<rect x="30" y="30" width="230" height="240" fill="url(#g)"/>{crop(30, 30)}{crop(260, 30)}{crop(30, 270)}{crop(260, 270)}
<g>{art}</g>
{T(W-36, 52, "FIG. " + fig, "fmb", 12, GRAPHITE, "end", 1.5)}
{T(288, 110, title, "fd", 46, INK, ls=-1)}
{T(290, 150, lines[0], "fb", 19, GRAPHITE)}{T(290, 178, lines[1], "fb", 19, GRAPHITE)}
<line x1="290" y1="206" x2="{W-36}" y2="206" stroke="{INK}" stroke-opacity=".25"/>
{tags_svg}</g>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{INK}" stroke-width="2"/>"""
    write(name, doc(W, H, body, css, f"{title}: {' '.join(lines)}"))


def minis():
    art = ""
    for i, (h1, h2) in enumerate([(90, 60), (50, 120), (130, 84), (70, 104)]):
        x = 62 + i * 46
        art += f'<rect class="g" x="{x}" y="{236-h1}" width="16" height="{h1}" fill="{INK}" style="animation-delay:-{i*.3:.1f}s"/>'
        art += f'<rect class="g" x="{x+18}" y="{236-h2}" width="16" height="{h2}" fill="{SIGNAL}" style="animation-delay:-{i*.3+.6:.1f}s"/>'
    art += f'<line x1="50" y1="237" x2="240" y2="237" stroke="{INK}" stroke-width="2"/>' + T(62, 64, "A vs B", "fs", 20, GRAPHITE)
    css = ".g{transform-box:fill-box;transform-origin:bottom;animation:gr 2.2s ease-in-out infinite alternate}@keyframes gr{from{transform:scaleY(.45)}to{transform:scaleY(1)}}"
    mini("mini-devhub.svg", "10", "DevHub", ("GitHub discovery workspace: search, compare", "and save developers and repositories."),
         ["Next.js", "Prisma", "Postgres"], art, css)

    art = f"""<g class="sw" style="transform-origin:145px 150px">
<path d="M85,128 A64,64 0 0 1 205,128" fill="none" stroke="{INK}" stroke-width="8"/><path d="M190,108 L206,130 L182,136" fill="none" stroke="{INK}" stroke-width="8" stroke-linejoin="miter"/>
<path d="M205,172 A64,64 0 0 1 85,172" fill="none" stroke="{SIGNAL}" stroke-width="8"/><path d="M100,192 L84,170 L108,164" fill="none" stroke="{SIGNAL}" stroke-width="8"/></g>
{T(145, 157, "swap", "fs", 22, INK, "middle")}"""
    mini("mini-bartr.svg", "11", "bartr", ("Shopify for campus barter: sell, swap or", "give away inside your own campus."),
         ["Next.js 15", "React 19", "shadcn/ui"], art, ".sw{animation:spin 7s linear infinite}")

    art, y = "", 150
    for i, d in enumerate([-18, 26, -12, -30, 22, -16, 28, -24]):
        o, c = y, y + d
        up = c < o
        x = 52 + i * 24
        art += f'<line x1="{x+6}" y1="{min(o,c)-14}" x2="{x+6}" y2="{max(o,c)+12}" stroke="{INK}" stroke-width="1.5"/>'
        fill = f'fill="{BONE}" stroke="{INK}" stroke-width="2"' if up else f'fill="{SIGNAL}"'
        art += f'<rect class="cd" x="{x}" y="{min(o,c)}" width="12" height="{abs(c-o)}" {fill} style="animation-delay:{i*.18:.2f}s"/>'
        y = c
    art += T(52, 64, "NSE / BSE", "fm", 11, GRAPHITE, ls=1)
    mini("mini-zerobot.svg", "12", "ZeroBot", ("Automated intraday trading for Zerodha", "with capital allocation and risk rules."),
         ["Python", "KiteConnect", "Next.js"], art, ".cd{opacity:0;animation:fade .5s ease-out forwards}")

    art = "".join(f'<circle class="ring" cx="145" cy="150" r="30" fill="none" stroke="{INK}" stroke-width="2" style="animation-delay:-{i}s"/>' for i in range(3))
    art += f'<path d="M145,118 L171,150 L145,182 L119,150 Z" fill="{SIGNAL}"/><path d="M145,118 L145,182 M119,150 L171,150" stroke="{BONE}" stroke-width="1.5"/>'
    mini("mini-web3beacon.svg", "13", "Web3Beacon", ("A friendly guide to Web3, with a wallet", "demo that never signs or moves funds."),
         ["HTML", "CSS", "EIP-6963"], art,
         ".ring{transform-box:fill-box;transform-origin:center;animation:ring 3s ease-out infinite}@keyframes ring{from{transform:scale(.7);opacity:1}to{transform:scale(3.4);opacity:0}}")


# ---------------------------------------------------------------- hero
def hero():
    W, H = 1600, 700
    rods = ""
    rows, cols = 8, 15
    for r in reversed(range(rows)):
        for c in range(cols):
            x = 905 + c * 40 + r * 19
            if x > 1540:
                continue
            base = 500 - r * 30
            h = 170 - r * 12
            op = 0.3 + 0.7 * (1 - r / rows)
            d = (c * 0.16 + r * 0.11) % 3.2
            rods += (f'<rect class="rod" x="{x}" y="{base-h}" width="9" height="{h}" fill="{BONE}" fill-opacity="{op:.2f}" '
                     f'style="animation-delay:-{d:.2f}s"/>')
    roles = ["compilers", "assistive ML", "dev tools", "AI agents", "party games"]
    rx = 64 + measure("NOW SHIPPING", "fmb", 16, 2) + 26
    roles_svg = "".join(f'<g class="role" style="animation-delay:-{((len(roles)-i)*2.6) % 13:.1f}s">' + T(rx, 566, r, "fs", 38, SIGNAL) + "</g>"
                        for i, r in enumerate(roles))
    specs = [("ROLE", "BTech CSE, SRMIST"), ("CLASS OF", "2029"), ("BASED IN", "Chennai, India"), ("STATUS", "open to internships")]
    spec_svg = ""
    for i, (k, v) in enumerate(specs):
        x = 64 + i * 370
        spec_svg += T(x, 640, k, "fm", 11, GRAPHITE, ls=2) + T(x + (18 if k == "STATUS" else 0), 670, v, "fbb", 21, BONE)
        if i:
            spec_svg += f'<line x1="{x-22}" y1="622" x2="{x-22}" y2="676" stroke="{INK3}"/>'
    status_x = 64 + 3 * 370
    body = f"""
<defs>{grid_pattern("hg", 40, INK3, .55)}
<clipPath id="clip"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<clipPath id="l1"><rect x="0" y="96" width="900" height="200"/></clipPath>
<clipPath id="l2"><rect x="0" y="300" width="900" height="160"/></clipPath></defs>
<g clip-path="url(#clip)">
<rect width="{W}" height="{H}" fill="{INK}"/>
<rect width="{W}" height="{H}" fill="url(#hg)"/>
<rect class="scan" x="0" y="0" width="{W}" height="2" fill="{SIGNAL}" fill-opacity=".35"/>
{T(64, 52, "MK-01", "fmb", 13, BONE, ls=2)}
{T(800, 52, "PROFILE DATASHEET  /  REV 2026.10", "fm", 12, GRAPHITE, "middle", 2)}
{T(1536, 52, "13.03 N  80.18 E  /  CHENNAI", "fm", 12, GRAPHITE, "end", 2)}
<line x1="64" y1="72" x2="1536" y2="72" stroke="{INK3}"/>
<g clip-path="url(#l1)"><g class="rise">{T(52, 268, "Maanav", "fd", 196, BONE, ls=-7)}</g></g>
<g clip-path="url(#l2)"><g class="rise" style="animation-delay:.15s"><text x="52" y="436" class="fd" font-size="164" fill="{BONE}" letter-spacing="-6">Krishna<tspan fill="{SIGNAL}">.</tspan></text></g></g>
<g class="fade" style="animation-delay:.6s">{T(64, 500, "builds systems that hold up when no one is watching.", "fs", 36, ASH)}</g>
{T(64, 560, "NOW SHIPPING", "fmb", 16, GRAPHITE, ls=2)}
{roles_svg}
<line x1="64" y1="604" x2="1536" y2="604" stroke="{INK3}"/>
{spec_svg}
<circle cx="{status_x+6}" cy="663" r="6" fill="{SIGNAL}" style="animation:pulse 1.4s infinite"/>
{rods}
{T(1536, 560, "FIG. 00  /  ACTUATOR FIELD, LIVE", "fm", 11, GRAPHITE, "end", 2)}
{crop(30, 30, 9, GRAPHITE)}{crop(W-30, 30, 9, GRAPHITE)}{crop(30, H-30, 9, GRAPHITE)}{crop(W-30, H-30, 9, GRAPHITE)}
</g>"""
    css = """.rod{transform-box:fill-box;transform-origin:bottom;animation:wave 3.2s ease-in-out infinite,hot 3.2s ease-in-out infinite}
@keyframes wave{0%,100%{transform:scaleY(.22)}50%{transform:scaleY(1)}}
@keyframes hot{0%,38%,62%,100%{fill:#EDE7DB}48%,52%{fill:#FF5B14}}
.rise{animation:rise 1.2s cubic-bezier(.2,.8,.2,1) both}@keyframes rise{from{transform:translateY(200px)}to{transform:none}}
.role{opacity:0;animation:roll 13s infinite}
@keyframes roll{0%{opacity:0;transform:translateY(18px)}3%,17%{opacity:1;transform:none}20%,100%{opacity:0;transform:translateY(-18px)}}
.scan{animation:scan 6s linear infinite}@keyframes scan{from{transform:translateY(0)}to{transform:translateY(700px)}}"""
    write("hero.svg", doc(W, H, body, css, "Maanav Krishna builds systems that hold up when no one is watching. BTech CSE at SRMIST, class of 2029, Chennai. Open to internships."))


# ---------------------------------------------------------------- odometer stats
def stats():
    W, H = 1600, 270
    cells = [("1", "st", "RANK", "ML Empowerment Build Challenge 3.0"),
             ("6", "", "HACKATHON BUILDS", "shipped across 2025 and 2026"),
             ("2", "x", "SMART INDIA HACKATHON", "Traceline '25, AeroPulse '26"),
             ("80", "+", "PUBLIC REPOSITORIES", "and one framework on PyPI")]
    cw = W / 4
    LH = 150
    body = f'<rect width="{W}" height="{H}" rx="18" fill="{BONE}"/>'
    defs = ""
    for i, (num, suf, label, cap) in enumerate(cells):
        x0 = i * cw
        defs += f'<clipPath id="o{i}"><rect x="{x0}" y="78" width="{cw}" height="140"/></clipPath>'
        body += T(x0 + 40, 54, f"0{i+1}", "fmb", 13, SIGNAL, ls=1.5) + T(x0 + 82, 54, label, "fm", 12, GRAPHITE, ls=1.5)
        size = 150
        x = x0 + 34
        odo = ""
        for j, ch in enumerate(num):
            target = int(ch)
            seq = list(range(10)) + list(range(target + 1))
            cwid = measure("0", "fd", size, -4)
            col = "".join(T(x + cwid / 2, 206 + k * LH, str(d), "fd", size, INK, "middle") for k, d in enumerate(seq))
            dist = (len(seq) - 1) * LH
            odo += (f'<g class="odo" style="--d:-{dist}px;animation-delay:{0.2*i+0.15*j:.2f}s">{col}</g>')
            x += cwid
        x -= (measure("0", "fd", size, -4) - measure(num[-1], "fd", size, -4)) / 2
        body += f'<g clip-path="url(#o{i})">{odo}</g>'
        if suf:
            body += f'<g class="fade" style="animation-delay:{1.6+0.2*i:.1f}s">' + T(x + 6, 206 if suf != "st" else 140, suf, "fd", 86 if suf != "st" else 52, SIGNAL if suf != "st" else INK) + "</g>"
        body += T(x0 + 40, 246, cap, "fs", fit(cap, "fs", 22, cw - 70), GRAPHITE)
        if i:
            body += f'<line x1="{x0}" y1="28" x2="{x0}" y2="{H-28}" stroke="{INK}" stroke-opacity=".9"/>'
    body = f"<defs>{defs}</defs>" + body + f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{INK}" stroke-width="2"/>'
    css = ".odo{animation:odo 2.2s cubic-bezier(.15,.85,.25,1) both}@keyframes odo{from{transform:translateY(0)}to{transform:translateY(var(--d))}}"
    write("stats.svg", doc(W, H, body, css, "1st place at ML Empowerment Build Challenge 3.0. 6 hackathon builds. 2 Smart India Hackathons. 80+ public repositories."))


# ---------------------------------------------------------------- section headers
def header(name, idx, title, note):
    W, H = 1600, 104
    ticks = "".join(f'<line x1="{x}" y1="{H}" x2="{x}" y2="{H-(14 if (x // 16) % 5 == 0 else 7)}" stroke="{BONE}" stroke-opacity=".28"/>'
                    for x in range(-80, W + 96, 16))
    body = f"""<defs><clipPath id="clip"><rect width="{W}" height="{H}" rx="14"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{INK}"/>
<g class="ruler">{ticks}</g>
{T(40, 60, "§" + idx, "fmb", 18, SIGNAL, ls=1)}
{T(116, 66, title, "fd", 46, BONE, ls=-1)}
{T(W-40, 60, note.upper(), "fm", 12, GRAPHITE, "end", 2)}
<rect class="cur" x="{116 + measure(title, "fd", 46, -1) + 14:.0f}" y="30" width="5" height="40" fill="{SIGNAL}"/></g>"""
    css = ".ruler{animation:ruler 5s linear infinite}@keyframes ruler{to{transform:translateX(-80px)}}.cur{animation:blink 1.1s steps(1) infinite}"
    write(name, doc(W, H, body, css, f"{idx} {title}"))


# ---------------------------------------------------------------- terminal
def terminal():
    W = 1600
    lines = [
        ("cmd", "whoami"),
        ("out", "maanav krishna  /  BTech CSE @ SRMIST Ramapuram  /  2025-2029  /  CGPA 8.88"),
        ("cmd", "cat highlights.txt"),
        ("hi", "1st place, ML Empowerment Build Challenge 3.0, with Hum"),
        ("hi", "Smart India Hackathon twice: Traceline '25, AeroPulse '26"),
        ("hi", "Author of PyWeb:  pip install pyweb-stack"),
        ("cmd", "echo $MOTTO"),
        ("quote", "Measure honestly, show the source, let the results decide."),
        ("cmd", "./status --now"),
        ("ok", "open to internships and research collaborations: SWE, ML, quant"),
    ]
    step = 46
    H = 112 + len(lines) * step + 50
    prompt_w = measure("maanav@srm", "fmb", 21) + 14
    pct_w = measure("~ %", "fm", 21) + 14
    body, t = "", 0.4
    for i, (kind, txt) in enumerate(lines):
        y = 130 + i * step
        if kind == "cmd":
            cx = 60 + prompt_w + pct_w
            w = measure(txt, "fm", 21) + 8
            body += (T(60, y, "maanav@srm", "fmb", 21, SIGNAL) + T(60 + prompt_w, y, "~ %", "fm", 21, GRAPHITE) +
                     T(cx, y, txt, "fm", 21, BONE) +
                     f'<rect class="type" x="{cx-2:.0f}" y="{y-24}" width="{w:.0f}" height="32" fill="{INK}" '
                     f'style="animation-delay:{t:.2f}s;animation-duration:{len(txt)*0.04:.2f}s"/>')
            t += len(txt) * 0.04 + 0.2
        elif kind == "quote":
            body += f'<g class="out" style="animation-delay:{t:.2f}s">' + T(60, y + 4, txt, "fs", 32, BONE) + "</g>"
            t += 0.2
        else:
            col = {"out": ASH, "hi": BONE, "ok": BONE}[kind]
            pre = ""
            if kind == "hi":
                pre = f'<rect x="60" y="{y-12}" width="10" height="10" fill="{SIGNAL}"/>'
            if kind == "ok":
                pre = f'<circle cx="65" cy="{y-7}" r="6" fill="{SIGNAL}" style="animation:pulse 1.4s infinite"/>'
            body += f'<g class="out" style="animation-delay:{t:.2f}s">{pre}' + T(60 + (26 if pre else 0), y, txt, "fm", 19, col) + "</g>"
            t += 0.2
    yc = 130 + len(lines) * step
    body += (T(60, yc, "maanav@srm", "fmb", 21, SIGNAL) + T(60 + prompt_w, yc, "~ %", "fm", 21, GRAPHITE) +
             f'<rect class="cur" x="{60+prompt_w+pct_w:.0f}" y="{yc-20}" width="12" height="26" fill="{BONE}"/>')
    svg = f"""<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="{INK}" stroke="{INK3}" stroke-width="2"/>
<path d="M19,1 H{W-19} A18,18 0 0 1 {W-1},19 V60 H1 V19 A18,18 0 0 1 19,1 Z" fill="{INK2}"/>
<line x1="1" y1="60" x2="{W-1}" y2="60" stroke="{INK3}"/>
<circle cx="38" cy="31" r="8" fill="none" stroke="{GRAPHITE}" stroke-width="1.5"/><circle cx="64" cy="31" r="8" fill="none" stroke="{GRAPHITE}" stroke-width="1.5"/><circle cx="90" cy="31" r="8" fill="{SIGNAL}"/>
{T(W/2, 37, "maanav@srm  ~/profile", "fm", 14, GRAPHITE, "middle", 1)}
{T(W-40, 37, "ZSH  /  80x24", "fm", 12, INK3, "end", 2)}
{body}"""
    css = """.out{opacity:0;animation:fade .45s ease-out forwards}
.type{transform-box:fill-box;transform-origin:right;animation-name:type;animation-timing-function:steps(16);animation-fill-mode:both}
@keyframes type{from{transform:scaleX(1)}to{transform:scaleX(0)}}.cur{animation:blink 1s steps(1) infinite}"""
    write("about-terminal.svg", doc(W, H, svg, css, "About Maanav Krishna"))


# ---------------------------------------------------------------- metro-map timeline
def timeline():
    W, H = 1600, 440
    path = "M90,180 H560 L690,310 H1510"
    stations = [  # (x, y, year, name, project, winner, label above?)
        (200, 180, "2025", "Smart India Hackathon", "Traceline / Kochi Metro", False, True),
        (440, 180, "2026", "Smart India Hackathon", "AeroPulse / MoSPI", False, True),
        (820, 310, "2026", "ML Empowerment 3.0", "Hum / first place", True, False),
        (1050, 310, "2026", "ForgeHacks", "Countersign / AI x security", False, True),
        (1260, 310, "2026", "Graph Hacks", "Deadlock / FalkorDB", False, False),
        (1450, 310, "2026", "Build, Ship, Shape", "Cadabra / Fire TV", False, True),
    ]
    st = ""
    for i, (x, y, yr, nm, pj, win, up) in enumerate(stations):
        if win:
            st += (f'<circle cx="{x}" cy="{y}" r="30" fill="{SIGNAL}" fill-opacity=".18" style="animation:pulse 1.8s infinite"/>'
                   f'<circle cx="{x}" cy="{y}" r="21" fill="{BONE}" stroke="{INK}" stroke-width="6"/><circle cx="{x}" cy="{y}" r="9" fill="{SIGNAL}"/>')
        else:
            st += f'<circle cx="{x}" cy="{y}" r="13" fill="{BONE}" stroke="{INK}" stroke-width="5"/>'
        ty = y - 84 if up else y + 56
        size = fit(nm, "fh", 24, 220)
        tag = f"{yr}  /  WINNER" if win else yr
        st += (f'<g class="fade" style="animation-delay:{0.4+0.18*i:.2f}s">' +
               (f'<rect x="{x-measure(tag, "fmb", 12, 1.5)/2-8:.0f}" y="{ty-16}" width="{measure(tag, "fmb", 12, 1.5)+16:.0f}" height="22" fill="{SIGNAL}"/>' if win else "") +
               T(x, ty, tag, "fmb", 12, BONE if win else GRAPHITE, "middle", 1.5) +
               T(x, ty + 30, nm, "fh", size, INK, "middle", -.3) +
               T(x, ty + 54, pj, "fs", 19, GRAPHITE, "middle") + "</g>")
    body = f"""<defs>{grid_pattern("tg", 24, BONE3, .5)}<clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{BONE}"/><rect width="{W}" height="{H}" fill="url(#tg)"/>
</g>
<rect x="40" y="34" width="86" height="30" fill="{INK}"/>{T(83, 55, "LINE H", "fmb", 13, BONE, "middle", 1.5)}
{T(142, 55, "THE HACKATHON LINE  /  2025 - 2026  /  6 STOPS", "fm", 12, GRAPHITE, ls=1.5)}
<g transform="translate(1290,36)"><rect width="34" height="14" rx="7" fill="{SIGNAL}"/>{T(46, 13, "next stop: yours", "fs", 20, INK)}</g>
<path d="{path}" fill="none" stroke="{INK}" stroke-width="16" stroke-linejoin="round" stroke-linecap="round" pathLength="1" class="plot"/>
<path id="metro" d="{path}" fill="none"/>
<g><animateMotion dur="10s" repeatCount="indefinite" rotate="auto"><mpath href="#metro"/></animateMotion><rect x="-24" y="-7" width="48" height="14" rx="7" fill="{SIGNAL}"/></g>
{st}
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="{INK}" stroke-width="2"/>"""
    write("timeline.svg", doc(W, H, body, "", "The hackathon line: Smart India Hackathon 2025 (Traceline), Smart India Hackathon 2026 (AeroPulse), ML Empowerment 3.0 (Hum, first place), ForgeHacks (Countersign), Graph Hacks (Deadlock), Amazon Build, Ship, Shape (Cadabra)."))


# ---------------------------------------------------------------- bill of materials
def bom():
    rows = [
        ("PY-01", "Python", "PyWeb, Hum, AeroPulse, Traceline, ZeroBot"),
        ("TS-02", "TypeScript", "Aftershock, Cadabra, Deadlock, Countersign, couchpad"),
        ("CX-03", "C / C++", "data structures, systems, coursework"),
        ("WB-04", "Next.js / React", "Aftershock, DevHub, bartr, Countersign"),
        ("AP-05", "FastAPI / Django", "AeroPulse, Traceline"),
        ("DB-06", "PostgreSQL / Prisma / Redis", "DevHub, PyWeb, records systems"),
        ("GR-07", "FalkorDB / Cypher", "Deadlock"),
        ("ML-08", "PyTorch / ONNX Runtime Web", "Hum, with conformal prediction"),
        ("AI-09", "LLM APIs / Bedrock / Claude", "Aftershock, Cadabra, Deadlock, Countersign"),
        ("RT-10", "WebRTC / WebSocket", "couchpad, Cadabra"),
        ("OP-11", "Docker / Vercel / Actions", "everything that ships, with pytest and Vitest"),
    ]
    W = 1600
    top = 176
    step = 52
    H = top + len(rows) * step + 40
    body = f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="18" fill="{INK}" stroke="{INK3}" stroke-width="2"/>'
    body += T(48, 74, "Bill of materials", "fd", 40, BONE, ls=-1)
    body += T(W - 48, 70, f"REV 2026.10  /  {len(rows)} LINES", "fm", 12, GRAPHITE, "end", 2)
    body += T(48, 132, "REF", "fmb", 11, GRAPHITE, ls=2) + T(200, 132, "COMPONENT", "fmb", 11, GRAPHITE, ls=2) + T(800, 132, "WHERE IT SHIPPED", "fmb", 11, GRAPHITE, ls=2)
    body += f'<line x1="48" y1="148" x2="{W-48}" y2="148" stroke="{BONE}" stroke-opacity=".5"/>'
    for i, (ref, comp, where) in enumerate(rows):
        y = top + i * step + 10
        body += (f'<g class="fade" style="animation-delay:{0.08*i:.2f}s">' + T(48, y, ref, "fmb", 14, SIGNAL, ls=1) +
                 T(200, y + 2, comp, "fh", fit(comp, "fh", 26, 560), BONE, ls=-.3) +
                 T(800, y + 1, where, "fb", fit(where, "fb", 20, 750), ASH) +
                 f'<line x1="48" y1="{y+20}" x2="{W-48}" y2="{y+20}" stroke="{INK3}"/></g>')
    write("toolbox.svg", doc(W, H, body, "", "Toolbox: Python, TypeScript, C and C++, Next.js, React, FastAPI, Django, PostgreSQL, Prisma, Redis, FalkorDB, PyTorch, ONNX, LLM APIs, Bedrock, WebRTC, Docker, Vercel, GitHub Actions."))


# ---------------------------------------------------------------- footer marquee
def footer():
    W, H = 1600, 230
    words = ["PYTHON", "TYPESCRIPT", "C++", "ONNX", "WEBRTC", "FALKORDB", "FASTAPI", "NEXT.JS", "COMPILERS", "CONFORMAL"]
    size = 96
    sep = "   /   "
    parts, x = "", 0
    for w in words:
        parts += T(x, 128, w, "fd", size, "none", extra=f'stroke="{BONE}" stroke-width="1.6"')
        x += measure(w, "fd", size)
        parts += T(x, 128, sep, "fd", size, SIGNAL)
        x += measure(sep, "fd", size)
    total = x
    body = f"""<defs><clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
<g clip-path="url(#clip)"><rect width="{W}" height="{H}" fill="{INK}"/>
<g class="mq" style="--w:-{total:.0f}px">{parts}<g transform="translate({total:.1f},0)">{parts}</g></g>
<line x1="40" y1="172" x2="{W-40}" y2="172" stroke="{INK3}"/>
{T(40, 204, "END OF DATASHEET", "fmb", 12, BONE, ls=2)}
{T(W/2, 204, "MK  /  2026  /  BUILT IN CHENNAI", "fm", 12, GRAPHITE, "middle", 2)}
{T(W-40, 204, "GITHUB.COM/MAANAVKRISHNA", "fm", 12, GRAPHITE, "end", 2)}</g>"""
    css = f".mq{{animation:mq {total/90:.1f}s linear infinite}}@keyframes mq{{to{{transform:translateX(var(--w))}}}}"
    write("footer.svg", doc(W, H, body, css, ""))


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    aftershock(); pyweb(); hum(); cadabra(); deadlock(); countersign(); aeropulse(); traceline(); couchpad()
    minis(); hero(); stats(); terminal(); timeline(); bom(); footer()
    for f, i, t, n in [("h-about.svg", "01", "About", "whoami"),
                       ("h-work.svg", "02", "Selected work", "9 figures, all shipped"),
                       ("h-more.svg", "03", "More builds", "smaller, still real"),
                       ("h-trail.svg", "04", "Hackathon line", "6 stops so far"),
                       ("h-stack.svg", "05", "Toolbox", "parts list"),
                       ("h-activity.svg", "06", "Activity", "live from github"),
                       ("h-connect.svg", "07", "Let's build something", "say hello")]:
        header(f, i, t, n)
    print("\n".join(sorted(f"{os.path.getsize(os.path.join(OUT, f))//1024:>4} KB  {f}" for f in os.listdir(OUT))))


if __name__ == "__main__":
    main()
