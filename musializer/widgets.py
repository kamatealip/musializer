import pygame

from .constants import (
    COLOR_ACCENT_SOFT,
    COLOR_CTRL,
    COLOR_CTRL_HOVER,
    COLOR_TERMINAL_BORDER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
)
from .visuals import draw_terminal_panel_box


class Button:
    def __init__(self, label, x, y, w, h, key_hint=""):
        self.label = label
        self.rect = pygame.Rect(x, y, w, h)
        self.key_hint = key_hint
        self.hovered = False

    def update_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def check_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def draw(self, surface, font, font_hint):
        color = COLOR_CTRL_HOVER if self.hovered else COLOR_CTRL
        border = COLOR_ACCENT_SOFT if self.hovered else COLOR_TERMINAL_BORDER
        draw_terminal_panel_box(
            surface,
            self.rect,
            border_color=border,
            fill_color=(color[0], color[1], color[2], 242),
            radius=12,
            glow_alpha=18 if self.hovered else 8,
        )

        txt = font.render(self.label, True, COLOR_TEXT)
        tx = self.rect.centerx - txt.get_width() // 2
        ty = self.rect.centery - txt.get_height() // 2
        surface.blit(txt, (tx, ty))

        if self.key_hint:
            hint = font_hint.render(self.key_hint, True, COLOR_TEXT_DIM)
            surface.blit(hint, (self.rect.centerx - hint.get_width() // 2, self.rect.bottom + 4))

    def is_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )
