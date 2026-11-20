#!/usr/bin/env python3
"""news-image-20261120 — "The World in One Day", Friday 20 November 2026.

Draws a 1024x1024 front-page image summarising the day's world news and
writes it as a PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).

Standard library only. Fully deterministic: no clock, no randomness,
no dependence on dict/hash ordering. Two runs produce identical bytes.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# --------------------------------------------------------------------------
# Embedded 5x7 bitmap font (A-Z, 0-9, punctuation). Each glyph is 7 rows
# of 5 columns; 'X' = ink, '.' = empty.
# --------------------------------------------------------------------------
FONT_SRC = {
    "A": (".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"),
    "B": ("XXXX.", "X...X", "X...X", "XXXX.", "X...X", "X...X", "XXXX."),
    "C": (".XXXX", "X....", "X....", "X....", "X....", "X....", ".XXXX"),
    "D": ("XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."),
    "E": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"),
    "F": ("XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."),
    "G": (".XXXX", "X....", "X....", "X..XX", "X...X", "X...X", ".XXXX"),
    "H": ("X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"),
    "I": ("XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "XXXXX"),
    "J": ("..XXX", "...X.", "...X.", "...X.", "...X.", "X..X.", ".XX.."),
    "K": ("X...X", "X..X.", "X.X..", "XX...", "X.X..", "X..X.", "X...X"),
    "L": ("X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"),
    "M": ("X...X", "XX.XX", "X.X.X", "X.X.X", "X...X", "X...X", "X...X"),
    "N": ("X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"),
    "O": (".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "P": ("XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."),
    "Q": (".XXX.", "X...X", "X...X", "X...X", "X.X.X", "X..X.", ".XX.X"),
    "R": ("XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"),
    "S": (".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."),
    "T": ("XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."),
    "U": ("X...X", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."),
    "V": ("X...X", "X...X", "X...X", "X...X", "X...X", ".X.X.", "..X.."),
    "W": ("X...X", "X...X", "X...X", "X.X.X", "X.X.X", "XX.XX", "X...X"),
    "X": ("X...X", "X...X", ".X.X.", "..X..", ".X.X.", "X...X", "X...X"),
    "Y": ("X...X", "X...X", ".X.X.", "..X..", "..X..", "..X..", "..X.."),
    "Z": ("XXXXX", "....X", "...X.", "..X..", ".X...", "X....", "XXXXX"),
    "0": (".XXX.", "X...X", "X..XX", "X.X.X", "XX..X", "X...X", ".XXX."),
    "1": ("..X..", ".XX..", "..X..", "..X..", "..X..", "..X..", "XXXXX"),
    "2": (".XXX.", "X...X", "....X", "...X.", "..X..", ".X...", "XXXXX"),
    "3": ("XXXXX", "....X", "...X.", "..XX.", "....X", "X...X", ".XXX."),
    "4": ("...X.", "..XX.", ".X.X.", "X..X.", "XXXXX", "...X.", "...X."),
    "5": ("XXXXX", "X....", "XXXX.", "....X", "....X", "X...X", ".XXX."),
    "6": (".XXX.", "X....", "X....", "XXXX.", "X...X", "X...X", ".XXX."),
    "7": ("XXXXX", "....X", "...X.", "..X..", "..X..", "..X..", "..X.."),
    "8": (".XXX.", "X...X", "X...X", ".XXX.", "X...X", "X...X", ".XXX."),
    "9": (".XXX.", "X...X", "X...X", ".XXXX", "....X", "....X", ".XXX."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", "..X..", "..X.."),
    ",": (".....", ".....", ".....", ".....", ".....", "..X..", ".X..."),
    ":": (".....", ".....", "..X..", ".....", ".....", "..X..", "....."),
    "-": (".....", ".....", ".....", ".XXX.", ".....", ".....", "....."),
    "\u2212": (".....", ".....", ".....", ".XXX.", ".....", ".....", "....."),  # minus
    "\u2013": (".....", ".....", ".....", "XXXXX", ".....", ".....", "....."),  # en dash
    "\u2014": (".....", ".....", ".....", "XXXXX", ".....", ".....", "....."),  # em dash
    "'": ("..X..", "..X..", ".....", ".....", ".....", ".....", "....."),
    '"': (".X.X.", ".X.X.", ".....", ".....", ".....", ".....", "....."),
    "\u00b7": (".....", ".....", ".....", "..X..", ".....", ".....", "....."),  # middle dot
    "$": ("..X..", ".XXXX", "X.X..", ".XXX.", "..X.X", "XXXX.", "..X.."),
    "%": ("XX..X", "XX..X", "...X.", "..X..", ".X...", "X..XX", "X..XX"),
    "\u2265": ("X....", ".X...", "..X..", ".X...", "X....", ".....", "XXXXX"),  # >=
    "\u2192": (".....", "..X..", "...X.", "XXXXX", "...X.", "..X..", "....."),  # ->
    "<": ("...X.", "..X..", ".X...", "X....", ".X...", "..X..", "...X."),
    ">": (".X...", "..X..", "...X.", "....X", "...X.", "..X..", ".X..."),
    "/": ("....X", "....X", "...X.", "..X..", ".X...", "X....", "X...."),
    "!": ("..X..", "..X..", "..X..", "..X..", "..X..", ".....", "..X.."),
    "?": (".XXX.", "X...X", "....X", "...X.", "..X..", ".....", "..X.."),
    "(": ("...X.", "..X..", ".X...", ".X...", ".X...", "..X..", "...X."),
    ")": (".X...", "..X..", "...X.", "...X.", "...X.", "..X..", ".X..."),
    "+": (".....", "..X..", "..X..", "XXXXX", "..X..", "..X..", "....."),
    "~": (".....", ".....", ".X..X", "X.X.X", "X..X.", ".....", "....."),
    "=": (".....", ".....", "XXXXX", ".....", "XXXXX", ".....", "....."),
    "&": (".XX..", "X..X.", "X..X.", ".XX..", "X.X.X", "X..X.", ".XX.X"),
}

# Pre-parse glyphs into lists of (dx, dy) ink pixels.
FONT = {}
for _ch, _rows in FONT_SRC.items():
    _pts = []
    for _y, _row in enumerate(_rows):
        for _x, _c in enumerate(_row):
            if _c == "X":
                _pts.append((_x, _y))
    FONT[_ch] = _pts

# --------------------------------------------------------------------------
# Canvas + drawing primitives
# --------------------------------------------------------------------------
canvas = bytearray(W * H * 3)


def rect(x, y, w, h, c):
    """Filled axis-aligned rectangle, clipped to the canvas."""
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    stride = W * 3
    off = y0 * stride + x0 * 3
    for _ in range(y1 - y0):
        canvas[off:off + len(row)] = row
        off += stride


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        off = (y * W + x) * 3
        canvas[off] = c[0]
        canvas[off + 1] = c[1]
        canvas[off + 2] = c[2]


def line(x0, y0, x1, y1, c, t=1):
    """Thick Bresenham line (t = thickness in pixels)."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    half = t // 2
    while True:
        rect(x0 - half, y0 - half, t, t, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def disc(cx, cy, r, c):
    """Filled circle via scanlines."""
    for yy in range(max(0, cy - r), min(H, cy + r + 1)):
        d = r * r - (yy - cy) * (yy - cy)
        if d < 0:
            continue
        half = int(math.isqrt(d))
        rect(cx - half, yy, 2 * half + 1, 1, c)


def vgrad(x, y, w, h, c0, c1):
    """Vertical linear gradient from c0 (top) to c1 (bottom)."""
    for i in range(h):
        f = i / max(1, h - 1)
        c = (
            int(c0[0] + (c1[0] - c0[0]) * f),
            int(c0[1] + (c1[1] - c0[1]) * f),
            int(c0[2] + (c1[2] - c0[2]) * f),
        )
        rect(x, y + i, w, 1, c)


def text_width(s, scale, gap):
    if not s:
        return 0
    return len(s) * 5 * scale + (len(s) - 1) * gap


def fit_gap(s, scale, max_w):
    """Largest tracking (<= scale) that keeps the string inside max_w."""
    gap = scale
    while gap > 0 and text_width(s, scale, gap) > max_w:
        gap -= 1
    return gap


def draw_text(s, x, y, scale, c, gap=None, shadow=None):
    """Draw a string with the bitmap font. Uppercase-only; unknown -> space."""
    if gap is None:
        gap = scale
    s = s.upper()
    if shadow is not None:
        draw_text(s, x + max(2, scale // 2), y + max(2, scale // 2),
                  scale, shadow, gap)
    cx = x
    for ch in s:
        pts = FONT.get(ch)
        if pts:
            for dx, dy in pts:
                rect(cx + dx * scale, y + dy * scale, scale, scale, c)
        cx += 5 * scale + gap


def center_text(s, cx, y, scale, c, gap=None, shadow=None):
    if gap is None:
        gap = scale
    draw_text(s, cx - text_width(s, scale, gap) // 2, y, scale, c, gap, shadow)


def chip(x, y, s, scale, fg, bg, pad=14, gap=None):
    """Rounded-look stat chip; returns its width."""
    if gap is None:
        gap = scale
    w = text_width(s, scale, gap) + pad * 2
    h = 7 * scale + pad
    rect(x + 2, y, w - 4, h, bg)
    rect(x, y + 2, w, h - 4, bg)
    draw_text(s, x + pad, y + pad // 2, scale, fg, gap)
    return w


# Deterministic pseudo-random generator (fixed seed; no `random` module).
_lcg_state = 987654321


def rnd():
    global _lcg_state
    _lcg_state = (_lcg_state * 1103515245 + 12345) & 0x7FFFFFFF
    return _lcg_state


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
NAVY = (11, 18, 48)
INK = (8, 10, 20)
PANEL_BG = (22, 26, 44)
PANEL_EDGE = (62, 68, 100)
WHITE = (255, 255, 255)
GOLD = (244, 205, 94)
AMBER = (255, 208, 110)
RED = (255, 82, 82)
DARK_RED = (122, 22, 28)
TEAL = (72, 196, 182)
BLUE = (108, 156, 255)
SHADOW = (6, 8, 18)


# --------------------------------------------------------------------------
# Scene pieces
# --------------------------------------------------------------------------
def masthead():
    rect(0, 0, W, 110, NAVY)
    rect(0, 106, W, 4, GOLD)
    center_text("THE WORLD IN ONE DAY", W // 2, 16, 5, WHITE, shadow=SHADOW)
    center_text("FRIDAY, 20 NOVEMBER 2026", W // 2, 66, 3, GOLD)


def kyiv_scene():
    # Night sky gradient over the whole lead block.
    vgrad(0, 110, W, 286, (18, 26, 66), (5, 7, 20))

    # Stars (deterministic).
    for _ in range(110):
        sx = rnd() % W
        sy = 116 + rnd() % 190
        b = 120 + rnd() % 136
        px(sx, sy, (b, b, min(255, b + 20)))

    # Incoming missile streaks, upper right.
    line(986, 132, 716, 268, (255, 196, 140), 2)
    disc(716, 268, 3, (255, 236, 190))
    line(1016, 196, 836, 292, (255, 170, 120), 2)
    disc(836, 292, 3, (255, 226, 180))

    # Dnipro river.
    rect(0, 352, W, 44, (8, 12, 32))

    # Bridge silhouette: deck, towers, piers, cables.
    bridge = (12, 14, 28)
    rect(0, 344, W, 9, bridge)          # deck
    rect(0, 340, W, 2, (20, 24, 44))    # railing
    for tx in (230, 690):
        rect(tx, 262, 16, 90, bridge)               # tower
        rect(tx - 4, 258, 24, 6, bridge)            # cap
        rect(tx + 2, 353, 12, 39, bridge)           # pier
        top = (tx + 8, 264)
        for anchor in range(0, W + 1, 64):          # stay cables
            if abs(anchor - (tx + 8)) > 30:
                line(top[0], top[1], anchor, 342, (24, 30, 54), 1)
    # Main suspension cable sagging between the two towers.
    prev = None
    for i in range(41):
        fx = 238 + (698 - 238) * i / 40
        sag = 66 * (1 - ((i / 20) - 1) ** 2)
        fy = int(266 + sag)
        if prev is not None:
            line(prev[0], prev[1], int(fx), fy, (24, 30, 54), 2)
        prev = (int(fx), fy)

    # Explosion bursts on the bridge.
    burst(520, 336, 46)
    burst(845, 340, 24)

    # Orange reflection on the water under the main burst.
    for i in range(36):
        c = (150 - i * 3, 60 - i, 18)
        rect(478 + (i % 3) * 4, 356 + i, 84 - (i % 5) * 6, 1, c)

    # Headline + subhead + stat chips.
    draw_text("MISSILES OVER KYIV", 40, 126, 6, WHITE, shadow=SHADOW)
    draw_text("HOURS AFTER THE PEACE PHOTO", 40, 182, 3, AMBER)
    w1 = chip(40, 220, "5+ KILLED", 3, WHITE, DARK_RED)
    chip(40 + w1 + 16, 220, "3 BRIDGES HIT", 3, WHITE, (44, 48, 78))


def burst(cx, cy, r):
    """Orange explosion: rays + layered fireball."""
    for k in range(12):
        ang = k * math.pi / 6
        ln = r + 26 if k % 2 == 0 else r + 12
        line(cx + int(math.cos(ang) * r * 0.5),
             cy + int(math.sin(ang) * r * 0.5),
             cx + int(math.cos(ang) * ln),
             cy + int(math.sin(ang) * ln),
             (255, 120, 30), 3)
    disc(cx, cy, r, (224, 72, 18))
    disc(cx, cy, int(r * 0.72), (255, 140, 32))
    disc(cx, cy, int(r * 0.45), (255, 214, 92))
    disc(cx, cy, max(3, int(r * 0.2)), (255, 248, 214))


def peace_strip():
    y0 = 396
    rect(0, y0, W, 74, (24, 32, 64))
    rect(0, y0, W, 2, (70, 84, 130))
    rect(0, y0 + 72, W, 2, (70, 84, 130))

    # Three small flag bars side by side: US / Russia / China (64px total).
    fx = 44
    fy = 426
    # US: red/white stripes + blue canton.
    for i in range(7):
        rect(fx, fy + i * 2, 20, 2, (190, 44, 54) if i % 2 == 0 else (238, 238, 238))
    rect(fx, fy, 8, 8, (24, 34, 86))
    # Russia: white / blue / red horizontal bands.
    rect(fx + 22, fy, 20, 5, (238, 238, 238))
    rect(fx + 22, fy + 5, 20, 5, (44, 84, 186))
    rect(fx + 22, fy + 10, 20, 4, (206, 44, 54))
    # China: red field + one yellow star.
    rect(fx + 44, fy, 20, 14, (214, 44, 44))
    star = ("..X..", ".XXX.", "XXXXX", ".X.X.", "X...X")
    for sy, row in enumerate(star):
        for sx, ch in enumerate(row):
            if ch == "X":
                rect(fx + 44 + 5 + sx * 2, fy + 2 + sy * 2, 2, 2, (250, 220, 80))

    draw_text("PEACE IN SHENZHEN \u2014 TRUMP \u00b7 PUTIN \u00b7 XI",
              132, 404, 3, WHITE)
    draw_text("\u201cA NUCLEAR WAR CANNOT BE WON\u201d".replace("\u201c", "'").replace("\u201d", "'"),
              132, 434, 3, GOLD)


def gta_block():
    # Sunset gradient: pink -> orange -> purple.
    vgrad(0, 470, W, 90, (255, 116, 156), (255, 152, 64))
    vgrad(0, 560, W, 140, (255, 152, 64), (86, 38, 118))

    # Retro sun with slats, top right.
    disc(934, 524, 62, (255, 214, 112))

    def sunset_at(yy):
        if yy < 560:
            f = (yy - 470) / 89
            return (255, int(116 + (152 - 116) * f), int(156 + (64 - 156) * f))
        f = (yy - 560) / 139
        return (int(255 + (86 - 255) * f), int(152 + (38 - 152) * f),
                int(64 + (118 - 64) * f))

    for i, yy in enumerate(range(524, 586, 9)):
        rect(872, yy, 124, 3 + i // 2, sunset_at(yy))

    # Palm silhouette, bottom right.
    palm = (40, 16, 62)
    line(982, 700, 968, 612, palm, 7)
    top = (968, 612)
    for ang_deg in (200, 235, 265, 295, 330, 5):
        a = math.radians(ang_deg)
        line(top[0], top[1],
             top[0] + int(math.cos(a) * 52),
             top[1] + int(math.sin(a) * 34) + 14, palm, 4)

    draw_text("GTA VI SHATTERS RECORDS", 40, 482, 6, WHITE, shadow=(64, 18, 84))
    draw_text("$2.36B", 40, 538, 9, WHITE, shadow=(64, 18, 84))
    draw_text("24.6M COPIES", 408, 542, 4, WHITE, shadow=(64, 18, 84))
    draw_text("DAY ONE", 408, 580, 4, WHITE, shadow=(64, 18, 84))
    w1 = chip(40, 622, "METACRITIC 99", 3, WHITE, (44, 14, 66))
    chip(40 + w1 + 16, 622, "TWITCH PEAK 3.31M", 3, WHITE, (44, 14, 66))
    draw_text("MOST-WATCHED GAME IN TWITCH HISTORY", 40, 672, 3, (255, 232, 240))


def mini_panel(x, accent, title):
    y = 706
    h = 278
    rect(x, y, 241, h, PANEL_BG)
    rect(x, y, 241, 2, PANEL_EDGE)
    rect(x, y + h - 2, 241, 2, PANEL_EDGE)
    rect(x, y, 2, h, PANEL_EDGE)
    rect(x + 239, y, 2, h, PANEL_EDGE)
    rect(x + 2, y + 2, 237, 6, accent)
    g = fit_gap(title, 3, 225)
    draw_text(title, x + 8, y + 18, 3, accent, gap=g)
    return x + 8


def bottom_row():
    rect(0, 700, W, 290, (12, 14, 26))

    # --- Panel 1: Anthropic IPO ---
    ix = mini_panel(12, GOLD, "ANTHROPIC IPO")
    draw_text("$81.3B", ix, 752, 6, WHITE, gap=4)
    draw_text("BIGGEST EVER", ix, 806, 3, GOLD)
    draw_text("$83 PRICED", ix, 840, 3, WHITE, gap=2)
    draw_text("$111.50 OPEN", ix, 868, 3, WHITE, gap=2)
    draw_text("$97.17 CLOSE", ix, 896, 3, WHITE, gap=2)
    draw_text("~$2T VALUATION", ix, 930, 3, (176, 184, 214), gap=1)

    # --- Panel 2: Taiex ---
    ix = mini_panel(265, RED, "TAIEX \u00b7 TAIWAN")
    draw_text("\u22126.22%", ix, 752, 6, RED, gap=4)
    draw_text("WORST WEEK", ix, 806, 3, WHITE)
    draw_text("SINCE 1991", ix, 834, 3, WHITE)
    # Falling line chart.
    pts = [(0, 6), (28, 12), (55, 8), (83, 22), (110, 18),
           (138, 34), (166, 30), (193, 48), (221, 58)]
    base_y = 858
    # Label in the free wedge below the line's start, clear of line and text.
    draw_text("\u221217%+", ix, 888, 3, RED, gap=2)
    for i in range(len(pts) - 1):
        line(ix + pts[i][0], base_y + pts[i][1],
             ix + pts[i + 1][0], base_y + pts[i + 1][1], RED, 3)
    disc(ix + 221, base_y + 58, 4, RED)
    line(ix, base_y + 62, ix + 221, base_y + 62, (60, 66, 96), 1)
    draw_text("TSMC BRIEFLY", ix, 930, 3, (176, 184, 214))
    draw_text("BELOW NT$2,000", ix, 956, 3, (176, 184, 214), gap=1)

    # --- Panel 3: ICJ ---
    ix = mini_panel(518, TEAL, "WORLD COURT")
    draw_text("9\u20136", ix + 46, 750, 8, WHITE, gap=6)
    draw_text("MYANMAR:", ix, 820, 4, TEAL, gap=3)
    draw_text("GENOCIDE", ix, 854, 4, TEAL, gap=3)
    draw_text("ROHINGYA 2017", ix, 900, 3, WHITE, gap=2)
    draw_text("THE HAGUE", ix, 934, 3, (176, 184, 214))

    # --- Panel 4: UK-EU ---
    ix = mini_panel(771, BLUE, "UK\u2013EU DEAL")
    draw_text("100,000", ix, 752, 6, WHITE, gap=2)
    draw_text("YOUTH VISAS", ix, 806, 3, BLUE)
    draw_text("A YEAR", ix, 834, 3, BLUE)
    draw_text("AGES 18\u201331", ix, 868, 3, WHITE, gap=2)
    draw_text("UP TO 3 YEARS", ix, 896, 3, WHITE, gap=2)
    draw_text("STALLED OVER", ix, 930, 3, (176, 184, 214))
    draw_text("TUITION FEES", ix, 958, 3, (176, 184, 214))


def footer():
    rect(0, 990, W, 34, INK)
    rect(0, 990, W, 1, (48, 54, 84))
    s = ("SOURCES: CNN \u00b7 REUTERS \u00b7 AP \u00b7 SENSOR TOWER \u00b7 "
         "METACRITIC \u00b7 MORNINGSTAR \u00b7 BBC \u2014 20 NOV 2026")
    g = fit_gap(s, 2, W - 32)
    center_text(s, W // 2, 1001, 2, (172, 180, 204), gap=g)


# --------------------------------------------------------------------------
# PNG encoder (stdlib only)
# --------------------------------------------------------------------------
def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: None
        raw.extend(canvas[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    masthead()
    kyiv_scene()
    peace_strip()
    gta_block()
    bottom_row()
    footer()

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.png")
    with open(out_path, "wb") as f:
        f.write(encode_png())


if __name__ == "__main__":
    main()