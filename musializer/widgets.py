import pygame

from .constants import COLOR_CTRL, COLOR_CTRL_HOVER, COLOR_TEXT, COLOR_TEXT_DIM


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
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (80, 80, 100), self.rect, 1, border_radius=8)

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
