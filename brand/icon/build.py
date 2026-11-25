"""Icon for the to-slack plugin in the Kensae style (32-unit grid, Kensae palette).

python3 build.py writes the SVGs and sheet.html; shoot.py renders sheet.png and 1024 px PNGs
(.claude-plugin/icon.png is 6b-heading-8-day-1024.png). Earlier candidates stay in the code."""
from pathlib import Path
import base64
_font = Path(__file__).parent / "KensaeSans-Regular.woff2"  # optional, only candidate 4 (M) uses it
FONT = "data:font/woff2;base64," + base64.b64encode(_font.read_bytes()).decode() if _font.exists() else ""

PAL = {"day": dict(bg="#f4e8dc", ink="#0d0e1c", sun="#e2412e"),
       "night": dict(bg="#141e32", ink="#ebe6dc", sun="#d27850")}
# Baou ridge from the Kensae avatar (brand/kensae-draft/svg/avatar-day.svg)
RIDGE = ("M-2 40L-2 28.05L-4.9 26.26L0.2 27.28L5.3 28.47L9.55 29.32L10.57 29.32L11.68 27.88L12.78 25.92"
         "L13.38 24.05L13.8 21.67L14.31 19.63L14.82 18.1L15.5 17.25L18.48 17.25L22.3 17.59L24.85 18.27"
         "L26.72 18.78L27.06 20.23L28.68 20.65L34 20.82L34 40Z")
RIDGE_LOW = ("M-2 40L-2 26.5L3 25.8L7.5 26.6L11 27.4L13.2 25.6L15 23.4L16.4 22.6L19.8 22.6L23.4 23.1"
             "L26.2 23.8L27 25L29.5 25.3L34 25.3L34 40Z")

def ring(cx, cy, fg, bg):
    return (f'<circle cx="{cx}" cy="{cy}" r="3" fill="{fg}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="1" fill="{bg}"/>')

