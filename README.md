# Musializer

A local Python music visualizer that renders animated frequency bars from audio files.

## Prerequisites

- Python 3.9+
- `uv` package manager
- `ffmpeg` for audio muxing into rendered MP4 files (optional, but recommended)

Verify:

```bash
python --version
uv --version
ffmpeg -version
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
├── music_visualizer.py
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

If no folder is provided, the script uses the local `music/` folder.

## Controls

- `SPACE` — Play / Pause
- `←` / `A` — Seek backward 10 seconds
- `→` / `D` — Seek forward 10 seconds
- `L` — Open playlist
- `R` — Start render mode
- `ESC` — Exit

## Render Output

Press `R` while a track is loaded to generate `*_viz.mp4` in the same folder as the music file.

If `ffmpeg` is available, the renderer will automatically mux the original audio into the output video.

## Tips

- Drop audio files onto the window to load them directly
- Use the playlist view to select another track
- The rendered video file is saved next to the source audio with `_viz.mp4` appended
