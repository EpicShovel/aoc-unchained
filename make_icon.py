#!/usr/bin/env python3
"""make_icon.py - generate chat_color.ico for the app identity.

A one-shot dev helper (not shipped in the build). Draws a dark rounded tile
with a gold chat bubble and three colored "text lines" inside, then writes a
multi-resolution .ico so the .exe has a real identity in Explorer /
SmartScreen (generic PyInstaller icons are an AV-heuristic trigger).

Needs Pillow at BUILD TIME only (the shipped app stays stdlib-only).

1.0.0 - initial icon generator.
"""
from __future__ import annotations

__version__ = "1.0.0"

import os

from PIL import Image, ImageDraw

# Palette (matches the app theme)
BG_TOP = (26, 26, 38)      # #1a1a26 panel
BG_BOT = (10, 10, 16)      # #0a0a10 window bg
BORDER = (201, 162, 75)    # #c9a24b gold
BUBBLE = (232, 200, 119)   # #e8c877 gold highlight
RED = (255, 69, 0)
GREEN = (0, 255, 0)
BLUE = (0, 120, 255)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def _rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def build(size: int) -> Image.Image:
    ss = 4  # supersample for crisp edges
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # dark tile with subtle vertical gradient
    tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    for y in range(S):
        td.line([(0, y), (S, y)], fill=_lerp(BG_TOP, BG_BOT, y / S) + (255,))
    mask = _rounded_mask(S, int(S * 0.18))
    img.paste(tile, (0, 0), mask)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.18),
                        outline=BORDER + (255,), width=max(2, S // 128))

    # chat bubble
    bx0, by0 = int(S * 0.16), int(S * 0.22)
    bx1, by1 = int(S * 0.84), int(S * 0.66)
    bw = max(2, S // 64)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(S * 0.10),
                        outline=BUBBLE + (255,), width=bw)
    # bubble tail
    d.polygon(
        [(int(S * 0.34), by1 - 1), (int(S * 0.30), int(S * 0.80)),
         (int(S * 0.46), by1 - 1)],
        fill=BUBBLE + (255,),
    )

    # three colored "text lines" inside the bubble
    lines = [(RED, 0.62), (GREEN, 0.78), (BLUE, 0.50)]
    y = int(S * 0.33)
    for color, frac in lines:
        x0 = int(S * 0.25)
        x1 = x0 + int((bx1 - bx0) * frac) - int(S * 0.10)
        d.rounded_rectangle([x0, y, x1, y + int(S * 0.06)],
                            radius=int(S * 0.03), fill=color + (255,))
        y += int(S * 0.12)

    return img.resize((size, size), Image.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "chat_color.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [build(s) for s in sizes]
    imgs[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes],
                  append_images=imgs[:-1])
    print("wrote", out)


if __name__ == "__main__":
    main()
