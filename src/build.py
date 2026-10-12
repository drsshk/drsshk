"""Builds every image in assets/ for the github.com/drsshk profile README.

Run from the repo root:  python3 src/build.py
Needs fonttools + brotli. Recursive (the darusishak.com typeface) is instanced into
static cuts, subset to the glyphs used and embedded, so GitHub renders the real type.
"""
import base64
import io
import math
import random
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "assets"

BLUE = "#1F4BFF"
INK = "#111012"
WHITE = "#FFFFFF"
SUN = "#FFC83D"
MUTE = "#6B6670"
LIGHT_FG, DARK_FG = "#1F2328", "#E6EDF3"
LIGHT_MUTE, DARK_MUTE = "#59636E", "#9198A1"

CUTS = {
    "cas": {"MONO": 0, "CASL": 1, "wght": 800},
    "mono": {"MONO": 1, "CASL": 0, "wght": 500},
    "monob": {"MONO": 1, "CASL": 0, "wght": 750},
    "sans": {"MONO": 0, "CASL": 0, "wght": 420},
}
GLYPHS = "".join(chr(c) for c in range(32, 127)) + "·×³°"

FONTS = {}
INSTANCES = {}


def load_fonts():
    for name, loc in CUTS.items():
        inst = instancer.instantiateVariableFont(TTFont(SRC / "fonts" / "recursive.woff2"), loc)
        buf = io.BytesIO()
        inst.save(buf)
        INSTANCES[name] = buf.getvalue()
        FONTS[name] = {"cmap": inst.getBestCmap(), "hmtx": inst["hmtx"].metrics, "upm": inst["head"].unitsPerEm}


def font_b64(cut, chars):
    """The cut subset to the characters one image uses, as woff2."""
    inst = TTFont(io.BytesIO(INSTANCES[cut]))
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern"]
    sub = subset.Subsetter(opts)
    sub.populate(text=chars + " ")
    sub.subset(inst)
    buf = io.BytesIO()
    inst.flavor = "woff2"
    inst.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def width(text, cut, size):
    f = FONTS[cut]
    total = 0
    for ch in text:
        g = f["cmap"].get(ord(ch))
        total += f["hmtx"][g][0] if g else f["upm"] * 0.5
    return total * size / f["upm"]


def wrap(text, cut, size, maxw):
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if width(t, cut, size) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_css(*cuts):
    out = []
    for c in cuts:
        out.append(
            f"@font-face{{font-family:r-{c};src:url(data:font/woff2;base64,@@{c}@@) format('woff2')}}"
            f".{c}{{font-family:r-{c},ui-monospace,monospace}}"
        )
    return "".join(out)


def text(x, y, s, cut, size, fill, anchor="start", extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" {"" if "class=" in extra else f'class="{cut}"'} font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" {extra}>{esc(s)}</text>'
    )


def arrow(x, y, size, color, diag=False):
    """Arrow drawn as a path (Recursive has no arrow glyphs). (x, y) = left end on the baseline-ish middle."""
    s = size
    if diag:
        return (
            f'<path d="M{x:.1f} {y:.1f} l{s:.1f} {-s:.1f} M{x + s * 0.3:.1f} {y - s:.1f} h{s * 0.7:.1f} v{s * 0.7:.1f}" '
            f'stroke="{color}" stroke-width="{max(1.6, s / 7):.1f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    return (
        f'<path d="M{x:.1f} {y:.1f} h{s:.1f} M{x + s * 0.6:.1f} {y - s * 0.4:.1f} l{s * 0.4:.1f} {s * 0.4:.1f} l{-s * 0.4:.1f} {s * 0.4:.1f}" '
        f'stroke="{color}" stroke-width="{max(1.6, s / 7):.1f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def svg(w, h, label, body, css=""):
    import re, html
    for cut in CUTS:
        if f"@@{cut}@@" in css:
            used = "".join(html.unescape(t) for t in re.findall(rf'class="(?:[^"]* )?{cut}(?: [^"]*)?"[^>]*>([^<]*)<', body))
            css = css.replace(f"@@{cut}@@", font_b64(cut, "".join(sorted(set(used)))))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
        f"<title>{esc(label)}</title><style>{css}</style>{body}</svg>\n"
    )


