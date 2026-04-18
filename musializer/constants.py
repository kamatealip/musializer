import os
import tempfile

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
COLOR_SUCCESS = (102, 255, 153)
COLOR_WARNING = (255, 210, 120)
COLOR_ERROR = (255, 120, 120)
COLOR_TERMINAL_BORDER = (86, 214, 132)
COLOR_TERMINAL_TEXT = (188, 255, 208)
COLOR_TERMINAL_DIM = (104, 164, 121)

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
    (0.78, 1.0, 0.95),
    (0.62, 1.0, 1.00),
    (0.50, 1.0, 1.00),
    (0.38, 1.0, 1.00),
    (0.10, 1.0, 1.00),
    (0.96, 1.0, 0.95),
]
