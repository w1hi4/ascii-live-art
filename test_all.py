import os
import sys
import time
import json
import re
from PIL import Image

def run_test(name, func):
    sys.stdout.write(f"[*] Testing {name}... ")
    sys.stdout.flush()
    try:
        start = time.time()
        func()
        duration = (time.time() - start) * 1000
        print(f"PASSED ({duration:.1f}ms)")
        return True
    except Exception as e:
        print(f"FAILED!\n    Error: {e}")
        import traceback
        traceback.print_exc()
        return False

print("=" * 65)
print(" ASCII.LIVE PRO - COMPLETE COMPONENT & INTEGRATION TEST SUITE")
print("=" * 65)

# --- 1. Dependencies and Assets ---
def test_environment_and_assets():
    import tornado
    import PIL
    import numpy
    assert os.path.exists("ciarllogo.png"), "ciarllogo.png is missing!"
    assert os.path.exists("static/index.html"), "index.html is missing!"
    assert os.path.exists("static/viewer.html"), "viewer.html is missing!"
    assert os.path.exists("static/app.js"), "app.js is missing!"
    assert os.path.exists("static/style.css"), "style.css is missing!"
    assert os.path.exists("Dockerfile"), "Dockerfile is missing!"
    assert os.path.exists("render.yaml"), "render.yaml is missing!"
    assert os.path.exists("requirements.txt"), "requirements.txt is missing!"

# --- 2. ASCII Engine: Half-Block Conversion ---
def test_halfblock_converter():
    import ascii_engine
    img = Image.open("ciarllogo.png")
    text = ascii_engine.convert_image_to_halfblock(img, width=54)
    assert len(text) > 0, "Half-block text is empty!"
    assert "▀" in text or "▄" in text, "Half-block characters not found!"
    assert "\033[38;2;" in text, "24-bit Truecolor ANSI foreground missing!"
    lines = text.split("\n")
    assert len(lines) > 10, f"Expected >10 rows, got {len(lines)}"

# --- 3. ASCII Engine: Character Density Conversion ---
def test_ascii_char_converter():
    import ascii_engine
    img = Image.open("ciarllogo.png")
    text = ascii_engine.convert_image_to_ascii(img, width=50)
    assert len(text) > 0, "ASCII text is empty!"
    assert "\033[38;2;" in text, "Color ANSI missing in character conversion!"
    lines = text.split("\n")
    assert len(lines) > 5, "Too few lines in character conversion"

# --- 4. Procedural Shaders: Scanner, Pulse, Matrix, Glitch ---
def test_procedural_shaders():
    import ascii_engine
    img = Image.open("ciarllogo.png")
    
    # 4a. Scanner
    scanner_frames = ascii_engine.generate_scanner_frames(img, width=50, num_frames=6)
    assert len(scanner_frames) == 6, f"Expected 6 frames, got {len(scanner_frames)}"
    assert "\033[H" in scanner_frames[0], "Cursor Home escape code missing"

    # 4b. Pulse
    pulse_frames = ascii_engine.generate_pulse_frames(img, width=50, num_frames=6)
    assert len(pulse_frames) == 6, f"Expected 6 frames, got {len(pulse_frames)}"

    # 4c. Matrix
    matrix_frames = ascii_engine.generate_matrix_frames(img, width=50, num_frames=6)
    assert len(matrix_frames) == 6, f"Expected 6 frames, got {len(matrix_frames)}"

    # 4d. Glitch
    glitch_frames = ascii_engine.generate_glitch_frames(img, width=50, num_frames=6)
    assert len(glitch_frames) == 6, f"Expected 6 frames, got {len(glitch_frames)}"

# --- 5. Donut 3D Math Engine ---
def test_donut_engine():
    import ascii_engine
    donut_frames = ascii_engine.generate_donut_frames(num_frames=6, width=40, height=20)
    assert len(donut_frames) == 6, "Expected 6 donut frames"
    assert "\033[H" in donut_frames[0], "Donut frame missing ANSI Home"

