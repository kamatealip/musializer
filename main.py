import pygame
import numpy as np
import librosa
import os
import sys
import threading
import cv2
import colorsys
import math
import shutil
import subprocess
import tempfile
import re
from datetime import timedelta
from urllib.parse import urlparse

# ───────────────── CONFIG ─────────────────
FPS = 60
MAX_BARS = 128
BAR_GAP = 1

SPRING = 0.16
DAMPING = 0.95

COLOR_BG = (6, 10, 7)
COLOR_TEXT = (190, 255, 210)
COLOR_TEXT_DIM = (98, 150, 113)
COLOR_ACCENT = (102, 255, 153)
COLOR_ACCENT_SOFT = (70, 185, 255)
COLOR_CTRL = (17, 28, 19)
COLOR_CTRL_HOVER = (22, 38, 26)
COLOR_PANEL = (9, 14, 10)
COLOR_PANEL_ALT = (13, 20, 14)
COLOR_SUCCESS = (102, 255, 153)
COLOR_WARNING = (255, 210, 120)
COLOR_ERROR = (255, 120, 120)
COLOR_TERMINAL_BG = (9, 13, 10)
COLOR_TERMINAL_BORDER = (86, 214, 132)
COLOR_TERMINAL_TEXT = (188, 255, 208)
COLOR_TERMINAL_DIM = (104, 164, 121)

SUPPORTED_FORMATS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".webm", ".opus", ".mp4"}
SKIP_SECONDS = 10
STREAM_CACHE_DIR = os.path.join(tempfile.gettempdir(), "musializer_streams")
STREAM_QUERY_PREFIX = "ytsearch1:"
STATUS_TIMEOUT_SECONDS = 5.0

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


def brighten(color, amount=0.25):
    return tuple(min(255, int(channel + (255 - channel) * amount)) for channel in color)


def with_alpha(color, alpha):
    return (color[0], color[1], color[2], alpha)


def blend_color(a, b, t=0.5):
    return (
        int(lerp(a[0], b[0], t)),
        int(lerp(a[1], b[1], t)),
        int(lerp(a[2], b[2], t)),
    )


def draw_glow_circle(surface, color, pos, radii_and_alpha):
    glow = brighten(color, 0.35)
    for radius, alpha in radii_and_alpha:
        if radius > 0 and alpha > 0:
            pygame.draw.circle(surface, with_alpha(glow, alpha), pos, radius)


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


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3

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


def load_ui_font(size, bold=False):
    font_path = pygame.font.match_font(
        ["inter", "segoeui", "segoe ui", "noto sans", "dejavu sans", "liberation sans"]
    )
    font = pygame.font.Font(font_path, size) if font_path else pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


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

