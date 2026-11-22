#!/usr/bin/env python3
"""Sum up 22 November 2026's world news in one image.

A deterministic front page (1024x1024 PNG) drawn with Pillow: six verified
stories from 22 November 2026 plus a ticker of secondary items. No network,
no clock, no randomness, so the same input always produces the same bytes.

Run: python3 main.py
Writes /output/entry.png when /output exists, otherwise ./entry.png
"""

import os
from PIL import Image, ImageDraw, ImageFont

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

BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
REGULAR_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

_font_cache = {}


def load_font(size, bold=False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    font = None
    for path in BOLD_PATHS if bold else REGULAR_PATHS:
        try:
            font = ImageFont.truetype(path, size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def text_w(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def wrap(draw, text, font, max_width):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, max_width, max_lines, start_size, bold=False, min_size=14):
    size = start_size
    while size > min_size:
        font = load_font(size, bold=bold)
        lines = wrap(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 1
    font = load_font(min_size, bold=bold)
    return font, wrap(draw, text, font, max_width)[:max_lines]


def line_height(font):
    return int(round(font.size * 1.28))


def draw_tracked(draw, cx, y, text, font, fill, tracking=5):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def draw_centered(draw, cx, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    x = cx - (box[2] - box[0]) / 2 - box[0]
    draw.text((x, y), text, font=font, fill=fill)


def icon_target(draw, cx, cy, color):
    draw.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), outline=color, width=5)
    draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=color)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        draw.line((cx + dx * 27, cy + dy * 27, cx + dx * 33, cy + dy * 33),
                  fill=color, width=5)


def icon_globe(draw, cx, cy, color):
    draw.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), outline=color, width=5)
    draw.line((cx - 24, cy, cx + 24, cy), fill=color, width=4)
    draw.ellipse((cx - 9, cy - 24, cx + 9, cy + 24), outline=color, width=4)


def icon_lock(draw, cx, cy, color):
    draw.arc((cx - 13, cy - 26, cx + 13, cy + 4), start=180, end=0,
             fill=color, width=5)
    draw.rounded_rectangle((cx - 19, cy - 2, cx + 19, cy + 26), radius=7,
                           outline=color, width=4)
    draw.ellipse((cx - 3, cy + 8, cx + 3, cy + 14), fill=color)


def icon_wave(draw, cx, cy, color):
    pts = [(cx - 28, cy + 2), (cx - 19, cy - 12), (cx - 11, cy + 10),
           (cx - 3, cy - 18), (cx + 5, cy + 14), (cx + 13, cy - 8),
           (cx + 22, cy + 2), (cx + 28, cy + 2)]
    draw.line(pts, fill=color, width=5, joint="curve")


def icon_talks(draw, cx, cy, color):
    draw.ellipse((cx - 27, cy - 21, cx + 3, cy + 9), outline=color, width=4)
    draw.ellipse((cx - 3, cy - 9, cx + 27, cy + 21), outline=color, width=4)
    draw.ellipse((cx - 15, cy - 9, cx - 9, cy - 3), fill=color)
    draw.ellipse((cx + 9, cy + 3, cx + 15, cy + 9), fill=color)


def icon_crown(draw, cx, cy, color):
    pts = [(cx - 24, cy + 16), (cx - 24, cy - 6), (cx - 12, cy + 4),
           (cx, cy - 14), (cx + 12, cy + 4), (cx + 24, cy - 6),
           (cx + 24, cy + 16)]
    draw.line(pts + [pts[0]], fill=color, width=4, joint="curve")
    for tx, ty in ((cx - 24, cy - 8), (cx, cy - 16), (cx + 24, cy - 8)):
        draw.ellipse((tx - 3, ty - 3, tx + 3, ty + 3), fill=color)


ICONS = {
    "target": icon_target,
    "globe": icon_globe,
    "lock": icon_lock,
    "wave": icon_wave,
    "talks": icon_talks,
    "crown": icon_crown,
}


def build():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Masthead
    kicker_font = load_font(20, bold=True)
    draw_tracked(draw, W // 2, 32, "THE WORLD IN ONE PAGE", kicker_font,
                 GOLD, tracking=5)
    date_font = load_font(52, bold=True)
    draw_centered(draw, W // 2, 60, "SUNDAY 22 NOVEMBER 2026", date_font, INK)
    draw.line((36, 128, W - 36, 128), fill=GOLD, width=3)

    # Story grid: 2 columns x 3 rows
    margin, gap = 36, 24
    card_w = (W - 2 * margin - gap) // 2
    card_h = 227
    top = 150
    for i, story in enumerate(STORIES):
        row, col = divmod(i, 2)
        x = margin + col * (card_w + gap)
        y = top + row * (card_h + gap)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=14,
                               fill=CARD, outline=CARD_EDGE, width=2)
        accent = story["accent"]
        bx, by = x + 58, y + 113
        draw.ellipse((bx - 40, by - 40, bx + 40, by + 40), outline=accent,
                     width=3)
        ICONS[story["icon"]](draw, bx, by, accent)
        tx = x + 118
        kicker = load_font(18, bold=True)
        draw.text((tx, y + 24), story["kicker"], font=kicker, fill=accent)
        text_max = card_w - 118 - 20
        hfont, hlines = fit_lines(draw, story["headline"], text_max, 2, 29,
                                  bold=True)
        hy = y + 50
        for line in hlines:
            draw.text((tx, hy), line, font=hfont, fill=INK)
            hy += line_height(hfont)
        sfont, slines = fit_lines(draw, story["summary"], text_max, 3, 19,
                                  bold=False)
        sy = y + 132
        for line in slines:
            draw.text((tx, sy), line, font=sfont, fill=MUTED)
            sy += line_height(sfont)

    # Ticker
    ty0, ty1 = 895, 957
    draw.rounded_rectangle((margin, ty0, W - margin, ty1), radius=12,
                           fill=TICKER_BG, outline=CARD_EDGE, width=2)
    label_font = load_font(18, bold=True)
    draw.text((54, ty0 + (ty1 - ty0 - 18) // 2), "LATEST", font=label_font,
              fill=GOLD)
    ticker_text = "  \u2022  ".join(TICKER)
    tfont, tlines = fit_lines(draw, ticker_text, W - margin - 150 - 18, 2, 19,
                              bold=False)
    th = len(tlines) * line_height(tfont)
    tyy = ty0 + (ty1 - ty0 - th) // 2
    for line in tlines:
        draw.text((150, tyy), line, font=tfont, fill=TICKER_INK)
        tyy += line_height(tfont)

    # Footer
    footer_font = load_font(16, bold=False)
    draw_centered(draw, W // 2, 972, SOURCES, footer_font, FAINT)

    return img


def output_path():
    if os.path.isdir("/output"):
        return "/output/entry.png"
    return os.path.join(os.getcwd(), "entry.png")


def main():
    img = build()
    path = output_path()
    img.save(path, format="PNG")
    print("wrote", path, img.size, img.mode)


if __name__ == "__main__":
    main()
