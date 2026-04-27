import re

import pygame

from .constants import COLOR_TERMINAL_BORDER


def bar_color(i, n, hue_shift=0.0, time_phase=0.0):
    return COLOR_TERMINAL_BORDER


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def draw_neon_bar(surface, glow_surface, x, base_y, top_y, color, stem_width):
    del glow_surface
    x = int(x)
    base_y = int(base_y)
    top_y = int(top_y)
    bar_width = max(2, int(stem_width))
    bar_height = max(4, base_y - top_y)
    radius = min(8, max(1, bar_width // 2 + 1))
    left = x - bar_width // 2
    rect = pygame.Rect(left, base_y - bar_height, bar_width, bar_height)
    pygame.draw.rect(surface, color, rect, border_radius=radius)


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
