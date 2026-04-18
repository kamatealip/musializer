import colorsys
import re

import pygame

from .constants import BAR_GRAD, COLOR_PANEL, COLOR_TERMINAL_BORDER


def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def bar_color(i, n, hue_shift=0.0):
    t = i / max(n - 1, 1)
    idx = t * (len(BAR_GRAD) - 1)
    lo = BAR_GRAD[int(idx)]
    hi = BAR_GRAD[min(int(idx) + 1, len(BAR_GRAD) - 1)]
    frac = idx - int(idx)
    h = lerp(lo[0], hi[0], frac) + hue_shift
    s = lerp(lo[1], hi[1], frac)
    v = lerp(lo[2], hi[2], frac)
    return hsv(h, s, v)


def brighten(color, amount=0.25):
    return tuple(min(255, int(channel + (255 - channel) * amount)) for channel in color)


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def draw_glow_ellipse(surface, color, center, sizes_and_alpha):
    glow = brighten(color, 0.35)
    cx, cy = int(center[0]), int(center[1])
    for width, height, alpha in sizes_and_alpha:
        if width <= 0 or height <= 0 or alpha <= 0:
            continue
        rect = pygame.Rect(0, 0, int(width), int(height))
        rect.center = (cx, cy)
        pygame.draw.ellipse(surface, with_alpha(glow, alpha), rect)


def draw_neon_bar(surface, glow_surface, x, base_y, top_y, color, stem_width):
    x = int(x)
    base_y = int(base_y)
    top_y = int(top_y)
    bright = brighten(color, 0.18)
    glow_width = max(stem_width + 8, stem_width * 4)
    mid_width = max(stem_width + 4, stem_width * 2 + 1)

    pygame.draw.line(glow_surface, with_alpha(color, 34), (x, base_y), (x, top_y), glow_width)
    pygame.draw.line(glow_surface, with_alpha(bright, 72), (x, base_y), (x, top_y), mid_width)
    pygame.draw.line(surface, bright, (x, base_y), (x, top_y), stem_width)

    cap_width = max(10, stem_width * 5)
    cap_height = max(6, int(cap_width * 0.62))
    draw_glow_ellipse(
        glow_surface,
        color,
        (x, top_y),
        [
            (cap_width + 20, cap_height + 14, 18),
            (cap_width + 12, cap_height + 8, 44),
            (cap_width + 4, cap_height + 2, 96),
        ],
    )

    cap_rect = pygame.Rect(0, 0, cap_width, cap_height)
    cap_rect.center = (x, top_y)
    pygame.draw.ellipse(surface, bright, cap_rect)

    highlight_rect = cap_rect.inflate(-max(2, stem_width), -max(2, stem_width // 2 + 1))
    if highlight_rect.width > 0 and highlight_rect.height > 0:
        pygame.draw.ellipse(surface, brighten(color, 0.42), highlight_rect)


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def trim_text(font, text, max_width):
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return text + ellipsis


def clean_filename(value, fallback="stream"):
    value = re.sub(r"[^\w\s-]", "", value, flags=re.ASCII).strip().replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    return value[:80] or fallback


def humanize_source(extractor_key):
    label = (extractor_key or "stream").replace("_", " ").strip()
    known = {
        "youtube": "YouTube",
        "youtu": "YouTube",
        "soundcloud": "SoundCloud",
        "generic": "Online stream",
    }
    return known.get(label.lower(), label.title())


def load_mono_font(size, bold=False):
    font_path = pygame.font.match_font(
        ["jetbrainsmono", "firacode", "consolas", "dejavu sans mono", "liberation mono"]
    )
    font = pygame.font.Font(font_path, size) if font_path else pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


def draw_terminal_panel(surface, rect, border_color=COLOR_TERMINAL_BORDER):
    pygame.draw.rect(surface, COLOR_PANEL, rect)
    pygame.draw.rect(surface, border_color, rect, 1)