def save(name, content):
    (OUT / name).write_text(content, encoding="utf-8")
    print(f"{name:28s} {len(content.encode()) / 1024:6.1f} KB")


def img_b64(path):
    return "data:image/webp;base64," + base64.b64encode(path.read_bytes()).decode()


# ------------------------------------------------------------------ hero
def trend_points(x0, x1, ytop, ybot):
    """One day of a plant tag at 15-minute resolution: 96 readings."""
    rnd = random.Random(15)
    pts = []
    level = 0.55
    for i in range(96):
        hour = i / 4
        day = 0.18 * math.sin((hour - 9) / 24 * 2 * math.pi)
        level += rnd.uniform(-0.035, 0.035) + (0.55 + day - level) * 0.18
        if 54 <= i <= 57:  # a short trip and recovery, as plants do
            level -= 0.09
        v = max(0.05, min(0.95, level))
        x = x0 + (x1 - x0) * i / 95
        y = ybot - (ybot - ytop) * v
        pts.append((x, y))
    return pts


def slotted(name, size, x0, y, fill_cas, fill_mono):
    """Both cuts letter by letter in shared slots, so the seam swaps type without the word shifting."""
    cas, mono, x = [], [], x0
    for ch in name:
        wc, wm = width(ch, "cas", size), width(ch, "mono", size)
        slot = max(wc, wm) - (8 if ch != " " else 22)
        if ch != " ":
            cas.append(text(x + slot / 2, y, ch, "cas", size, fill_cas, "middle"))
            mono.append(text(x + slot / 2, y, ch, "mono", size, fill_mono, "middle"))
        x += slot
    return "".join(cas), "".join(mono), x


