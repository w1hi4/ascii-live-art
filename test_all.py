import os
import sys
import time
import json
import re

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
print(" ASCII LIVE ART - COMPLETE TEST SUITE")
print("=" * 65)

# --- 1. Dependencies and Assets ---
def test_environment_and_assets():
    import tornado
    import PIL
    import numpy
    assert os.path.exists("static/index.html"), "index.html is missing!"
    assert os.path.exists("static/viewer.html"), "viewer.html is missing!"
    assert os.path.exists("static/app.js"), "app.js is missing!"
    assert os.path.exists("static/style.css"), "style.css is missing!"
    assert os.path.exists("Dockerfile"), "Dockerfile is missing!"
    assert os.path.exists("render.yaml"), "render.yaml is missing!"
    assert os.path.exists("requirements.txt"), "requirements.txt is missing!"

# --- 2. Flagship Art Banner Engine ---
def test_flagship_art_generator():
    import ascii_engine
    frames = ascii_engine.generate_flagship_art_frames(num_frames=6)
    assert len(frames) == 6, f"Expected 6 frames, got {len(frames)}"
    assert "\033[H" in frames[0], "Cursor Home escape code missing"
    clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', frames[0])
    assert "A S C I I" in clean_text, "Flagship banner missing ASCII text"

# --- 3. 3D Donut Math Engine ---
def test_donut_engine():
    import ascii_engine
    donut_frames = ascii_engine.generate_donut_frames(num_frames=6, width=40, height=20)
    assert len(donut_frames) == 6, "Expected 6 donut frames"
    assert "\033[H" in donut_frames[0], "Donut frame missing ANSI Home"

# --- 4. Server Initialization & Preloaded Animations ---
def test_server_initialization():
    import db
    import server
    server.init_default_animations()
    art_data = db.get_animation("art")
    assert art_data is not None, "art animation not found in DB!"
    assert len(art_data["frames"]) >= 10, f"Expected >=10 frames for art, got {len(art_data['frames'])}"
    assert art_data["fps"] > 0, "FPS should be positive"
    assert art_data["width"] > 0, "Width should be positive"

    assert db.get_animation("donut") is not None, "donut animation not found in DB!"
    assert db.get_animation("fire") is not None, "fire animation not found in DB!"

    # Test analytics buffering
    db.record_view("art")
    db.record_view("art")
    db.flush_views_to_db()
    # Test search query
    donut_results = db.list_animations(search="donut")
    assert len(donut_results) == 1, f"Expected 1 search result for 'donut', got {len(donut_results)}"
    assert donut_results[0]["slug"] == "donut"

# --- 5. Offline CLI Player ---
def test_offline_player():
    import play_ascii
    frames, fps, title = play_ascii.get_animation_frames("art")
    assert len(frames) > 0, "play_ascii returned 0 frames for 'art'"
    assert "ASCII" in title, f"Title does not contain ASCII: {title}"

    frames_donut, _, _ = play_ascii.get_animation_frames("donut")
    assert len(frames_donut) > 0, "play_ascii returned 0 frames for 'donut'"

# --- 6. API & Route Logic ---
def test_api_handlers():
    import server
    app = server.make_app()
    assert app is not None, "Failed to create Tornado Application"
    
    # Check routes
    patterns = [r.matcher.regex.pattern for r in app.wildcard_router.rules]
    expected_routes = ["/$", "/health$", "/viewer$", "/api/stats$", "/api/list$", "/api/animation/(.*)$", "/api/upload$"]
    for r in expected_routes:
        assert r in patterns, f"Route pattern {r} missing in app router!"

# --- 7. Static UI Syntax & HTML Integrity ---
def test_static_ui_integrity():
    with open("static/index.html", "r", encoding="utf-8") as f:
        html = f.read()
        assert "ASCII LIVE ART" in html
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
    ("Flagship Art Banner Generator", test_flagship_art_generator),
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
