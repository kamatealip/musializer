import os
import sys
from pathlib import Path


def _project_venv_python():
    root = Path(__file__).resolve().parent
    candidates = [
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_app():
    try:
        from musializer import AudioVisualizer
    except ModuleNotFoundError as exc:
        venv_python = _project_venv_python()
        if venv_python and Path(sys.executable).resolve() != venv_python.resolve():
            os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])

        missing = exc.name or "a required dependency"
        raise SystemExit(
            f"Missing dependency: {missing}\n"
            "Run `uv sync` and then start the app with `uv run python main.py`,\n"
            "or point your IDE interpreter to the project's `.venv`."
        ) from exc

    return AudioVisualizer


if __name__ == "__main__":
    start_path = sys.argv[1] if len(sys.argv) > 1 else None
    AudioVisualizer = _load_app()
    AudioVisualizer(start_path).run()