def hero():
    W, H = 1200, 440
    seam_a, seam_b = 600, 720
    name = "Darus Ishak"
    size = 128
    pts = trend_points(56, 1144, 248, 338)
    name_cas, name_mono, _ = slotted(name, 136, 52, 198, WHITE, INK)
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    plen = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) + 10
    ex, ey = pts[-1]

    css = font_css("cas", "mono", "monob", "sans") + (
        f".draw{{stroke-dasharray:{plen:.0f};stroke-dashoffset:{plen:.0f};animation:draw 3.4s cubic-bezier(.16,1,.3,1) .4s forwards}}"
        "@keyframes draw{to{stroke-dashoffset:0}}"
        ".pulse{transform-origin:center;transform-box:fill-box;animation:pulse 2.4s ease-out 3.4s infinite;opacity:0}"
        "@keyframes pulse{0%{opacity:.55;transform:scale(1)}100%{opacity:0;transform:scale(3.2)}}"
        ".fade{opacity:0;animation:fade .9s ease 3.2s forwards}@keyframes fade{to{opacity:1}}"
        "@media (prefers-reduced-motion:reduce){.draw{animation:none;stroke-dashoffset:0}.fade{animation:none;opacity:1}.pulse{display:none}}"
    )

    spline = 'calcMode="spline" keyTimes="0;0.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"'
    anim_w = f'<animate attributeName="width" values="{seam_a};{seam_b};{seam_a}" dur="12s" repeatCount="indefinite" {spline}/>'
    anim_x = f'<animate attributeName="x" values="{seam_a};{seam_b};{seam_a}" dur="12s" repeatCount="indefinite" {spline}/>'
    anim_t = (
        f'<animateTransform attributeName="transform" type="translate" values="{seam_a} 0;{seam_b} 0;{seam_a} 0" '
        f'dur="12s" repeatCount="indefinite" {spline}/>'
    )

    def grid(color):
        g = []
        for i in range(0, 25, 3):
            x = 56 + (1144 - 56) * i / 24
            g.append(f'<line x1="{x:.1f}" y1="240" x2="{x:.1f}" y2="346" stroke="{color}" stroke-width="1"/>')
        for y in (248, 293, 338):
            g.append(f'<line x1="56" y1="{y}" x2="1144" y2="{y}" stroke="{color}" stroke-width="1"/>')
        return "".join(g)

    def hours(color):
        return "".join(
            text(56 + (1144 - 56) * h / 24, 366, f"{h:02d}:00", "mono", 11, color,
                 "start" if h == 0 else ("end" if h == 24 else "middle"))
            for h in range(0, 25, 6)
        )

    left = (
        f'<rect width="{W}" height="{H}" fill="{BLUE}"/>'
        + grid("rgba(255,255,255,.14)")
        + text(56, 62, "DARUSISHAK.COM", "monob", 13, WHITE, extra='letter-spacing="2.5"')
        + name_cas
        + f'<path class="draw" d="{path}" fill="none" stroke="{WHITE}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>'
        + hours("rgba(255,255,255,.62)")
        + text(56, 404, "BEFORE", "monob", 12, SUN, extra='letter-spacing="2"')
        + text(56, 424, "The plant floor", "sans", 15, WHITE)
    )
    right = (
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>'
        + grid("rgba(17,16,18,.08)")
        + text(1144, 62, "ENGINEER · BUILDER", "monob", 13, INK, "end", 'letter-spacing="2.5"')
        + name_mono
        + f'<path class="draw" d="{path}" fill="none" stroke="{BLUE}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>'
        + hours(MUTE)
        + text(1144, 404, "NOW", "monob", 12, BLUE, "end", 'letter-spacing="2"')
        + text(1144, 424, "The software behind it", "sans", 15, INK, "end")
        + f'<circle class="pulse" cx="{ex:.1f}" cy="{ey:.1f}" r="6" fill="{BLUE}"/>'
        + f'<circle class="fade" cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="{BLUE}"/>'
        + text(ex - 12, ey - 14, "LIVE", "monob", 10, BLUE, "end", 'class="monob fade" letter-spacing="1.5"')
    )
    seam = (
        f'<g transform="translate({seam_a} 0)">{anim_t}'
        f'<line x1="0" y1="0" x2="0" y2="{H}" stroke="{INK}" stroke-width="2"/>'
        f'<rect x="-20" y="{H / 2 - 66}" width="40" height="28" rx="14" fill="{INK}"/>'
        f'<path d="M-9 {H / 2 - 52} l5 -5 M-9 {H / 2 - 52} l5 5 M-9 {H / 2 - 52} h18 M9 {H / 2 - 52} l-5 -5 M9 {H / 2 - 52} l-5 5" '
        f'stroke="{WHITE}" stroke-width="2" stroke-linecap="round" fill="none"/></g>'
    )
    body = (
        f'<defs><clipPath id="card"><rect width="{W}" height="{H}" rx="28"/></clipPath>'
        f'<clipPath id="L"><rect x="0" y="0" width="{seam_a}" height="{H}">{anim_w}</rect></clipPath>'
        f'<clipPath id="R"><rect x="{seam_a}" y="0" width="{W}" height="{H}">{anim_x}</rect></clipPath></defs>'
        f'<g clip-path="url(#card)"><g clip-path="url(#R)">{right}</g><g clip-path="url(#L)">{left}</g>{seam}</g>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="27" fill="none" stroke="{INK}" stroke-opacity=".12" stroke-width="2"/>'
    )
    save("hero.svg", svg(W, H, "Darus Ishak. Before: the plant floor. Now: the software behind it.", body, css))


# ------------------------------------------------------------------ section headers
def header(num, title, note):
    W, H = 1200, 96
    for mode, fg, mute in (("light", LIGHT_FG, LIGHT_MUTE), ("dark", DARK_FG, DARK_MUTE)):
        tw = width(title, "cas", 46)
        x_rule = 56 + tw + 26
        nw = width(note.upper(), "monob", 12) + len(note) * 2
        body = (
            text(0, 64, num, "monob", 14, BLUE if mode == "light" else "#7C93FF", extra='letter-spacing="2"')
            + text(44, 70, title, "cas", 46, fg, extra='letter-spacing="-1"')
            + f'<line x1="{x_rule:.0f}" y1="56" x2="{W - nw - 18:.0f}" y2="56" stroke="{mute}" stroke-opacity=".45" stroke-width="1.5"/>'
            + text(W, 61, note.upper(), "monob", 12, mute, "end", 'letter-spacing="2"')
        )
        save(f"h-{num}-{mode}.svg", svg(W, H, f"{num} {title}", body, font_css("cas", "monob")))


