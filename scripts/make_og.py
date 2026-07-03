"""Generate the OG preview image for the Venezuela Earthquake Search bot.

Produces a 1200x630 PNG (Open Graph / Twitter Card standard) suitable
for being served as a static file by the FastAPI backend.

Run locally: python _make_og.py
Output: backend/frontend/og-preview.png
"""

from PIL import Image, ImageDraw, ImageFont
import os
import random

# Output dimensions — Open Graph / Twitter Card large image standard.
W, H = 1200, 630

# Brand palette (matches the site).
BG_TOP = (10, 21, 48)         # #0a1530
BG_BOT = (4, 10, 28)          # #040a1c
FLAG_YELLOW = (255, 206, 0)   # #FFCE00
FLAG_BLUE = (0, 51, 160)      # #0033A0
FLAG_RED = (239, 51, 64)      # #EF3340
GOLD = (255, 210, 63)         # #ffd23f
TEXT = (230, 237, 247)
MUTED = (154, 167, 194)


def find_font(candidates, size):
    """Return the first font that exists; fall back to PIL default."""
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_stars(draw, count, w, h, color=(214, 228, 255), seed=42):
    """Scatter tiny stars across the canvas (above and below the title)."""
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(20, w - 20)
        y = rng.randint(180, h - 60)  # avoid the title area roughly
        r = rng.choice([1, 1, 1, 2, 2, 3])
        alpha = rng.randint(140, 230)
        # Compose color with alpha via overlay; for simplicity just lighten/darken.
        c = tuple(int(v * (alpha / 255)) for v in color)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=c)


def draw_tricolor_ribbon(draw, w):
    """Top-of-image flag ribbon with the 8 stars of the Venezuelan flag."""
    h_band = 28
    # Yellow
    draw.rectangle((0, 0, w, h_band), fill=FLAG_YELLOW)
    # Blue (slightly taller, holds the 8 stars)
    blue_h = 40
    draw.rectangle((0, h_band, w, h_band + blue_h), fill=FLAG_BLUE)
    # Red
    draw.rectangle((0, h_band + blue_h, w, h_band + blue_h + h_band), fill=FLAG_RED)
    # 8 stars in an arc on the blue band
    star_path = [
        (0, -7), (1.6, -2.4), (6.5, -2.1), (2.7, 0.9),
        (4.0, 5.5), (0, 2.9), (-4.0, 5.5), (-2.7, 0.9),
        (-6.5, -2.1), (-1.6, -2.4), (0, -7),
    ]
    cx = w / 2
    cy = h_band + blue_h / 2
    arc_w = 360
    for i in range(8):
        t = (i + 0.5) / 8 - 0.5  # -0.5 .. 0.5
        ox = cx + t * arc_w
        oy = cy + abs(t) * 14
        pts = [(cx0 + ox, cy0 + oy) for cx0, cy0 in star_path]
        draw.polygon(pts, fill=(255, 255, 255))


def draw_title(draw, w, h, font_title, font_subtitle, font_url, lang="es"):
    if lang == "es":
        line1 = "Búsqueda Terremoto"
        line2 = "Venezuela"
        sub = "Busca personas desaparecidas en 13 plataformas oficiales y comunitarias"
        url = "vzla-search-bot.onrender.com"
        below = "Sin instalación · Bilingüe ES/EN"
    else:
        line1 = "Venezuela Earthquake"
        line2 = "Search"
        sub = "Search for missing persons across 13 official and community platforms"
        url = "vzla-search-bot.onrender.com"
        below = "No install · Bilingual ES/EN"

    # Title — two lines, centered.
    cy_title = h / 2 - 30
    # Outline a soft glow behind the title by drawing it multiple times with low alpha.
    for _ in range(3):
        bbox1 = draw.textbbox((0, 0), line1, font=font_title)
        bbox2 = draw.textbbox((0, 0), line2, font=font_title)
        w1 = bbox1[2] - bbox1[0]
        w2 = bbox2[2] - bbox2[0]
        draw.text(((w - w1) / 2, cy_title - 100), line1, font=font_title, fill=GOLD)
        draw.text(((w - w2) / 2, cy_title - 10), line2, font=font_title, fill=TEXT)

    # Subtitle.
    bbox = draw.textbbox((0, 0), sub, font=font_subtitle)
    sub_w = bbox[2] - bbox[0]
    draw.text(
        ((w - sub_w) / 2, cy_title + 80),
        sub,
        font=font_subtitle,
        fill=MUTED,
    )

    # URL.
    bbox = draw.textbbox((0, 0), url, font=font_url)
    url_w = bbox[2] - bbox[0]
    draw.text(
        ((w - url_w) / 2, h - 70),
        url,
        font=font_url,
        fill=GOLD,
    )

    # Below-URL hint.
    bbox = draw.textbbox((0, 0), below, font=font_subtitle)
    bw = bbox[2] - bbox[0]
    draw.text(
        ((w - bw) / 2, h - 36),
        below,
        font=font_subtitle,
        fill=MUTED,
    )


def render(lang="es"):
    img = Image.new("RGB", (W, H), BG_BOT)
    draw = ImageDraw.Draw(img)

    # Vertical gradient background.
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
        draw.line((0, y, W, y), fill=(r, g, b))

    # Stars.
    draw_stars(draw, 110, W, H, color=(214, 228, 255), seed=42)
    draw_stars(draw, 24, W, H, color=(255, 214, 60), seed=137)

    # Top flag ribbon with 8 stars.
    draw_tricolor_ribbon(draw, W)

    # Fonts (Windows-friendly, Render deployment just serves the PNG).
    title_font = find_font(
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ],
        88,
    )
    sub_font = find_font(
        [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        28,
    )
    url_font = find_font(
        [
            "C:/Windows/Fonts/consolab.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        ],
        30,
    )

    draw_title(draw, W, H, title_font, sub_font, url_font, lang=lang)

    return img


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)  # scripts/ is at repo root
    out_dir = os.path.join(repo_root, "backend", "frontend")
    os.makedirs(out_dir, exist_ok=True)

    # Spanish (primary — matches default lang).
    img_es = render(lang="es")
    out_es = os.path.join(out_dir, "og-preview.png")
    img_es.save(out_es, "PNG", optimize=True)
    print(f"Wrote {out_es}  ({img_es.size[0]}x{img_es.size[1]})")

    # English fallback — useful if a crawler requests /og-preview-en.png.
    img_en = render(lang="en")
    out_en = os.path.join(out_dir, "og-preview-en.png")
    img_en.save(out_en, "PNG", optimize=True)
    print(f"Wrote {out_en}  ({img_en.size[0]}x{img_en.size[1]})")


if __name__ == "__main__":
    main()