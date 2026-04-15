import pygame
import numpy as np
import librosa
import os
import sys
import threading
import cv2
import colorsys
from datetime import timedelta

# ───────────────── CONFIG ─────────────────
FPS = 60
MAX_BARS = 128
BAR_GAP = 3

SPRING = 0.2
DAMPING = 0.8

COLOR_BG = (10, 10, 14)
COLOR_TEXT = (230, 230, 230)
COLOR_TEXT_DIM = (120, 120, 120)
COLOR_ACCENT = (255, 60, 120)
COLOR_CTRL = (50, 50, 60)
COLOR_CTRL_HOVER = (80, 80, 95)

SUPPORTED_FORMATS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".webm", ".opus", ".mp4"}
SKIP_SECONDS = 10

BAR_GRAD = [
    (0.78, 1.0, 0.95),
    (0.62, 1.0, 1.00),
    (0.50, 1.0, 1.00),
    (0.38, 1.0, 1.00),
    (0.10, 1.0, 1.00),
    (0.96, 1.0, 0.95),
]

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

# ───────────────── VIDEO RENDERER ─────────────────
class VideoRenderer:
    def __init__(self, w, h, fps):
        self.w = w
        self.h = h
        self.fps = fps
        self.frame = 0
        self.total = 0
        self.writer = None

    def start(self, path, duration):
        self.total = int(duration * self.fps)
        self.writer = cv2.VideoWriter(
            path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (self.w, self.h)
        )
        self.frame = 0
        print(f"[RENDER] START → {path}")

    def write(self, surface):
        frame = pygame.surfarray.array3d(surface).transpose(1, 0, 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        if frame.shape[:2] != (self.h, self.w):
            frame = cv2.resize(frame, (self.w, self.h))
        self.writer.write(frame)
        self.frame += 1

    def stop(self):
        self.writer.release()
        print("[RENDER] COMPLETE ✔")


# ───────────────── BUTTON ─────────────────
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


# ───────────────── VISUALIZER ─────────────────
class AudioVisualizer:
    def __init__(self, start_path=None):
        pygame.init()
        pygame.mixer.init(44100, -16, 2, 512)

        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        pygame.display.set_caption("Minimal Audio Visualizer")

        self.clock = pygame.time.Clock()
        self.running = True

        self.font = pygame.font.SysFont("Segoe UI", 18)
        self.font_big = pygame.font.SysFont("Segoe UI", 36, bold=True)
        self.font_hint = pygame.font.SysFont("Segoe UI", 13)

        self.file = None
        self.spec = None
        self.times = None
        self.duration = 0

        self.active_bars = 64
        self.heights = np.zeros(MAX_BARS)
        self.velocity = np.zeros(MAX_BARS)

        self.start_ticks = 0
        self.pause_time = 0.0
        self.paused = False
        self.current_time = 0.0

        self.renderer = None
        self.rendering = False

        BW, BH = 115, 38
        self.btn_prev = Button("◀◀  -10s", 0, 0, BW, BH, key_hint="← / A")
        self.btn_play = Button("▶  Play",  0, 0, BW, BH, key_hint="Space")
        self.btn_next = Button("▶▶  +10s", 0, 0, BW, BH, key_hint="→ / D")

        self.playlist_dir = None
        self.playlist = []
        self.playlist_index = 0
        self.playlist_cursor = 0
        self.playlist_scroll = 0
        self.show_playlist = False

        if start_path:
            if os.path.isdir(start_path):
                self.load_playlist(start_path)
            elif os.path.isfile(start_path):
                self.load_playlist(os.path.dirname(start_path), start_file=start_path)

    # ───────── SEEK ─────────
    def seek(self, t):
        """Reliable cross-platform seek: stop → rewind → play from t."""
        t = max(0.0, min(float(t), self.duration))
        pygame.mixer.music.stop()
        pygame.mixer.music.play(start=t)          # works on most backends
        self.start_ticks = pygame.time.get_ticks() - int(t * 1000)
        self.pause_time = t
        self.current_time = t
        if self.paused:
            pygame.mixer.music.pause()

    def skip(self, delta):
        self.seek(self.current_time + delta)

    # ───────── TOGGLE PAUSE ─────────
    def toggle_pause(self):
        if self.spec is None:
            return
        if not self.paused:
            pygame.mixer.music.pause()
            self.pause_time = self.current_time
            self.paused = True
            self.btn_play.label = "⏸  Pause"
        else:
            pygame.mixer.music.unpause()
            self.start_ticks = pygame.time.get_ticks() - int(self.pause_time * 1000)
            self.paused = False
            self.btn_play.label = "▶  Play"

    # ───────── AUDIO LOAD ─────────
    def analyze(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            print(f"[SKIP] Unsupported format: {ext}")
            print(f"       Supported: {', '.join(sorted(SUPPORTED_FORMATS))}")
            return

        print(f"[LOAD] {os.path.basename(path)}")

        y, sr = librosa.load(path, sr=None, mono=True)
        self.duration = librosa.get_duration(y=y, sr=sr)

        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=MAX_BARS, hop_length=512)
        self.spec = librosa.power_to_db(mel, ref=np.max)
        self.times = librosa.frames_to_time(
            np.arange(self.spec.shape[1]), sr=sr, hop_length=512
        )

        self.file = path
        self.heights.fill(0)
        self.velocity.fill(0)

        pygame.mixer.music.load(path)
        pygame.mixer.music.play()

        self.start_ticks = pygame.time.get_ticks()
        self.pause_time = 0.0
        self.paused = False
        self.btn_play.label = "▶  Play"

        print("[READY]  Space=Pause  ←/→=±10s  R=Render  L=Playlist  ESC=Exit")

    def get_supported_files(self, directory):
        files = []
        try:
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if os.path.isfile(path) and os.path.splitext(name)[1].lower() in SUPPORTED_FORMATS:
                    files.append(path)
        except OSError:
            pass
        return files

    def load_playlist(self, directory, start_file=None):
        self.playlist_dir = directory
        self.playlist = self.get_supported_files(directory)
        self.playlist_index = 0
        self.playlist_cursor = 0
        self.playlist_scroll = 0

        if start_file and start_file in self.playlist:
            self.playlist_index = self.playlist.index(start_file)
            self.playlist_cursor = self.playlist_index
        elif not self.playlist:
            print(f"[PLAYLIST] No supported tracks found in {directory}")

        if self.playlist:
            self.analyze(self.playlist[self.playlist_index])

    def toggle_playlist(self):
        if not self.playlist:
            return
        self.show_playlist = not self.show_playlist
        if self.show_playlist:
            self.playlist_cursor = self.playlist_index
            self.playlist_scroll = max(0, self.playlist_cursor - 5)

    def move_playlist_cursor(self, delta):
        if not self.playlist:
            return
        self.playlist_cursor = (self.playlist_cursor + delta) % len(self.playlist)
        visible = 10
        if self.playlist_cursor < self.playlist_scroll:
            self.playlist_scroll = self.playlist_cursor
        elif self.playlist_cursor >= self.playlist_scroll + visible:
            self.playlist_scroll = self.playlist_cursor - visible + 1

    def select_playlist_item(self):
        if not self.playlist:
            return
        self.playlist_index = self.playlist_cursor
        self.show_playlist = False
        self.analyze(self.playlist[self.playlist_index])

    def spectrum_at(self, t):
        idx = np.searchsorted(self.times, t)
        idx = min(idx, len(self.times) - 1)
        frame = self.spec[:, idx]
        frame = np.clip((frame + 80) / 80, 0, 1) ** 0.65
        return frame[:self.active_bars]

    # ───────── UPDATE ─────────
    def update(self):
        if self.spec is None:
            return

        if self.rendering:
            t = self.renderer.frame / FPS
            if t >= self.duration:
                self.renderer.stop()
                self.rendering = False
                return
        else:
            if self.paused:
                t = self.pause_time
            else:
                t = (pygame.time.get_ticks() - self.start_ticks) / 1000.0

        self.current_time = min(max(t, 0.0), self.duration)

        data = self.spectrum_at(self.current_time)
        max_h = self.screen.get_height() * 0.60

        for i in range(self.active_bars):
            target = data[i] * max_h
            force = (target - self.heights[i]) * SPRING
            self.velocity[i] = (self.velocity[i] + force) * DAMPING
            self.heights[i] += self.velocity[i]

    # ───────── DRAW ─────────
    def draw(self):
        self.screen.fill(COLOR_BG)
        w, h = self.screen.get_size()
        mx, my = pygame.mouse.get_pos()

        if self.spec is None:
            txt = self.font_big.render("DROP AUDIO FILE", True, COLOR_TEXT)
            self.screen.blit(txt, (w // 2 - txt.get_width() // 2, h // 2 - 30))
            lines = [
                "Supported: MP3 · WAV · OGG · FLAC · AAC · M4A · MP4 · WebM · Opus",
                "Space = Play/Pause     ← / A = −10s     → / D = +10s     R = Render     ESC = Quit",
            ]
            for i, line in enumerate(lines):
                s = self.font_hint.render(line, True, COLOR_TEXT_DIM)
                self.screen.blit(s, (w // 2 - s.get_width() // 2, h // 2 + 20 + i * 22))
            pygame.display.flip()
            return

        # ── Bars ──
        bar_area_w = w - 120
        bar_w = bar_area_w / self.active_bars
        base_y = h * 0.68

        hue_shift = (pygame.time.get_ticks() / 1000.0) * 0.06
        for i in range(self.active_bars):
            bh = self.heights[i]
            if bh < 1:
                continue
            color = bar_color(i, self.active_bars, hue_shift)
            pygame.draw.rect(
                self.screen, color,
                (60 + i * bar_w, base_y - bh, bar_w - BAR_GAP, bh),
                border_radius=8
            )

        # ── Progress bar ──
        prog_y = h - 95
        prog_x = 60
        prog_w = w - 120
        prog_h = 5
        prog_rect = pygame.Rect(prog_x, prog_y - 6, prog_w, prog_h + 12)

        pygame.draw.rect(self.screen, (40, 40, 40), (prog_x, prog_y, prog_w, prog_h), border_radius=3)

        progress = self.current_time / self.duration if self.duration > 0 else 0
        fill = int(prog_w * progress)
        if fill > 0:
            pygame.draw.rect(self.screen, COLOR_ACCENT, (prog_x, prog_y, fill, prog_h), border_radius=3)

        # Highlight on hover
        if prog_rect.collidepoint(mx, my):
            pygame.draw.rect(self.screen, (255, 255, 255), (prog_x, prog_y, prog_w, prog_h), 1, border_radius=3)

        # Timestamp
        time_txt = (
            f"{timedelta(seconds=int(self.current_time))} / "
            f"{timedelta(seconds=int(self.duration))}"
        )
        ts = self.font.render(time_txt, True, COLOR_TEXT_DIM)
        self.screen.blit(ts, (w // 2 - ts.get_width() // 2, prog_y - 24))

        # ── Control buttons ──
        BW, BH = 115, 38
        gap = 14
        total_ctrl = 3 * BW + 2 * gap
        bx = w // 2 - total_ctrl // 2
        by = h - 60

        self.btn_prev.update_pos(bx, by)
        self.btn_play.update_pos(bx + BW + gap, by)
        self.btn_next.update_pos(bx + 2 * (BW + gap), by)

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.check_hover(mx, my)
            btn.draw(self.screen, self.font, self.font_hint)

        # ── Render overlay ──
        if self.rendering:
            pct = int(self.renderer.frame / max(self.renderer.total, 1) * 100)
            ov = self.font.render(f"● RENDERING  {pct}%", True, COLOR_ACCENT)
            self.screen.blit(ov, (w - ov.get_width() - 16, 12))

        if self.show_playlist:
            overlay_w = w - 120
            overlay_h = min(h - 120, 520)
            overlay = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 220))
            pygame.draw.rect(overlay, (40, 42, 52), (0, 0, overlay_w, overlay_h), border_radius=14)

            title = self.font_big.render("Playlist", True, COLOR_TEXT)
            overlay.blit(title, (24, 18))
            help_text = self.font_hint.render(
                "L / Esc = Close   ↑ / ↓ = Navigate   Enter = Play", True, COLOR_TEXT_DIM
            )
            overlay.blit(help_text, (24, 64))

            visible_lines = 10
            for idx in range(self.playlist_scroll, min(len(self.playlist), self.playlist_scroll + visible_lines)):
                name = os.path.basename(self.playlist[idx])
                prefix = "▶ " if idx == self.playlist_index else "   "
                color = COLOR_ACCENT if idx == self.playlist_cursor else COLOR_TEXT
                item = self.font.render(f"{prefix}{idx + 1:02d}. {name}", True, color)
                overlay.blit(item, (24, 104 + (idx - self.playlist_scroll) * 32))

            self.screen.blit(overlay, (60, 40))

        pygame.display.flip()

        if self.rendering:
            self.renderer.write(self.screen)

    # ───────── RUN ─────────
    def run(self):
        print("MINIMAL VISUALIZER READY — drop an audio/video file onto the window. Press L to open the playlist.")

        while self.running:
            for e in pygame.event.get():

                # ── Quit ──
                if e.type == pygame.QUIT:
                    self.running = False

                # ── Drop file ──
                elif e.type == pygame.DROPFILE and not self.rendering:
                    threading.Thread(target=self.analyze, args=(e.file,), daemon=True).start()

                # ── Keyboard  (checked independently — NOT elif) ──
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_l and self.playlist:
                        self.toggle_playlist()
                    elif self.show_playlist:
                        if e.key in (pygame.K_ESCAPE, pygame.K_l):
                            self.show_playlist = False
                        elif e.key == pygame.K_UP:
                            self.move_playlist_cursor(-1)
                        elif e.key == pygame.K_DOWN:
                            self.move_playlist_cursor(1)
                        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.select_playlist_item()
                    else:
                        if e.key == pygame.K_ESCAPE:
                            self.running = False

                        elif e.key == pygame.K_SPACE:
                            self.toggle_pause()

                        elif e.key in (pygame.K_LEFT, pygame.K_a) and self.spec is not None:
                            self.skip(-SKIP_SECONDS)

                        elif e.key in (pygame.K_RIGHT, pygame.K_d) and self.spec is not None:
                            self.skip(SKIP_SECONDS)

                        elif e.key == pygame.K_r and self.spec is not None and not self.rendering:
                            out = os.path.splitext(self.file)[0] + "_viz.mp4"
                            self.renderer = VideoRenderer(1920, 1080, FPS)
                            self.renderer.start(out, self.duration)
                            self.rendering = True

                # ── Mouse clicks (also independent) ──
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    w, h = self.screen.get_size()
                    prog_x, prog_y = 60, h - 95
                    prog_w = w - 120

                    # Progress bar seek
                    if self.spec is not None and pygame.Rect(prog_x, prog_y - 6, prog_w, 17).collidepoint(e.pos):
                        ratio = (e.pos[0] - prog_x) / prog_w
                        self.seek(ratio * self.duration)

                    # Buttons
                    elif self.spec is not None:
                        if self.btn_prev.is_clicked(e):
                            self.skip(-SKIP_SECONDS)
                        elif self.btn_play.is_clicked(e):
                            self.toggle_pause()
                        elif self.btn_next.is_clicked(e):
                            self.skip(SKIP_SECONDS)

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        print("[EXIT]")


if __name__ == "__main__":
    start_path = sys.argv[1] if len(sys.argv) > 1 else None
    AudioVisualizer(start_path).run()