# ------------------------------------------------------------------ Ruji Labs
def studio_card():
    W, H = 1200, 200
    logo = (SRC / "ruji-labs-logo-white.svg").read_text()
    logo_b64 = "data:image/svg+xml;base64," + base64.b64encode(logo.encode()).decode()
    lh = 92
    lw = lh * 1149 / 616
    body = (
        f'<rect width="{W}" height="{H}" rx="26" fill="{INK}"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="25" fill="none" stroke="{WHITE}" stroke-opacity=".16" stroke-width="2"/>'
        f'<image href="{logo_b64}" x="48" y="{(H - lh) / 2:.0f}" width="{lw:.0f}" height="{lh}"/>'
        f'<line x1="{48 + lw + 40:.0f}" y1="48" x2="{48 + lw + 40:.0f}" y2="{H - 48}" stroke="{WHITE}" stroke-opacity=".2"/>'
    )
    x = 48 + lw + 80
    body += text(x, 74, "RUJI LABS", "monob", 12, SUN, extra='letter-spacing="2"')
    y = 112
    for line in wrap("My product studio. Software for Malaysian businesses, live in production.", "sans", 20, W - x - 56):
        body += text(x, y, line, "sans", 20, WHITE)
        y += 30
    save("studio.svg", svg(W, H, "Ruji Labs, my product studio in Shah Alam.", body, font_css("monob", "sans")))


def tile(slug, name, kind, year, line, domain):
    W, H = 384, 236
    p = 24
    body = [
        f'<rect x="1.5" y="6" width="{W - 3}" height="{H - 7.5}" rx="20" fill="{INK}"/>',
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 8}" rx="20" fill="{WHITE}" stroke="{INK}" stroke-width="2"/>',
        text(p, 44, kind.upper(), "monob", 11, BLUE, extra='letter-spacing="1.8"'),
        text(W - p, 44, year, "mono", 12, MUTE, "end"),
        text(p - 1, 86, name, "cas", 32, INK, extra='letter-spacing="-.6"'),
    ]
    y = 118
    for ln in wrap(line, "sans", 15, W - p * 2)[:3]:
        body.append(text(p, y, ln, "sans", 15, "#3A3640"))
        y += 22
    body.append(text(p, H - 34, domain, "mono", 13, INK))
    body.append(arrow(W - p - 13, H - 34, 12, INK, diag=True))
    save(f"p-{slug}.svg", svg(W, H, f"{name}: {line}", "".join(body), font_css("cas", "monob", "mono", "sans")))


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    load_fonts()
    hero()
    header("01", "Ruji Labs", "what I build")
    studio_card()
    products = [
        ("postlah", "Post-Lah", "Social posting", "2026", "Write it, or let AI write it. Post-Lah schedules it, posts it and answers the comments.", "post-lah.my"),
        ("nodex", "NodeX", "Bio storefront", "2026", "One link in your bio for products, orders and bookings. Buyers pay you directly.", "nodex.my"),
        ("berkira", "Berkira", "Receipts and tax", "2026", "Snap a receipt, AI reads it, export a Tax Agent Pack at year end.", "berkira.com"),
        ("conecta", "Conecta", "Name cards", "2026", "One identity, many name cards. Printed QR codes can be re-pointed without reprinting.", "conecta.my"),
        ("workit", "WorkIt", "Service operations", "2026", "Quotation to job to service report, for contractors and maintenance teams.", "workit.my"),
        ("semakcv", "SemakCV", "Resumes", "2026", "Upload a resume, get rewritten bullet points and an ATS score against the job ad.", "semakcv.com"),
    ]
    for p in products:
        tile(*p)


if __name__ == "__main__":
    main()
