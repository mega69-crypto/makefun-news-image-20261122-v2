#!/usr/bin/env python3
"""Sum up 22 November 2026's world news in one image.

A deterministic front page (1024x1024 PNG) drawn with the Python
standard library only: no Pillow, no third-party modules at all, so it
runs in the grader's pinned image where nothing is installed.

Text comes from a bitmap font atlas (atlas.png, shipped beside this
file): DejaVu Sans bold and regular glyphs rendered once at build time
into a grid, decoded here with zlib. Shapes are drawn with small
raster helpers written below, and the final image is encoded as PNG
by hand. No network, no clock, no randomness, so the same input
always produces the same bytes.

Run: python3 main.py
Writes /output/entry.png when MAKEFUN_OUTPUT_DIR (default /output)
exists, otherwise ./entry.png
"""

import binascii
import math
import os
import struct
import zlib

W, H = 1024, 1024
BG = (10, 26, 47)
CARD = (18, 42, 71)
CARD_EDGE = (30, 58, 92)
INK = (255, 255, 255)
MUTED = (199, 211, 224)
FAINT = (122, 143, 166)
GOLD = (232, 184, 75)
TICKER_BG = (14, 34, 56)
TICKER_INK = (232, 230, 223)

STORIES = [
    {
        "kicker": "MEXICO",
        "headline": "Mexico captures El Chapo's son Isidro",
        "summary": "Soldiers seized the cartel figure in a military operation, "
                   "a major blow to the Sinaloa cartel.",
        "accent": (232, 184, 75),
        "icon": "target",
    },
    {
        "kicker": "CLIMATE",
        "headline": "COP31 nears a deal as a new draft lands",
        "summary": "A third draft, released on Sunday, recalls the "
                   "COP28 fossil-fuel deal. Objections close at 03:00 GMT.",
        "accent": (78, 205, 196),
        "icon": "globe",
    },
    {
        "kicker": "CYBER",
        "headline": "FBI probes breach of its crime database",
        "summary": "Suspected hackers broke into the NCIC system, "
                   "which lists wanted people and stolen property.",
        "accent": (255, 107, 107),
        "icon": "lock",
    },
    {
        "kicker": "QUAKE",
        "headline": "Magnitude 4.1 quake strikes Myanmar",
        "summary": "The tremor hit at 02:35 local time, 95 km deep. "
                   "No damage or casualties were reported.",
        "accent": (108, 180, 255),
        "icon": "wave",
    },
    {
        "kicker": "ISRAEL",
        "headline": "Coalition talks open in Israel",
        "summary": "Yashar and Likud begin marathon talks today as Eisenkot "
                   "seeks the broadest possible government.",
        "accent": (126, 217, 87),
        "icon": "talks",
    },
    {
        "kicker": "ROYALS",
        "headline": "Kate film tells her road to recovery",
        "summary": "A new film follows the Princess of Wales through cancer "
                   "treatment and her return to public life.",
        "accent": (199, 146, 234),
        "icon": "crown",
    },
]

TICKER = [
    "France: 82,500 march in a sixth weekend of cost-of-living protests",
    "Kryvyi Rih: Russian strike kills two",
    "Cyclone Akvan grounds 14 flights at Ranchi airport",
]

SOURCES = "Sources: BBC, Reuters, ANI, AP, France 24 / AFP  \u00b7  22 November 2026"

# ------------------------------------------------------------------ canvas
canvas = bytearray(W * H * 3)