# ───────────────── VIDEO RENDERER ─────────────────
class VideoRenderer:
    def __init__(self, w, h, fps):
        self.w = w
        self.h = h
        self.fps = fps
        self.frame = 0
        self.total = 0
        self.writer = None

    def start(self, path, duration, audio_source=None):
        self.path = path
        self.audio_source = audio_source
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
        if self.audio_source and shutil.which("ffmpeg"):
            temp_path = self.path + ".tmp.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-i", self.path,
                "-i", self.audio_source,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                temp_path,
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.replace(temp_path, self.path)
                print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")
            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")
                print(f"[RENDER] WARNING: audio mux failed: {e}")
        else:
            print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")


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
        pygame.display.set_caption("Musializer")
        self.clipboard_ready = False
        try:
            pygame.scrap.init()
            self.clipboard_ready = True
        except pygame.error:
            self.clipboard_ready = False

        self.clock = pygame.time.Clock()
        self.running = True

        self.font = load_mono_font(18)
        self.font_big = load_mono_font(30, bold=True)
        self.font_hint = load_mono_font(14)
        self.font_title = load_mono_font(40, bold=True)
        self.font_track = load_mono_font(15)
        self.font_prompt = load_mono_font(18)

        self.file = None
        self.spec = None
        self.times = None
        self.duration = 0
        self.track_title = ""
        self.track_source_label = ""
        self.track_source_detail = ""
        self.track_query = ""
        self.render_base_path = None

        self.active_bars = 84
        self.heights = np.zeros(MAX_BARS)
        self.velocity = np.zeros(MAX_BARS)

        self.start_ticks = 0
        self.pause_time = 0.0
        self.paused = False
        self.current_time = 0.0

        self.renderer = None
        self.rendering = False
        self.last_render_log = 0
        self.render_progress_length = 0
        self.loading = False
        self.loading_message = ""
        self.pending_load = None
        self.load_request_id = 0
        self.playback_finished = False

        self.status_message = ""
        self.status_level = "info"
        self.status_until = 0.0

        self.show_stream_prompt = False
        self.stream_input = ""

        BW, BH = 115, 38
        self.btn_prev = Button("◀◀  -10s", 0, 0, BW, BH, key_hint="← / A")
        self.btn_play = Button("▶  Play",  0, 0, BW, BH, key_hint="Space")
        self.btn_next = Button("▶▶  +10s", 0, 0, BW, BH, key_hint="→ / D")
        self.btn_stream = Button("Open URL", 0, 0, 120, 38, key_hint="U")
        self.btn_render = Button("Export MP4", 0, 0, 130, 38, key_hint="R")
        self.btn_playlist = Button("Playlist", 0, 0, 110, 38, key_hint="L")

        self.playlist_dir = None
        self.playlist = []
        self.playlist_index = 0
        self.playlist_cursor = 0
        self.playlist_scroll = 0
        self.show_playlist = False

        if start_path:
            start_path = start_path.strip()
            if os.path.isdir(start_path):
                self.load_playlist(start_path)
            elif os.path.isfile(start_path):
                self.load_playlist(os.path.dirname(start_path), start_file=start_path)
            else:
                self.open_stream_prompt(seed=start_path)
        else:
            default_music_dir = os.path.join(os.getcwd(), "music")
            if os.path.isdir(default_music_dir) and self.get_supported_files(default_music_dir):
                self.load_playlist(default_music_dir)

        self.refresh_play_button()

    def set_status(self, message, level="info", seconds=STATUS_TIMEOUT_SECONDS):
        self.status_message = message
        self.status_level = level
        self.status_until = (pygame.time.get_ticks() / 1000.0) + seconds if seconds else 0.0

    def refresh_play_button(self):
        if self.spec is None or self.loading or self.paused or self.playback_finished:
            self.btn_play.label = "▶  Play"
        else:
            self.btn_play.label = "⏸  Pause"

    def is_url(self, value):
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def normalize_stream_target(self, value):
        value = value.strip()
        if value.startswith(("www.", "m.", "youtube.com", "youtu.be", "music.youtube.com")):
            return "https://" + value
        return value

    def stream_prompt_rect(self):
        return self.terminal_dock_rect()

    def open_stream_prompt(self, seed=""):
        if self.rendering:
            return
        self.show_stream_prompt = True
        self.stream_input = seed
        self.show_playlist = False
        pygame.key.start_text_input()

    def close_stream_prompt(self):
        if not self.show_stream_prompt:
            return
        self.show_stream_prompt = False
        pygame.key.stop_text_input()

    def paste_stream_input(self):
        if not self.clipboard_ready:
            self.set_status("Clipboard paste is not available on this system.", "warning")
            return
        clip = pygame.scrap.get(pygame.SCRAP_TEXT)
        if not clip:
            self.set_status("Clipboard is empty.", "warning")
            return
        text = clip.decode("utf-8", errors="ignore").replace("\x00", "").strip()
        if not text:
            self.set_status("Clipboard is empty.", "warning")
            return
        self.stream_input += text

    # ───────── SEEK ─────────
    def seek(self, t):
        """Reliable cross-platform seek: stop → rewind → play from t."""
        if self.spec is None or self.loading:
            return
        t = max(0.0, min(float(t), self.duration))
        pygame.mixer.music.stop()
        pygame.mixer.music.play(start=t)
        self.start_ticks = pygame.time.get_ticks() - int(t * 1000)
        self.pause_time = t
        self.current_time = t
        self.playback_finished = False
        if self.paused:
            pygame.mixer.music.pause()
        self.refresh_play_button()

    def skip(self, delta):
        self.seek(self.current_time + delta)

    # ───────── TOGGLE PAUSE ─────────
    def toggle_pause(self):
        if self.spec is None or self.loading:
            return
        if self.paused or self.playback_finished:
            if self.playback_finished or self.current_time >= max(0.0, self.duration - 0.1):
                self.paused = False
                self.playback_finished = False
                self.seek(0.0)
            else:
                pygame.mixer.music.unpause()
                self.start_ticks = pygame.time.get_ticks() - int(self.pause_time * 1000)
                self.paused = False
                self.playback_finished = False
        else:
            pygame.mixer.music.pause()
            self.pause_time = self.current_time
            self.paused = True
        self.refresh_play_button()

    # ───────── AUDIO LOAD ─────────
    def start_load(self, source, source_mode="auto"):
        if self.rendering:
            return

        source = source.strip()
        if not source:
            self.set_status("Enter a YouTube link or a search term first.", "warning")
            return

        self.load_request_id += 1
        request_id = self.load_request_id
        self.pending_load = None
        self.loading = True
        self.loading_message = "Loading source..."
        self.playback_finished = False
        self.pause_time = self.current_time
        self.paused = True
        self.refresh_play_button()
        pygame.mixer.music.stop()

        threading.Thread(
            target=self._load_source_worker,
            args=(request_id, source, source_mode),
            daemon=True,
        ).start()

    def _load_source_worker(self, request_id, source, source_mode):
        try:
            if source_mode == "stream":
                payload = self.prepare_stream_payload(source)
            else:
                payload = self.prepare_local_payload(source)
            self.pending_load = {"request_id": request_id, "payload": payload, "error": None}
        except Exception as exc:
            self.pending_load = {"request_id": request_id, "payload": None, "error": str(exc)}

    def prepare_local_payload(self, path):
        path = os.path.abspath(path)
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            supported = ", ".join(sorted(SUPPORTED_FORMATS))
            raise ValueError(f"Unsupported format: {ext or 'unknown'} ({supported})")

        print(f"[LOAD] {os.path.basename(path)}")
        self.loading_message = f"Analyzing {os.path.basename(path)}..."

        y, sr = librosa.load(path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=MAX_BARS, hop_length=512)
        spec = librosa.power_to_db(mel, ref=np.max)
        times = librosa.frames_to_time(np.arange(spec.shape[1]), sr=sr, hop_length=512)

        return {
            "path": path,
            "duration": duration,
            "spec": spec,
            "times": times,
            "title": os.path.splitext(os.path.basename(path))[0],
            "source_label": "Local file",
            "source_detail": path,
            "render_base_path": path,
            "query": "",
        }

    def prepare_stream_payload(self, query):
        yt_dlp = shutil.which("yt-dlp")
        if not yt_dlp:
            raise RuntimeError("Install `yt-dlp` to open YouTube links or run stream searches.")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Install `ffmpeg` to extract audio from online streams.")

        os.makedirs(STREAM_CACHE_DIR, exist_ok=True)
        query = self.normalize_stream_target(query)
        target = query if self.is_url(query) else f"{STREAM_QUERY_PREFIX}{query}"

        self.loading_message = "Searching YouTube..." if target.startswith(STREAM_QUERY_PREFIX) else "Fetching stream..."

        cmd = [
            yt_dlp,
            "--quiet",
            "--no-warnings",
            "--no-playlist",
            "--no-progress",
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "--output",
            os.path.join(STREAM_CACHE_DIR, "%(extractor_key)s-%(id)s.%(ext)s"),
            "--print",
            "after_move:%(filepath)s|||%(title)s|||%(extractor_key)s|||%(webpage_url)s",
            target,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(self.extract_yt_dlp_error(result.stderr or result.stdout))

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("The stream was resolved, but no track metadata came back from yt-dlp.")

        if "|||" not in lines[-1]:
            raise RuntimeError("The stream loaded, but yt-dlp returned incomplete metadata.")

        path, title, extractor_key, webpage_url = lines[-1].split("|||", 3)
        path = path.strip()
        title = title.strip() or "Online stream"
        extractor_key = extractor_key.strip()
        webpage_url = webpage_url.strip() or query

        if not os.path.exists(path):
            raise RuntimeError("The stream finished downloading, but the extracted audio file was not found.")

        print(f"[STREAM] {title}")
        self.loading_message = f"Analyzing {title}..."

        y, sr = librosa.load(path, sr=None, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=MAX_BARS, hop_length=512)
        spec = librosa.power_to_db(mel, ref=np.max)
        times = librosa.frames_to_time(np.arange(spec.shape[1]), sr=sr, hop_length=512)

        render_dir = os.path.join(os.getcwd(), "renders")
        os.makedirs(render_dir, exist_ok=True)

        return {
            "path": path,
            "duration": duration,
            "spec": spec,
            "times": times,
            "title": title,
            "source_label": humanize_source(extractor_key),
            "source_detail": webpage_url,
            "render_base_path": os.path.join(render_dir, clean_filename(title, fallback="stream") + ".mp3"),
            "query": query,
        }

    def extract_yt_dlp_error(self, text):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "Unable to load that stream."
        return lines[-1].removeprefix("ERROR: ").strip() or "Unable to load that stream."

    def apply_pending_load(self):
        pending = self.pending_load
        if not pending:
            return

        self.pending_load = None
        if pending["request_id"] != self.load_request_id:
            return

        self.loading = False
        self.loading_message = ""

        if pending["error"]:
            self.set_status(pending["error"], "error", seconds=7.0)
            self.refresh_play_button()
            return

        payload = pending["payload"]
        self.spec = payload["spec"]
        self.times = payload["times"]
        self.duration = payload["duration"]
        self.file = payload["path"]
        self.track_title = payload["title"]
        self.track_source_label = payload["source_label"]
        self.track_source_detail = payload["source_detail"]
        self.track_query = payload["query"]
        self.render_base_path = payload["render_base_path"]

        self.heights.fill(0)
        self.velocity.fill(0)

        pygame.mixer.music.load(self.file)
        pygame.mixer.music.play()

        self.start_ticks = pygame.time.get_ticks()
        self.pause_time = 0.0
        self.current_time = 0.0
        self.paused = False
        self.playback_finished = False
        self.refresh_play_button()

        print("[READY]  Space=Pause  U=Stream  ←/→=±10s  R=Render  L=Playlist  ESC=Exit")
        self.set_status(f"Now playing: {self.track_title}", "success", seconds=4.0)

    def get_supported_files(self, directory):
        files = []
        try:
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                stem, ext = os.path.splitext(name)
                if ext.lower() in SUPPORTED_FORMATS and not stem.lower().endswith("_viz"):
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
            self.start_load(self.playlist[self.playlist_index], source_mode="local")

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
        self.start_load(self.playlist[self.playlist_index], source_mode="local")

    def start_next_track(self):
        if not self.playlist:
            return
        self.playlist_index = (self.playlist_index + 1) % len(self.playlist)
        self.playlist_cursor = self.playlist_index
        self.start_load(self.playlist[self.playlist_index], source_mode="local")

    def spectrum_at(self, t):
        idx = np.searchsorted(self.times, t)
        idx = min(idx, len(self.times) - 1)
        frame = self.spec[:, idx]
        frame = np.clip((frame + 80) / 80, 0, 1) ** 0.65
        return frame[:self.active_bars]

    # ───────── UPDATE ─────────
    def update(self):
        self.apply_pending_load()

        if self.status_message and self.status_until:
            now = pygame.time.get_ticks() / 1000.0
            if now >= self.status_until:
                self.status_message = ""
                self.status_until = 0.0

        if self.spec is None:
            return

        if self.rendering:
            if self.paused:
                pygame.mixer.music.unpause()
                self.paused = False
                self.refresh_play_button()
            t = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
            track_ended = not pygame.mixer.music.get_busy() and t >= self.duration - 0.1
            if track_ended or t >= self.duration or self.renderer.frame >= self.renderer.total:
                self.renderer.stop()
                self.rendering = False
                self.render_progress_length = 0
                if track_ended:
                    self.start_next_track()
                return
        else:
            if self.paused:
                t = self.pause_time
            else:
                t = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
                if not pygame.mixer.music.get_busy() and t >= self.duration - 0.1:
                    self.current_time = self.duration
                    self.pause_time = self.duration
                    self.paused = True
                    self.playback_finished = True
                    self.refresh_play_button()
                    if self.playlist and self.file in self.playlist:
                        self.start_next_track()
                    return

        self.current_time = min(max(t, 0.0), self.duration)

        if self.rendering:
            now_ms = pygame.time.get_ticks()
            if now_ms - self.last_render_log >= 500:
                remaining = max(0.0, self.duration - self.current_time)
                pct = int((self.current_time / self.duration) * 100) if self.duration > 0 else 0
                rem_text = str(timedelta(seconds=int(remaining)))
                bar_len = 30
                filled = int(bar_len * pct / 100)
                bar = "#" * filled + "-" * (bar_len - filled)
                msg = f"[RENDER] [{bar}] {pct}% complete — {rem_text} remaining"
                clear = " " * max(0, self.render_progress_length - len(msg))
                sys.stdout.write("\r" + msg + clear)
                sys.stdout.flush()
                self.render_progress_length = len(msg)
                self.last_render_log = now_ms

        data = self.spectrum_at(self.current_time)
        max_h = self.screen.get_height() * 0.60

        for i in range(self.active_bars):
            target = data[i] * max_h
            diff = target - self.heights[i]
            ratio = min(1.0, abs(diff) / max_h)
            ease = ease_in_out(ratio)
            spring_force = SPRING * (0.70 + 0.50 * ease)
            self.velocity[i] = (self.velocity[i] + diff * spring_force) * DAMPING
            if abs(self.velocity[i]) > abs(diff):
                self.velocity[i] = math.copysign(abs(diff), self.velocity[i])
            self.heights[i] = max(0.0, self.heights[i] + self.velocity[i])

    def control_panel_rect(self):
        w, h = self.screen.get_size()
        margin = 24 if w >= 640 else 12
        return pygame.Rect(margin, h - 124 - margin, max(220, w - margin * 2), 124)

    def terminal_dock_rect(self):
        w, h = self.screen.get_size()
        width = min(720, max(320, w - 36))
        width = min(width, max(220, w - 20))
        height = 84
        return pygame.Rect(18, h - height - 18, width, height)

    def progress_hit_rect(self):
        dock = self.terminal_dock_rect()
        margin = 28 if self.screen.get_width() >= 640 else 16
        y = max(18, dock.y - 24)
        return pygame.Rect(margin, y, max(120, self.screen.get_width() - margin * 2), 12)

    def playlist_overlay_rect(self):
        w, h = self.screen.get_size()
        margin = 60 if w >= 780 else 18
        overlay_w = max(240, w - margin * 2)
        overlay_h = max(220, min(h - 80, 520))
        return pygame.Rect((w - overlay_w) // 2, 40, overlay_w, overlay_h)

    def layout_buttons(self, mx=None, my=None):
        return

    def next_available_path(self, path):
        if not os.path.exists(path):
            return path
        stem, ext = os.path.splitext(path)
        counter = 2
        while True:
            candidate = f"{stem}_{counter}{ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1

    def start_render(self):
        if self.spec is None or self.rendering or self.loading:
            return

        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

        if self.playback_finished or not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(start=self.current_time)
            self.start_ticks = pygame.time.get_ticks() - int(self.current_time * 1000)
            self.playback_finished = False

        base = self.render_base_path or self.file
        out = self.next_available_path(os.path.splitext(base)[0] + "_viz.mp4")
        out_dir = os.path.dirname(out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        self.renderer = VideoRenderer(1920, 1080, FPS)
        self.renderer.start(out, self.duration, audio_source=self.file)
        self.rendering = True
        self.refresh_play_button()
        self.set_status(f"Rendering to {os.path.basename(out)}", "info", seconds=4.0)

    def submit_stream_prompt(self):
        value = self.stream_input.strip()
        if not value:
            self.set_status("Paste a link or type a search to start playback.", "warning")
            return
        self.close_stream_prompt()
        self.start_load(value, source_mode="stream")

    def handle_stream_prompt_event(self, event):
        if not self.show_stream_prompt:
            return False

        if event.type == pygame.TEXTINPUT:
            if len(self.stream_input) < 300:
                self.stream_input += event.text
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close_stream_prompt()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.submit_stream_prompt()
            elif event.key == pygame.K_BACKSPACE:
                self.stream_input = self.stream_input[:-1]
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                self.paste_stream_input()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.stream_prompt_rect().collidepoint(event.pos):
                self.close_stream_prompt()
            return True

        return False

    def draw_background(self, w, h):
        self.screen.fill(COLOR_BG)

    def draw_top_actions(self):
        return

    def draw_empty_state(self, w, h):
        panel = self.terminal_dock_rect()
        draw_terminal_panel(self.screen, panel)

        title = self.font.render("musializer", True, COLOR_TERMINAL_BORDER)
        self.screen.blit(title, (panel.x + 14, panel.y + 12))

        lines = [
            "> drop audio file",
            "> press u to search youtube",
            "> left/right seek, space pause",
        ]
        for idx, line in enumerate(lines):
            label = self.font.render(line, True, COLOR_TERMINAL_TEXT if idx == 0 else COLOR_TEXT_DIM)
            self.screen.blit(label, (panel.x + 16, panel.y + 34 + idx * 16))

    def draw_header(self, w):
        return

    def draw_controls(self, mx, my):
        prog_hit = self.progress_hit_rect()
        prog_x = prog_hit.x
        prog_y = prog_hit.y + prog_hit.h // 2
        prog_w = prog_hit.w
        prog_h = 2

        pygame.draw.rect(self.screen, COLOR_TERMINAL_DIM, (prog_x, prog_y, prog_w, prog_h))

        progress = self.current_time / self.duration if self.duration > 0 else 0
        fill = int(prog_w * progress)
        if fill > 0:
            pygame.draw.rect(self.screen, COLOR_TERMINAL_BORDER, (prog_x, prog_y, fill, prog_h))

        if prog_hit.collidepoint(mx, my):
            pygame.draw.rect(
                self.screen,
                COLOR_TERMINAL_TEXT,
                (prog_x, prog_y - 2, prog_w, prog_h + 4),
                1,
            )

        knob_x = prog_x + fill
        knob_x = max(prog_x, min(prog_x + prog_w, knob_x))
        pygame.draw.circle(self.screen, COLOR_TERMINAL_BORDER, (knob_x, prog_y + prog_h // 2), 4)

    def draw_track_label(self, w):
        title = trim_text(self.font_track, self.track_title or "", max(120, w - 40))
        if not title:
            return
        label = self.font_track.render(title, True, COLOR_TERMINAL_TEXT)
        self.screen.blit(label, (20, 18))

    def draw_playlist_overlay(self):
        overlay_rect = self.playlist_overlay_rect()
        overlay = pygame.Surface((overlay_rect.w, overlay_rect.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))
        pygame.draw.rect(overlay, (8, 12, 9, 238), (0, 0, overlay_rect.w, overlay_rect.h))
        pygame.draw.rect(overlay, COLOR_TERMINAL_BORDER, (0, 0, overlay_rect.w, overlay_rect.h), 1)

        title = self.font_big.render("[playlist]", True, COLOR_TERMINAL_BORDER)
        overlay.blit(title, (24, 18))
        help_text = self.font_hint.render(
            "esc close | up/down move | enter/click play",
            True,
            COLOR_TERMINAL_DIM,
        )
        overlay.blit(help_text, (24, 64))

        visible_lines = 10
        for idx in range(self.playlist_scroll, min(len(self.playlist), self.playlist_scroll + visible_lines)):
            row = pygame.Rect(18, 96 + (idx - self.playlist_scroll) * 36, overlay_rect.w - 36, 30)
            if idx == self.playlist_cursor:
                pygame.draw.rect(overlay, (18, 30, 20), row)
                pygame.draw.rect(overlay, COLOR_TERMINAL_BORDER, row, 1)
            name = trim_text(self.font, os.path.basename(self.playlist[idx]), row.w - 24)
            prefix = "▶ " if idx == self.playlist_index else "   "
            color = COLOR_TERMINAL_BORDER if idx == self.playlist_cursor else COLOR_TERMINAL_TEXT
            item = self.font.render(f"{prefix}{idx + 1:02d}. {name}", True, color)
            overlay.blit(item, (row.x + 10, row.y + 5))

        self.screen.blit(overlay, overlay_rect.topleft)

    def draw_status_toast(self):
        if not self.status_message:
            return
        if self.status_level not in {"warning", "error"}:
            return

        colors = {
            "info": COLOR_ACCENT_SOFT,
            "success": COLOR_SUCCESS,
            "warning": COLOR_WARNING,
            "error": COLOR_ERROR,
        }
        border = colors.get(self.status_level, COLOR_TERMINAL_BORDER)
        toast_y = max(18, self.terminal_dock_rect().y - 52)
        toast = pygame.Rect(24, toast_y, min(self.screen.get_width() - 48, 560), 42)
        pygame.draw.rect(self.screen, COLOR_PANEL, toast)
        pygame.draw.rect(self.screen, border, toast, 1)
        text = trim_text(self.font, self.status_message, toast.w - 24)
        label = self.font.render(text, True, border)
        self.screen.blit(label, (toast.x + 12, toast.y + 11))

    def draw_loading_overlay(self):
        panel = self.terminal_dock_rect()
        tick = (pygame.time.get_ticks() // 250) % 4
        pulse = "." * (tick + 1)
        text_x = panel.x + 6
        title = self.font_hint.render("yt-loader", True, COLOR_TERMINAL_DIM)
        self.screen.blit(title, (text_x, panel.y + 8))

        line1_text = trim_text(
            self.font,
            f"> {self.loading_message or 'working'}{pulse}",
            panel.w - 12,
        )
        line2_text = trim_text(
            self.font_hint,
            "downloading -> decoding -> analyzing",
            panel.w - 12,
        )
        line1 = self.font.render(line1_text, True, COLOR_TERMINAL_TEXT)
        line2 = self.font_hint.render(line2_text, True, COLOR_TERMINAL_DIM)
        self.screen.blit(line1, (text_x, panel.y + 30))
        self.screen.blit(line2, (text_x, panel.y + 54))

    def draw_stream_prompt_overlay(self):
        rect = self.stream_prompt_rect()
        prompt_label = self.font_hint.render("yt-search", True, COLOR_TERMINAL_DIM)
        self.screen.blit(prompt_label, (rect.x + 6, rect.y + 8))

        prompt_x = rect.x + 6
        prompt_y = rect.y + 30
        prompt_surface = self.font_prompt.render(">", True, COLOR_TERMINAL_BORDER)
        self.screen.blit(prompt_surface, (prompt_x, prompt_y))

        entry = self.stream_input or "paste link or type search"
        entry_color = COLOR_TERMINAL_TEXT if self.stream_input else COLOR_TERMINAL_DIM
        text_x = prompt_x + prompt_surface.get_width() + 12
        rendered = trim_text(self.font_prompt, entry, rect.w - (text_x - rect.x) - 6)
        entry_surface = self.font_prompt.render(rendered, True, entry_color)
        self.screen.blit(entry_surface, (text_x, prompt_y))

        if self.stream_input and (pygame.time.get_ticks() // 500) % 2 == 0:
            caret_x = min(rect.right - 8, text_x + entry_surface.get_width() + 2)
            pygame.draw.line(
                self.screen,
                COLOR_TERMINAL_TEXT,
                (caret_x, prompt_y + 2),
                (caret_x, prompt_y + self.font_prompt.get_height() - 2),
                2,
            )

    # ───────── DRAW ─────────
    def draw(self):
        w, h = self.screen.get_size()
        mx, my = pygame.mouse.get_pos()
        self.draw_background(w, h)

        if self.spec is None:
            self.draw_empty_state(w, h)
        else:
            bar_area_x = 60
            bar_area_w = w - 120
            bar_w = bar_area_w / self.active_bars
            stem_width = max(2, int(bar_w * 0.18))

            if self.rendering:
                base_y = h - 40
                hue_shift = 0.0
            else:
                base_y = self.progress_hit_rect().y - 20
                hue_shift = (pygame.time.get_ticks() / 1000.0) * 0.06

            max_h = self.screen.get_height() * 0.72
            glow_surface = pygame.Surface((w, h), pygame.SRCALPHA)

            for i in range(self.active_bars):
                bh = self.heights[i]
                if bh < 1:
                    continue
                color = bar_color(i, self.active_bars, hue_shift)
                x = bar_area_x + i * bar_w + bar_w * 0.5
                top_y = base_y - bh
                draw_neon_bar(self.screen, glow_surface, x, base_y, top_y, color, stem_width)

            self.screen.blit(glow_surface, (0, 0))

            if not self.rendering:
                self.draw_controls(mx, my)
                if not self.show_stream_prompt and not self.loading:
                    self.draw_track_label(w)

        if self.show_playlist and not self.rendering:
            self.draw_playlist_overlay()

        self.draw_status_toast()

        if self.show_stream_prompt:
            self.draw_stream_prompt_overlay()

        if self.loading:
            self.draw_loading_overlay()

        pygame.display.flip()

        if self.rendering:
            self.renderer.write(self.screen)

    # ───────── RUN ─────────
    def run(self):
        print("MUSIALIZER READY — drop audio/video, press U for YouTube/search, press L for playlists.")

        while self.running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                    continue

                if self.handle_stream_prompt_event(e):
                    continue

                if e.type == pygame.DROPFILE and not self.rendering and not self.loading:
                    if os.path.isdir(e.file):
                        self.load_playlist(e.file)
                    elif os.path.isfile(e.file):
                        self.load_playlist(os.path.dirname(e.file), start_file=e.file)
                    else:
                        self.set_status("That drop target is not a supported file or folder.", "warning")
                    continue

                if e.type == pygame.KEYDOWN:
                    if self.show_playlist:
                        if e.key in (pygame.K_ESCAPE, pygame.K_l):
                            self.show_playlist = False
                        elif e.key == pygame.K_UP:
                            self.move_playlist_cursor(-1)
                        elif e.key == pygame.K_DOWN:
                            self.move_playlist_cursor(1)
                        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.select_playlist_item()
                        continue

                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                    elif e.key == pygame.K_u:
                        self.open_stream_prompt()
                    elif e.key == pygame.K_l and self.playlist:
                        self.toggle_playlist()
                    elif e.key == pygame.K_SPACE:
                        self.toggle_pause()
                    elif e.key in (pygame.K_LEFT, pygame.K_a) and self.spec is not None:
                        self.skip(-SKIP_SECONDS)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d) and self.spec is not None:
                        self.skip(SKIP_SECONDS)
                    elif e.key == pygame.K_r and self.spec is not None and not self.rendering:
                        self.start_render()

                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.show_playlist:
                        overlay = self.playlist_overlay_rect()
                        if not overlay.collidepoint(e.pos):
                            self.show_playlist = False
                        else:
                            visible_lines = 10
                            for idx in range(
                                self.playlist_scroll,
                                min(len(self.playlist), self.playlist_scroll + visible_lines),
                            ):
                                row = pygame.Rect(
                                    overlay.x + 18,
                                    overlay.y + 96 + (idx - self.playlist_scroll) * 36,
                                    overlay.w - 36,
                                    30,
                                )
                                if row.collidepoint(e.pos):
                                    self.playlist_cursor = idx
                                    self.select_playlist_item()
                                    break
                        continue

                    if self.spec is not None and self.progress_hit_rect().collidepoint(e.pos):
                        ratio = (e.pos[0] - self.progress_hit_rect().x) / self.progress_hit_rect().w
                        self.seek(ratio * self.duration)

            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        print("[EXIT]")


if __name__ == "__main__":
    start_path = sys.argv[1] if len(sys.argv) > 1 else None
    AudioVisualizer(start_path).run()
