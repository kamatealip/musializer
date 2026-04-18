import sys

from musializer import AudioVisualizer


if __name__ == "__main__":
    start_path = sys.argv[1] if len(sys.argv) > 1 else None
    AudioVisualizer(start_path).run()
