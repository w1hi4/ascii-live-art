#!/usr/bin/env python3
"""
CLI Terminal Player for ASCII Live Art animations.
Usage:
    python play_ascii.py art
    python play_ascii.py donut
    python play_ascii.py fire
"""

import sys
import os
import time
import json
import tempfile

import ascii_engine
import db

def get_animation_frames(name="art"):
    name = name.strip("/").lower()

    # 1. Check SQLite / LRU cache
    anim = db.get_animation(name)
    if anim:
        return anim.get("frames", []), anim.get("fps", 14), anim.get("title", name)

    # 2. Dynamic generation fallback
    if name == "art":
        frames = ascii_engine.generate_flagship_art_frames(num_frames=20)
        return frames, 14, "ASCII Live Art - Cyber Shimmer & Wave"
    elif name == "donut":
        frames = ascii_engine.generate_donut_frames(num_frames=24, width=50, height=22)
        return frames, 16, "3D Mathematical Spinning Donut"

    return [], 12, name

def play(name="art"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    frames, fps, title = get_animation_frames(name)
    if not frames:
        print(f"Error: Animation '{name}' not found.")
        print("Available: art, donut, fire")
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
    anim_name = sys.argv[1] if len(sys.argv) > 1 else "art"
    play(anim_name)
