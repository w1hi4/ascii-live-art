#!/usr/bin/env python3
"""
CLI Terminal Player for ASCII.LIVE animations.
Usage:
    python play_ascii.py ciarl
    python play_ascii.py donut
    python play_ascii.py fire
"""

import sys
import os
import time
import json
import tempfile

import ascii_engine
from PIL import Image

def get_animation_frames(name="ciarl"):
    name = name.strip("/").lower()

    # 1. Check temp cache
    temp_path = os.path.join(tempfile.gettempdir(), "ascii_live_animations", f"{name}.json")
    if os.path.exists(temp_path):
        with open(temp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("frames", []), data.get("fps", 12), data.get("title", name)

    # 2. Check local animations folder
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animations", f"{name}.json")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("frames", []), data.get("fps", 12), data.get("title", name)

    # 3. Dynamic generation
    if name == "ciarl":
        img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ciarllogo.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            frames = ascii_engine.generate_scanner_frames(img, width=54, mode="halfblock", num_frames=18)
            return frames, 12, "CIARL Cyber Shield - Laser Scanner"
    elif name == "donut":
        frames = ascii_engine.generate_donut_frames(num_frames=24, width=50, height=22)
        return frames, 16, "3D Mathematical Spinning Donut"

    return [], 12, name

def play(name="ciarl"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    frames, fps, title = get_animation_frames(name)
    if not frames:
        print(f"Error: Animation '{name}' not found.")
        print("Available: ciarl, ciarl-pulse, donut, fire")
        return

    delay = 1.0 / max(1, fps)
    idx = 0

    # Hide cursor and clear screen
    sys.stdout.write(f"{ascii_engine.ANSI_CLEAR}{ascii_engine.ANSI_HIDE_CURSOR}")
    sys.stdout.flush()

    try:
        while True:
            sys.stdout.write(frames[idx])
            sys.stdout.flush()
            time.sleep(delay)
            idx = (idx + 1) % len(frames)
    except KeyboardInterrupt:
        pass
    finally:
        # Show cursor and reset colors
        sys.stdout.write(f"{ascii_engine.ANSI_SHOW_CURSOR}{ascii_engine.ANSI_RESET}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    anim_name = sys.argv[1] if len(sys.argv) > 1 else "ciarl"
    play(anim_name)
