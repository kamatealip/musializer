import colorsys
import math
import re

import pygame

from .constants import BAR_GRAD, COLOR_TERMINAL_BORDER


def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def clamp01(value):
    return max(0.0, min(1.0, value))


def bar_color(i, n, hue_shift=0.0, time_phase=0.0):
    t = i / max(n - 1, 1)
    idx = t * (len(BAR_GRAD) - 1)
    lo = BAR_GRAD[int(idx)]
    hi = BAR_GRAD[min(int(idx) + 1, len(BAR_GRAD) - 1)]
    frac = idx - int(idx)
    base_h = lerp(lo[0], hi[0], frac)
    base_s = lerp(lo[1], hi[1], frac)
    base_v = lerp(lo[2], hi[2], frac)

    # Create a subtle animated gradient wave that moves across the whole bar field.
    wave_primary = math.sin(time_phase * 1.15 + t * math.tau * 1.55)
    wave_secondary = math.sin(time_phase * 0.72 - t * math.tau * 2.25 + 0.9)
    hue_wave = wave_primary * 0.014 + wave_secondary * 0.008
    saturation_wave = wave_secondary * 0.045 + wave_primary * 0.02
    value_wave = wave_primary * 0.06 + wave_secondary * 0.025

    h = base_h + hue_shift + hue_wave
    s = clamp01(base_s + saturation_wave)
    v = clamp01(base_v + value_wave)
    return hsv(h, s, v)


def brighten(color, amount=0.25):
    return tuple(min(255, int(channel + (255 - channel) * amount)) for channel in color)


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def draw_neon_bar(surface, glow_surface, x, base_y, top_y, color, stem_width):
    x = int(x)
    base_y = int(base_y)
    top_y = int(top_y)
    bar_width = max(2, int(stem_width))
    bar_height = max(4, base_y - top_y)
    radius = min(10, max(1, bar_width // 2 + 1))
    left = x - bar_width // 2
    rect = pygame.Rect(left, base_y - bar_height, bar_width, bar_height)

    bright = brighten(color, 0.32)
    hottest = brighten(color, 0.58)

    for inflate_x, inflate_y, alpha in ((26, 18, 18), (16, 10, 38), (8, 4, 76)):
        glow_rect = rect.inflate(inflate_x, inflate_y)
        pygame.draw.rect(
            glow_surface,
            with_alpha(bright, alpha),
            glow_rect,
            border_radius=max(radius, radius + inflate_x // 6),
        )

    pygame.draw.rect(surface, color, rect, border_radius=radius)

    inner_rect = rect.inflate(-max(2, bar_width // 3), -max(2, bar_width // 4))
    if inner_rect.width > 0 and inner_rect.height > 0:
        pygame.draw.rect(
            surface,
            bright,
            inner_rect,
            border_radius=max(2, radius - 1),
        )

    highlight_width = max(1, bar_width // 4)
    highlight_x = rect.x + 1 if rect.w > 3 else rect.x
    highlight_rect = pygame.Rect(
        highlight_x,
        rect.y + 1,
        max(1, min(highlight_width, rect.right - highlight_x)),
        max(1, rect.h - 2),
    )
    pygame.draw.rect(
        surface,
        hottest,
        highlight_rect,
        border_radius=max(2, radius - 2),
    )


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
    draw_terminal_panel_box(surface, rect, border_color=border_color)


def draw_terminal_panel_box(
    surface,
    rect,
    border_color=COLOR_TERMINAL_BORDER,
    fill_color=(8, 4, 7, 232),
    radius=18,
    glow_alpha=26,
):
    if glow_alpha > 0:
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for pad, alpha in ((18, glow_alpha // 2), (10, glow_alpha), (4, glow_alpha + 10)):
            glow_rect = rect.inflate(pad * 2, pad * 2)
            pygame.draw.rect(
                glow,
                with_alpha(border_color, alpha),
                glow_rect,
                1,
                border_radius=radius + pad,
            )
        surface.blit(glow, (0, 0))

    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    panel_rect = panel.get_rect()
    pygame.draw.rect(panel, fill_color, panel_rect, border_radius=radius)
    pygame.draw.rect(panel, with_alpha(border_color, 150), panel_rect, 1, border_radius=radius)

    highlight = pygame.Rect(1, 1, max(0, rect.w - 2), max(14, rect.h // 5))
    if highlight.width > 0 and highlight.height > 0:
        pygame.draw.rect(
            panel,
            with_alpha(border_color, 22),
            highlight,
            border_radius=max(6, radius - 4),
        )

    surface.blit(panel, rect.topleft)
