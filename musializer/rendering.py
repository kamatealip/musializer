import os
import shutil
import subprocess

import cv2
import pygame


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
            (self.w, self.h),
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
                "ffmpeg",
                "-y",
                "-i",
                self.path,
                "-i",
                self.audio_source,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                temp_path,
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.replace(temp_path, self.path)
                print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")
            except Exception as exc:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")
                print(f"[RENDER] WARNING: audio mux failed: {exc}")
        else:
            print(f"\n[RENDER] COMPLETE ✔ stored at: {self.path}")
