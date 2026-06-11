import re

import pygame

from .constants import (
    BAR_BASE_COLOR,
    BAR_MID_COLOR,
    BAR_PEAK_COLOR,
    BAR_TICK_COLOR,
    COLOR_TERMINAL_BORDER,
    VISUAL_BASE_RATIO,
    VISUAL_PEAK_RATIO,
)


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def draw_stacked_bar(surface, x, base_y, height, peak_height, max_height, stem_width):
    x = int(x)
    base_y = int(base_y)
    bar_width = max(2, int(stem_width))
    bar_height = max(1, int(height))
    max_height = max(1, int(max_height))
    left = x - bar_width // 2

    base_h = min(bar_height, max(2, int(max_height * VISUAL_BASE_RATIO)))
    mid_h = max(0, bar_height - base_h)
    peak_h = min(mid_h, max(2, int(max_height * VISUAL_PEAK_RATIO))) if mid_h > 0 else 0
    body_h = max(0, mid_h - peak_h)

    pygame.draw.rect(surface, BAR_BASE_COLOR, pygame.Rect(left, base_y - base_h, bar_width, base_h))

    y = base_y - base_h
    if body_h > 0:
        pygame.draw.rect(surface, BAR_MID_COLOR, pygame.Rect(left, y - body_h, bar_width, body_h))
        y -= body_h
    if peak_h > 0:
        pygame.draw.rect(surface, BAR_PEAK_COLOR, pygame.Rect(left, y - peak_h, bar_width, peak_h))

    tick_y = base_y - int(max(peak_height, bar_height)) - 14
    if tick_y > 2:
        tick_w = max(3, min(bar_width, int(bar_width * 0.75)))
        tick_x = x - tick_w // 2
        pygame.draw.rect(surface, BAR_TICK_COLOR, pygame.Rect(tick_x, tick_y, tick_w, 2))


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