def scene(sym, p, sun, ridge=RIDGE, uid="x"):
    """sym(fg, bg) -> svg; drawn in ink over the sky and in paper over the ridge (the Kensae flip)."""
    bg, ink = p["bg"], p["ink"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<defs><clipPath id="r{uid}"><path d="{ridge}"/></clipPath>
<style>@font-face{{font-family:KS;src:url({FONT})}}</style></defs>
<rect x="-1" y="-1" width="34" height="34" fill="{bg}"/>
<circle cx="{sun[0]}" cy="{sun[1]}" r="{sun[2]}" fill="{p['sun']}"/>
<g>{sym(ink, bg)}</g>
<path d="{ridge}" fill="{ink}"/>
<g clip-path="url(#r{uid})">{sym(bg, ink)}</g>
</svg>'''

# 1. Hash on the ridge: a channel # in 4-unit strokes, the K's git node on its top end.
def hash_sym(fg, bg):
    s = 'transform="skewX(-12) translate(4.2 0)"'
    return (f'<g {s}><rect x="10" y="6" width="4" height="22" fill="{fg}"/>'
            f'<rect x="18" y="6" width="4" height="22" fill="{fg}"/></g>'
            f'<rect x="5" y="11" width="22" height="4" fill="{fg}"/>'
            f'<rect x="4" y="19" width="22" height="4" fill="{fg}"/>' + ring(22.1, 6.6, fg, bg))

# 2. Table bubble: a square chat bubble holding a table, header row solid.
def bubble_sym(fg, bg):
    return (f'<path d="M4 6H28V23H12L7 28V23H4Z" fill="{fg}"/>'
            f'<rect x="6.5" y="12" width="19" height="8.5" fill="{bg}"/>'
            f'<rect x="15" y="12" width="2" height="8.5" fill="{fg}"/>'
            f'<rect x="6.5" y="15.25" width="19" height="2" fill="{fg}"/>'
            f'<circle cx="9.5" cy="9" r="1" fill="{bg}"/>')

# 3. Clipboard: the clip is the Kensae ring; a heading bar and two bullet lines.
def clip_sym(fg, bg):
    return (f'<rect x="7" y="7" width="18" height="21" fill="{fg}"/>'
            f'<rect x="12" y="5" width="8" height="4" fill="{fg}"/>' + ring(16, 5, fg, bg) +
            f'<rect x="10" y="12" width="12" height="3" fill="{bg}"/>'
            f'<circle cx="11" cy="18.5" r="1.2" fill="{bg}"/><rect x="13.5" y="17.5" width="8.5" height="2" fill="{bg}"/>'
            f'<circle cx="11" cy="23" r="1.2" fill="{bg}"/><rect x="13.5" y="22" width="6" height="2" fill="{bg}"/>')

# 4. M down: the markdown mark redrawn in Kensae Sans, the arrow dropping into the ridge.
def mdown_sym(fg, bg):
    return (f'<text x="2.6" y="22" font-family="KS" font-size="20.5" fill="{fg}">M</text>'
            f'<rect x="21" y="6" width="4" height="12" fill="{fg}"/>'
            f'<path d="M17.5 16H28.5L23 23.5Z" fill="{fg}"/>')


def board(fg, bg):
    return (f'<rect x="7" y="7" width="18" height="21" fill="{fg}"/>'
            f'<rect x="12" y="5" width="8" height="4" fill="{fg}"/>' + ring(16, 5, fg, bg))

def hash_at(x, y, size, col, w=None):
    """A # in a size x size box at (x, y): two verticals slanted 12 degrees, two bars that cross
    both with the same overhang. Stroke w defaults to size/5.5 (4 in 22, the Kensae ratio)."""
    import math
    w = w or size / 5.5
    t = math.tan(math.radians(12))
    lean = t * size                       # horizontal shift from bottom to top
    gap = size - 2 * w - lean - 2 * (w * 0.55)   # inner space between the verticals
    gap = max(gap, w * 1.1)
    v1 = x + w * 0.55                     # bottom-left x of left vertical (after left overhang)
    v2 = v1 + w + gap
    def vert(bx):
        return f'M{bx:.2f} {y+size:.2f}L{bx+w:.2f} {y+size:.2f}L{bx+w+lean:.2f} {y:.2f}L{bx+lean:.2f} {y:.2f}Z'
    def bar(by):
        # x of the left edge of the left vertical and right edge of the right vertical at height by
        frac = (y + size - by - w / 2) / size
        left = v1 + lean * frac - w * 0.55
        right = v2 + w + lean * frac + w * 0.55
        return f'M{left:.2f} {by:.2f}H{right:.2f}V{by+w:.2f}H{left:.2f}Z'
    b1, b2 = y + size * 0.28 - w / 2, y + size * 0.70 - w / 2
    return "".join(f'<path fill="{col}" d="{d}"/>' for d in (vert(v1), vert(v2), bar(b1), bar(b2)))

# 3a. The board carries one big # knocked out in paper.
def clip_hash_big(fg, bg):
    return board(fg, bg) + hash_at(9.6, 12, 12, bg, 2.3)

# 3b. Markdown heading line "# ____" then two bullet lines: the # is both channel and heading.
def clip_hash_heading(fg, bg):
    return (board(fg, bg) + hash_at(9.4, 11.2, 5.2, bg, 1.25) +
            f'<rect x="15.5" y="12.4" width="7" height="3" fill="{bg}"/>'
            f'<circle cx="11" cy="19.5" r="1.2" fill="{bg}"/><rect x="13.5" y="18.5" width="8.5" height="2" fill="{bg}"/>'
            f'<circle cx="11" cy="24" r="1.2" fill="{bg}"/><rect x="13.5" y="23" width="6" height="2" fill="{bg}"/>')

# 3c. A sheet held by the ring clip, the # printed on it in ink (outline board, solid #).
def clip_hash_sheet(fg, bg):
    return (f'<rect x="8.25" y="8.25" width="15.5" height="18.5" fill="none" stroke="{fg}" stroke-width="2.5"/>'
            f'<rect x="12" y="5" width="8" height="4" fill="{fg}"/>' + ring(16, 5, fg, bg) +
            hash_at(10.2, 12, 11.5, fg, 2.4))

# 3d. The # itself is the clipboard: its frame is the board, the clip ring on top.
def clip_hash_frame(fg, bg):
    return (f'<rect x="7" y="7" width="18" height="21" fill="{fg}"/>'
            f'<rect x="12" y="5" width="8" height="4" fill="{fg}"/>' + ring(16, 5, fg, bg) +
            f'<rect x="10" y="10.5" width="12" height="15" fill="{bg}"/>' + hash_at(10.6, 11.6, 12.5, fg, 2.6))

RIDGE_LOWER = ("M-2 40L-2 27.2L3 26.5L7.5 27.3L10.5 28.1L12.6 27.4L14.6 26.7L16.6 26.4L20 26.4L23.4 26.8"
               "L26.2 25.6L27.2 24.6L29.5 24.9L34 24.9L34 40Z")

def heading_variant(hsize, hw, bar_w, bullets, top=10.4):
    def sym(fg, bg):
        out = board(fg, bg) + hash_at(9.0, top, hsize, bg, hw)
        bar_h = 2.0
        bx = 9.0 + hsize + 2.2
        out += f'<rect x="{bx:.2f}" y="{top + hsize/2 - bar_h/2:.2f}" width="{23 - bx:.2f}" height="{bar_h:.2f}" fill="{bg}"/>'
        y = top + hsize + 2.3
        for w in bullets:
            out += (f'<circle cx="11" cy="{y + 1:.2f}" r="1.25" fill="{bg}"/>'
                    f'<rect x="13.6" y="{y:.2f}" width="{w}" height="2" fill="{bg}"/>')
            y += 3.6
        return out
    return sym

CANDS = [
    ("6b-heading-8", "Chosen icon: # heading line + bullets", heading_variant(8, 1.6, 0, [8.4, 5.6], top=10.2), (24.5, 9.5, 4.5), RIDGE_LOWER),
]

out = Path(__file__).parent
cards = []
for key, label, fn, sun, ridge in CANDS:
    for mode in ("day", "night"):
        svg = scene(fn, PAL[mode], sun, ridge, uid=f"{key}{mode}".replace("-", ""))
        (out / f"{key}-{mode}.svg").write_text(svg)
    cards.append((key, label))

rows = "".join(f'''<section><h2>{label}</h2><div class="row">
<img src="{k}-day.svg" width="256"><img src="{k}-night.svg" width="256">
<div class="small"><img src="{k}-day.svg" width="64"><img src="{k}-night.svg" width="64">
<img src="{k}-day.svg" width="32"><img src="{k}-night.svg" width="32">
<img src="{k}-day.svg" width="16"><img src="{k}-night.svg" width="16"></div></div></section>''' for k, label in cards)
(out / "sheet.html").write_text(f'''<!doctype html><meta charset="utf-8"><title>to-slack icon candidates</title>
<style>@font-face{{font-family:KS;src:url(KensaeSans-Regular.woff2)}}
body{{margin:0;padding:32px;background:#e9dfd3;font:14px ui-monospace,monospace;color:#0d0e1c}}
h1{{font-family:KS;font-size:40px;margin:0 0 24px;letter-spacing:.02em}}
h2{{font-family:KS;font-size:20px;margin:28px 0 10px}}
.row{{display:flex;gap:18px;align-items:flex-end}} .small{{display:flex;gap:14px;align-items:flex-end}}
img{{display:block}}</style><h1>TO SLACK ICON</h1>{rows}''')
print("ok", len(cards))
