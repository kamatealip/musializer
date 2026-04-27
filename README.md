# Musializer

A Python music visualizer that renders animated frequency bars from local files and online streams.

## Prerequisites

- Python 3.9+
- `uv` package manager
- `ffmpeg` for audio muxing and extracting online stream audio
- `yt-dlp` for YouTube and other supported online streams

Verify:

```bash
python --version
uv --version
ffmpeg -version
yt-dlp --version
```

## Install Dependencies

From the repository root:

```bash
uv sync
```

This installs the dependencies defined in `pyproject.toml`.

## Project Structure

```
.
├── main.py
├── pyproject.toml
├── uv.lock
├── README.md
└── music/
```

## Run the Visualizer

From the repository root:

```bash
uv run python main.py
```

You can also pass a music folder manually:

```bash
uv run python main.py ~/Music
```

You can also start with a YouTube URL or search term:

```bash
uv run python main.py "https://youtu.be/example"
uv run python main.py "daft punk harder better faster stronger"
```

If no folder is provided, the script uses the local `music/` folder.

## Controls

- `SPACE` — Play / Pause
- `←` / `A` — Seek backward 10 seconds
- `→` / `D` — Seek forward 10 seconds
- `F` — Open the YouTube find/search prompt
- `O` — Open a local file picker
- `L` — Open playlist
- `R` — Start render mode
- `ESC` — Exit

## Render Output

Press `R` while a track is loaded to generate a `*_viz.mp4` export.

If `ffmpeg` is available, the renderer will automatically mux the original audio into the output video.

## Tips

- Drop audio files onto the window to load them directly
- Press `F` to paste a YouTube link or type a quick search query
- Press `O` to browse for a local track
- Use the playlist view to select another track
- The rendered video file is saved next to the source audio with `_viz.mp4` appended

## next ti implement

- youtube search
- # multi threading
- Local renders are saved next to the source audio with `_viz.mp4` appended
- Stream renders are saved in the local `renders/` folder