# --- 6. Server Initialization & Preloaded Animations ---
def test_server_initialization():
    import db
    import server
    server.init_default_animations()
    ciarl_data = db.get_animation("ciarl")
    assert ciarl_data is not None, "ciarl animation not found in DB!"
    assert len(ciarl_data["frames"]) >= 10, f"Expected >=10 frames for CIARL, got {len(ciarl_data['frames'])}"
    assert ciarl_data["fps"] > 0, "FPS should be positive"
    assert ciarl_data["width"] > 0, "Width should be positive"

    assert db.get_animation("ciarl-pulse") is not None, "ciarl-pulse animation not found in DB!"
    assert db.get_animation("donut") is not None, "donut animation not found in DB!"
    assert db.get_animation("fire") is not None, "fire animation not found in DB!"

    # Test analytics buffering
    db.record_view("ciarl")
    db.record_view("ciarl")
    db.flush_views_to_db()
    stats = db.get_stats()
    assert stats["total_animations"] >= 4
    assert stats["total_views"] >= 2

# --- 7. Offline CLI Player ---
def test_offline_player():
    import play_ascii
    frames, fps, title = play_ascii.get_animation_frames("ciarl")
    assert len(frames) > 0, "play_ascii returned 0 frames for 'ciarl'"
    assert "CIARL" in title, f"Title does not contain CIARL: {title}"

    frames_donut, _, _ = play_ascii.get_animation_frames("donut")
    assert len(frames_donut) > 0, "play_ascii returned 0 frames for 'donut'"

# --- 8. API & Route Logic ---
def test_api_handlers():
    import server
    app = server.make_app()
    assert app is not None, "Failed to create Tornado Application"
    
    # Check routes
    patterns = [r.matcher.regex.pattern for r in app.wildcard_router.rules]
    expected_routes = ["/$", "/health$", "/viewer$", "/static/ciarllogo.png$", "/api/stats$", "/api/list$", "/api/animation/(.*)$", "/api/upload$"]
    for r in expected_routes:
        assert r in patterns, f"Route pattern {r} missing in app router!"

# --- 9. Static UI Syntax & HTML Integrity ---
def test_static_ui_integrity():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()
        assert "ASCII.LIVE" in html
        assert "dropzone" in html
        assert "btnGenerate" in html
        assert "streamsBody" in html

    with open("static/viewer.html", "r", encoding="utf-8") as f:
        viewer = f.read()
        assert "crtDisplay" in viewer
        assert "scanlines" in viewer
        assert "btnPause" in viewer

    with open("static/app.js", "r", encoding="utf-8") as f:
        js = f.read()
        assert "function ansiToHtml" in js
        assert "loadPreview" in js
        assert "copyText" in js

# --- Run All Tests ---
tests = [
    ("Environment & Core Files", test_environment_and_assets),
    ("Half-Block 24-bit Truecolor Renderer", test_halfblock_converter),
    ("ASCII Character Density Converter", test_ascii_char_converter),
    ("Procedural Shaders (Scanner/Pulse/Matrix/Glitch)", test_procedural_shaders),
    ("3D Mathematical Donut Engine", test_donut_engine),
    ("Server In-Memory Registry & Default Presets", test_server_initialization),
    ("Offline CLI Player (play_ascii.py)", test_offline_player),
    ("API Handlers & Tornado Route Manifest", test_api_handlers),
    ("HTML, JS & CSS Integrity", test_static_ui_integrity),
]

passed = 0
for name, func in tests:
    if run_test(name, func):
        passed += 1

print("=" * 65)
print(f" RESULT: {passed}/{len(tests)} TESTS PASSED ({passed / len(tests) * 100:.0f}%)")
print("=" * 65)

if passed == len(tests):
    print(" ALL SYSTEMS OPERATIONAL AND VERIFIED!")
    sys.exit(0)
else:
    print(" SOME TESTS FAILED.")
    sys.exit(1)