def plot(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = c[0]
        canvas[i + 1] = c[1]
        canvas[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            canvas[i] = c[0]
            canvas[i + 1] = c[1]
            canvas[i + 2] = c[2]


def hline(x0, x1, y, c):
    if x0 > x1:
        x0, x1 = x1, x0
    for x in range(max(0, x0), min(W, x1 + 1)):
        plot(x, y, c)


def vline(x, y0, y1, c):
    if y0 > y1:
        y0, y1 = y1, y0
    for y in range(max(0, y0), min(H, y1 + 1)):
        plot(x, y, c)


def disc(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(cx - dx, cx + dx, cy + dy, c)


def thick_seg(x0, y0, x1, y1, c, t):
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    rad = max(1, t // 2)
    for k in range(steps + 1):
        f = k / steps
        disc(int(round(x0 + (x1 - x0) * f)),
             int(round(y0 + (y1 - y0) * f)), rad, c)


def polyline(points, c, t, closed=False):
    pts = list(points)
    if closed:
        pts = pts + [pts[0]]
    for a, b in zip(pts, pts[1:]):
        thick_seg(a[0], a[1], b[0], b[1], c, t)


def poly_fill(points, c):
    ys = [p[1] for p in points]
    y0, y1 = min(ys), max(ys)
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, ya = points[i]
            x1, yb = points[(i + 1) % n]
            if ya == yb:
                continue
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(int(xs[k]), int(xs[k + 1]), y, c)


def ellipse_points(cx, cy, rx, ry, a0=0.0, a1=360.0, steps=48):
    pts = []
    for k in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * k / steps)
        pts.append((int(round(cx + rx * math.cos(a))),
                    int(round(cy + ry * math.sin(a)))))
    return pts


def circle_outline(cx, cy, r, c, t):
    polyline(ellipse_points(cx, cy, r, r), c, t, closed=True)


def ellipse_outline(cx, cy, rx, ry, c, t):
    polyline(ellipse_points(cx, cy, rx, ry), c, t, closed=True)


def arc_outline(cx, cy, r, a0, a1, c, t):
    polyline(ellipse_points(cx, cy, r, r, a0, a1, steps=24), c, t)


def round_rect_fill(x, y, w, h, r, c):
    fill_rect(x + r, y, w - 2 * r, h, c)
    fill_rect(x, y + r, w, h - 2 * r, c)
    disc(x + r, y + r, r, c)
    disc(x + w - r - 1, y + r, r, c)
    disc(x + r, y + h - r - 1, r, c)
    disc(x + w - r - 1, y + h - r - 1, r, c)


def round_rect_outline(x, y, w, h, r, c, t):
    thick_seg(x + r, y, x + w - r, y, c, t)
    thick_seg(x + r, y + h, x + w - r, y + h, c, t)
    thick_seg(x, y + r, x, y + h - r, c, t)
    thick_seg(x + w, y + r, x + w, y + h - r, c, t)
    for cx, cy, a0, a1 in (
            (x + r, y + r, 180, 270),
            (x + w - r, y + r, 270, 360),
            (x + w - r, y + h - r, 0, 90),
            (x + r, y + h - r, 90, 180)):
        arc_outline(cx, cy, r, a0, a1, c, t)


# ---------------------------------------------------------------- PNG codec
def _paeth(a, b, cc):
    p = a + b - cc
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return cc


def read_rgba(path):
    """Minimal PNG reader: 8-bit, non-interlaced, color type 2 or 6."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    w = h = None
    ctype = None
    idat = bytearray()
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", chunk)
            assert depth == 8 and inter == 0
            assert ctype in (2, 6)
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    ch = 4 if ctype == 6 else 3
    stride = w * ch
    raw = zlib.decompress(bytes(idat))
    out = bytearray(w * h * 4)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        row = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(ch, stride):
                row[i] = (row[i] + row[i - ch]) & 255
        elif ft == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = row[i - ch] if i >= ch else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = row[i - ch] if i >= ch else 0
                b = prev[i]
                cc = prev[i - ch] if i >= ch else 0
                row[i] = (row[i] + _paeth(a, b, cc)) & 255
        elif ft != 0:
            raise ValueError("bad filter %d" % ft)
        if ch == 4:
            out[y * w * 4:(y + 1) * w * 4] = row
        else:
            for x in range(w):
                o = (y * w + x) * 4
                s = x * 3
                out[o] = row[s]
                out[o + 1] = row[s + 1]
                out[o + 2] = row[s + 2]
                out[o + 3] = 255
        prev = row
    return w, h, out


def encode_png(rgb, w, h):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, payload):
        return (struct.pack(">I", len(payload)) + typ + payload +
                struct.pack(">I", binascii.crc32(typ + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------------- font
FONT_SIZE = 64
CELL_W = 76
CELL_H = 96
COLS = 10
ROWS_PER_WEIGHT = 10

# Advance width of each glyph at size 64, in atlas order:
# ASCII 32..126, then U+2022 (bullet), U+00B7 (middle dot).
ADV_BOLD = [22, 29, 33, 54, 45, 64, 56, 20, 29, 29, 33, 54, 24, 27, 24, 23, 45, 45, 45, 45, 45, 45, 45, 45, 45, 45, 26, 26, 54, 54, 54, 37, 64, 50, 49, 47, 53, 44, 44, 53, 54, 24, 24, 50, 41, 64, 54, 54, 47, 54, 49, 46, 44, 52, 50, 71, 49, 46, 46, 29, 23, 29, 54, 32, 32, 43, 46, 38, 46, 43, 28, 46, 46, 22, 22, 43, 22, 67, 46, 44, 46, 46, 32, 38, 31, 46, 42, 59, 41, 42, 37, 46, 23, 46, 54, 41, 24]
ADV_REG = [20, 26, 29, 54, 41, 61, 50, 18, 25, 25, 32, 54, 20, 23, 20, 22, 41, 41, 41, 41, 41, 41, 41, 41, 41, 41, 22, 22, 54, 54, 54, 34, 64, 44, 44, 45, 49, 40, 37, 50, 48, 19, 19, 42, 36, 55, 48, 50, 39, 50, 44, 41, 39, 47, 44, 63, 44, 39, 44, 25, 22, 25, 54, 32, 32, 39, 41, 35, 41, 39, 23, 41, 41, 18, 18, 37, 18, 62, 41, 39, 41, 41, 26, 33, 25, 41, 38, 52, 38, 38, 34, 41, 22, 41, 54, 38, 20]

ATLAS_W = 0
ATLAS_H = 0
ATLAS = b""
_glyph_cache = {}


def load_atlas():
    global ATLAS_W, ATLAS_H, ATLAS
    here = os.path.dirname(os.path.abspath(__file__))
    ATLAS_W, ATLAS_H, ATLAS = read_rgba(os.path.join(here, "atlas.png"))


def char_index(ch):
    o = ord(ch)
    if 32 <= o <= 126:
        return o - 32
    if ch == "\u2022":
        return 95
    if ch == "\u00b7":
        return 96
    return 0


def advance(ch, bold, size):
    idx = char_index(ch)
    table = ADV_BOLD if bold else ADV_REG
    return table[idx] * size / FONT_SIZE


def glyph(ch, bold, size):
    key = (ch, bold, size)
    g = _glyph_cache.get(key)
    if g is not None:
        return g
    idx = char_index(ch)
    col = idx % COLS
    row = idx // COLS + (0 if bold else ROWS_PER_WEIGHT)
    sx0 = col * CELL_W
    sy0 = row * CELL_H
    scale = size / FONT_SIZE
    dw = max(1, int(round(CELL_W * scale)))
    dh = max(1, int(round(CELL_H * scale)))
    alpha = bytearray(dw * dh)
    inv = 1.0 / scale
    for dy in range(dh):
        y0 = dy * inv
        y1 = (dy + 1) * inv
        iy0 = int(y0)
        iy1 = min(CELL_H - 1, int(y1))
        for dx in range(dw):
            x0 = dx * inv
            x1 = (dx + 1) * inv
            ix0 = int(x0)
            ix1 = min(CELL_W - 1, int(x1))
            s = 0.0
            wsum = 0.0
            for iy in range(iy0, iy1 + 1):
                wy = min(y1, iy + 1) - max(y0, iy)
                if wy <= 0:
                    continue
                base = ((sy0 + iy) * ATLAS_W + sx0) * 4 + 3
                for ix in range(ix0, ix1 + 1):
                    wx = min(x1, ix + 1) - max(x0, ix)
                    if wx <= 0:
                        continue
                    s += ATLAS[base + ix * 4] * wx * wy
                    wsum += wx * wy
            alpha[dy * dw + dx] = int(s / wsum + 0.5) if wsum else 0
    g = (dw, dh, alpha)
    _glyph_cache[key] = g
    return g


def text_width(s, size, bold=False):
    return sum(advance(ch, bold, size) for ch in s)


def draw_text(s, x, y, color, size, bold=False):
    cx = float(x)
    for ch in s:
        dw, dh, alpha = glyph(ch, bold, size)
        bx = int(round(cx))
        for dy in range(dh):
            yy = y + dy
            if yy < 0 or yy >= H:
                continue
            rowbase = (yy * W + bx) * 3
            abase = dy * dw
            for dx in range(dw):
                a = alpha[abase + dx]
                if a == 0:
                    continue
                xx = bx + dx
                if xx < 0 or xx >= W:
                    continue
                i = rowbase + dx * 3
                if a == 255:
                    canvas[i] = color[0]
                    canvas[i + 1] = color[1]
                    canvas[i + 2] = color[2]
                else:
                    canvas[i] = (canvas[i] * (255 - a) + color[0] * a) // 255
                    canvas[i + 1] = (canvas[i + 1] * (255 - a) +
                                     color[1] * a) // 255
                    canvas[i + 2] = (canvas[i + 2] * (255 - a) +
                                     color[2] * a) // 255
        cx += advance(ch, bold, size)
    return cx


def draw_centered(s, cx, y, color, size, bold=False):
    draw_text(s, int(round(cx - text_width(s, size, bold) / 2)), y,
              color, size, bold)


def draw_tracked(s, cx, y, color, size, tracking=5, bold=False):
    total = text_width(s, size, bold) + tracking * (len(s) - 1)
    x = cx - total / 2
    for ch in s:
        draw_text(ch, int(round(x)), y, color, size, bold)
        x += advance(ch, bold, size) + tracking


def wrap_text(s, max_w, size, bold=False):
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, size, bold) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_text(s, max_w, max_lines, start, bold=False, min_size=14):
    size = start
    while size > min_size:
        lines = wrap_text(s, max_w, size, bold)
        if len(lines) <= max_lines:
            return size, lines
        size -= 1
    return min_size, wrap_text(s, max_w, min_size, bold)[:max_lines]


def line_height(size):
    return int(round(size * 1.28))


def ticker_lines(max_w, size):
    """Split the ticker at item boundaries when a clean split fits,
    so no single news item is torn across two lines. A boundary split
    at one size smaller beats a mid-item word wrap at the larger size.
    Falls back to ordinary word wrap (shrinking the size) when no
    boundary split fits at any size."""
    sep = "  \u2022  "
    for s in range(size, 13, -1):
        for cut in (1, 2):
            first = sep.join(TICKER[:cut])
            rest = sep.join(TICKER[cut:])
            if (text_width(first, s) <= max_w
                    and text_width(rest, s) <= max_w):
                return s, [first, rest]
    return fit_text(sep.join(TICKER), max_w, 2, size)


# ------------------------------------------------------------------ icons
def icon_target(cx, cy, color):
    circle_outline(cx, cy, 22, color, 5)
    disc(cx, cy, 6, color)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        thick_seg(cx + dx * 27, cy + dy * 27, cx + dx * 33, cy + dy * 33,
                  color, 5)


def icon_globe(cx, cy, color):
    circle_outline(cx, cy, 24, color, 5)
    thick_seg(cx - 24, cy, cx + 24, cy, color, 4)
    ellipse_outline(cx, cy, 9, 24, color, 4)


def icon_lock(cx, cy, color):
    arc_outline(cx, cy - 11, 13, 180, 360, color, 5)
    round_rect_outline(cx - 19, cy - 2, 38, 28, 7, color, 4)
    disc(cx, cy + 11, 3, color)


def icon_wave(cx, cy, color):
    pts = [(cx - 28, cy + 2), (cx - 19, cy - 12), (cx - 11, cy + 10),
           (cx - 3, cy - 18), (cx + 5, cy + 14), (cx + 13, cy - 8),
           (cx + 22, cy + 2), (cx + 28, cy + 2)]
    polyline(pts, color, 5)


def icon_talks(cx, cy, color):
    ellipse_outline(cx - 12, cy - 6, 15, 15, color, 4)
    ellipse_outline(cx + 12, cy + 6, 15, 15, color, 4)
    disc(cx - 12, cy - 6, 3, color)
    disc(cx + 12, cy + 6, 3, color)


def icon_crown(cx, cy, color):
    pts = [(cx - 24, cy + 16), (cx - 24, cy - 6), (cx - 12, cy + 4),
           (cx, cy - 14), (cx + 12, cy + 4), (cx + 24, cy - 6),
           (cx + 24, cy + 16)]
    polyline(pts, color, 4, closed=True)
    for tx, ty in ((cx - 24, cy - 8), (cx, cy - 16), (cx + 24, cy - 8)):
        disc(tx, ty, 3, color)


ICONS = {
    "target": icon_target,
    "globe": icon_globe,
    "lock": icon_lock,
    "wave": icon_wave,
    "talks": icon_talks,
    "crown": icon_crown,
}


# ------------------------------------------------------------------ build
def build():
    load_atlas()
    fill_rect(0, 0, W, H, BG)

    # Masthead
    draw_tracked("THE WORLD IN ONE PAGE", W // 2, 32, GOLD, 20,
                 tracking=5, bold=True)
    draw_centered("SUNDAY 22 NOVEMBER 2026", W // 2, 60, INK, 52, bold=True)
    fill_rect(36, 128, W - 72, 3, GOLD)

    # Story grid: 2 columns x 3 rows
    margin, gap = 36, 24
    card_w = (W - 2 * margin - gap) // 2
    card_h = 227
    top = 150
    for i, story in enumerate(STORIES):
        row, col = divmod(i, 2)
        x = margin + col * (card_w + gap)
        y = top + row * (card_h + gap)
        round_rect_fill(x, y, card_w, card_h, 14, CARD)
        round_rect_outline(x, y, card_w, card_h, 14, CARD_EDGE, 2)
        accent = story["accent"]
        bx, by = x + 58, y + 113
        circle_outline(bx, by, 40, accent, 3)
        ICONS[story["icon"]](bx, by, accent)
        tx = x + 118
        draw_text(story["kicker"], tx, y + 24, accent, 18, bold=True)
        text_max = card_w - 118 - 20
        hsize, hlines = fit_text(story["headline"], text_max, 2, 29,
                                 bold=True)
        hy = y + 50
        for line in hlines:
            draw_text(line, tx, hy, INK, hsize, bold=True)
            hy += line_height(hsize)
        ssize, slines = fit_text(story["summary"], text_max, 3, 19)
        sy = y + 132
        for line in slines:
            draw_text(line, tx, sy, MUTED, ssize)
            sy += line_height(ssize)

    # Ticker
    ty0, ty1 = 895, 957
    round_rect_fill(margin, ty0, W - 2 * margin, ty1 - ty0, 12, TICKER_BG)
    round_rect_outline(margin, ty0, W - 2 * margin, ty1 - ty0, 12,
                       CARD_EDGE, 2)
    draw_text("LATEST", 54, ty0 + (ty1 - ty0 - 18) // 2, GOLD, 18, bold=True)
    tsize, tlines = ticker_lines(W - margin - 150 - 18, 19)
    th = len(tlines) * line_height(tsize)
    tyy = ty0 + (ty1 - ty0 - th) // 2
    for line in tlines:
        draw_text(line, 150, tyy, TICKER_INK, tsize)
        tyy += line_height(tsize)

    # Footer
    draw_centered(SOURCES, W // 2, 972, FAINT, 16)

    return bytes(canvas)


def output_path():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if outdir is None:
        outdir = "/output" if os.path.isdir("/output") else os.getcwd()
    os.makedirs(outdir, exist_ok=True)
    return os.path.join(outdir, "entry.png")


def main():
    data = encode_png(build(), W, H)
    path = output_path()
    with open(path, "wb") as f:
        f.write(data)
    print("wrote", path, (W, H), "RGB")


if __name__ == "__main__":
    main()
