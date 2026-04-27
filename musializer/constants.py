import os
import tempfile

FPS = 60
MAX_BARS = 128
BAR_GAP = 1

SPRING = 0.16
DAMPING = 0.95

COLOR_BG = (0, 0, 0)
COLOR_TEXT = (255, 232, 242)
COLOR_TEXT_DIM = (183, 133, 157)
COLOR_ACCENT = (255, 86, 150)
COLOR_ACCENT_SOFT = (255, 152, 192)
COLOR_CTRL = (16, 6, 12)
COLOR_CTRL_HOVER = (30, 10, 20)
COLOR_PANEL = (8, 4, 7)
COLOR_SUCCESS = (255, 134, 182)
COLOR_WARNING = (255, 197, 162)
COLOR_ERROR = (255, 118, 143)
COLOR_TERMINAL_BORDER = (255, 96, 160)
COLOR_TERMINAL_TEXT = (255, 218, 232)
COLOR_TERMINAL_DIM = (188, 122, 151)

SUPPORTED_FORMATS = {
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".aac",
    ".m4a",
    ".webm",
    ".opus",
    ".mp4",
}
SKIP_SECONDS = 10
STREAM_CACHE_DIR = os.path.join(tempfile.gettempdir(), "musializer_streams")
STREAM_QUERY_PREFIX = "ytsearch1:"
STATUS_TIMEOUT_SECONDS = 5.0

BAR_GRAD = [
    (0.00, 0.92, 1.00),
    (0.08, 0.94, 1.00),
    (0.16, 0.92, 1.00),
    (0.32, 0.82, 1.00),
    (0.54, 0.86, 1.00),
    (0.72, 0.84, 1.00),
    (0.86, 0.88, 1.00),
]
