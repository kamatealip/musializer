import re

import pygame

from .constants import BAR_GRAD, COLOR_TERMINAL_BORDER


def bar_color(i, n, hue_shift=0.0, time_phase=0.0):
    del hue_shift, time_phase
    if len(BAR_GRAD) == 1:
        return BAR_GRAD[0]

    t = i / max(n - 1, 1)
    scaled = t * (len(BAR_GRAD) - 1)
    lo_idx = int(scaled)
    hi_idx = min(lo_idx + 1, len(BAR_GRAD) - 1)
    mix = scaled - lo_idx
    lo = BAR_GRAD[lo_idx]
    hi = BAR_GRAD[hi_idx]
    return tuple(int(lo[channel] + (hi[channel] - lo[channel]) * mix) for channel in range(3))


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def draw_neon_bar(surface, x, base_y, top_y, color, stem_width):
    x = int(x)
    base_y = int(base_y)
    top_y = int(top_y)
    bar_width = max(2, int(stem_width))
    bar_height = max(4, base_y - top_y)
    left = x - bar_width // 2
    rect = pygame.Rect(left, base_y - bar_height, bar_width, bar_height)
    pygame.draw.rect(surface, color, rect)


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
    radius=0,
    glow_alpha=26,
):
    del radius, glow_alpha
    clipped_rect = pygame.Rect(rect).clip(surface.get_rect())
    if clipped_rect.width <= 0 or clipped_rect.height <= 0:
        return

    panel = pygame.Surface((clipped_rect.w, clipped_rect.h), pygame.SRCALPHA)
    panel_rect = panel.get_rect()
    pygame.draw.rect(panel, fill_color, panel_rect)

    border_rect = panel_rect.inflate(-2, -2)
    if border_rect.width <= 0 or border_rect.height <= 0:
        border_rect = panel_rect.copy()
    pygame.draw.rect(panel, with_alpha(border_color, 180), border_rect, 1)

    surface.blit(panel, clipped_rect.topleft)
