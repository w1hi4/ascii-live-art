import os
import sys
import json
import time
import math
import random
import asyncio
import tempfile
import string
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

import tornado.ioloop
import tornado.web
import tornado.iostream

import ascii_engine
import db

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Thread pool for non-blocking image/GIF conversion
EXECUTOR = ThreadPoolExecutor(max_workers=4)

def generate_random_slug(length=6):
    """Generates a clean, short, URL-friendly slug."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))

def init_default_animations():
    """Initializes default showcase animations in SQLite if not present."""
    # 1. Flagship ASCII Live Art Stream (/art)
    if not db.get_animation("art"):
        print("[INFO] Baking flagship ASCII Live Art animation into database...")
        art_frames = ascii_engine.generate_flagship_art_frames(num_frames=20)
        db.save_animation("art", "ASCII Live Art - Cyber Shimmer & Wave", 14, 60, "ascii", "flagship", art_frames)

    # 2. 3D Donut (/donut)
    if not db.get_animation("donut"):
        print("[INFO] Baking 3D Donut into database...")
        donut_frames = ascii_engine.generate_donut_frames(num_frames=24, width=50, height=22)
        db.save_animation("donut", "3D Mathematical Spinning Donut", 16, 50, "ascii", "3d", donut_frames)

    # 3. Doom Inferno Fire (/fire)
    if not db.get_animation("fire"):
        print("[INFO] Baking Doom Inferno Fire into database...")
        w_f, h_f = 50, 20
        palette = [
            (0,0,0), (7,7,7), (31,7,7), (47,15,7), (71,15,7), (87,23,7), (103,31,7), (119,31,7),
            (143,39,7), (159,47,7), (175,63,7), (191,71,7), (199,71,7), (223,79,7), (223,87,7),
            (223,87,7), (215,95,7), (215,103,15), (207,111,15), (207,119,15), (207,127,15),
            (207,135,23), (199,135,23), (199,143,23), (199,151,31), (191,159,31), (191,159,31),
            (191,167,39), (191,167,39), (191,175,47), (183,175,47), (183,183,47), (183,183,55),
            (207,207,111), (223,223,159), (239,239,199), (255,255,255)
        ]
        fire_buf = [0] * (w_f * h_f)
        for x in range(w_f): fire_buf[(h_f - 1) * w_f + x] = 36
        for _ in range(50):
            for x in range(w_f):
                for y in range(1, h_f):
                    src = y * w_f + x
                    p = fire_buf[src]
                    if p > 0:
                        rnd = random.randint(0, 3) & 3
                        dst = src - rnd + 1
                        if w_f <= dst < w_f * h_f: fire_buf[dst - w_f] = max(0, p - (rnd & 1))
        
        fire_frames = []
        chars_fire = " .:-=+*#%@█"
        for _ in range(24):
            for x in range(w_f):
                for y in range(1, h_f):
                    src = y * w_f + x
                    p = fire_buf[src]
                    if p == 0: fire_buf[src - w_f] = 0
                    else:
                        rnd = random.randint(0, 3) & 3
                        dst = src - rnd + 1
                        if w_f <= dst < w_f * h_f: fire_buf[dst - w_f] = max(0, p - (rnd & 1))
            lines = []
            for y in range(h_f):
                line = ""
                for x in range(w_f):
                    val = min(36, max(0, fire_buf[y * w_f + x]))
                    r, g, b = palette[val]
                    char = chars_fire[min(len(chars_fire) - 1, val * len(chars_fire) // 37)]
                    if val < 2: line += " "
                    else: line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
                lines.append(line)
            fire_frames.append(f"{ascii_engine.ANSI_HOME}{ascii_engine.ANSI_HIDE_CURSOR}" + "\n".join(lines) + f"{ascii_engine.ANSI_RESET}\n")

        db.save_animation("fire", "Demoscene Doom Inferno Fire", 15, 50, "ascii", "fire", fire_frames)


def process_uploaded_media(body_bytes, width, mode, effect, contrast, brightness):
    """Worker function executed in thread pool for CPU-heavy frame baking."""
    if not body_bytes:
        return ascii_engine.generate_flagship_art_frames(num_frames=20), 14

    img = Image.open(BytesIO(body_bytes))
    is_gif = getattr(img, "is_animated", False)
    frames = []
    fps = 12

    if is_gif:
        tmp_gif = os.path.join(tempfile.gettempdir(), f"upload_{time.time()}.gif")
        with open(tmp_gif, "wb") as f_out:
            f_out.write(body_bytes)
        frames, gif_delay = ascii_engine.convert_gif_to_frames(tmp_gif, width=width, mode=mode)
        try:
            os.remove(tmp_gif)
        except Exception:
            pass
        if gif_delay > 0:
            fps = max(1, min(30, int(1000 / gif_delay)))
    else:
        if effect == "scanner":
            frames = ascii_engine.generate_scanner_frames(img, width=width, mode=mode, num_frames=18)
        elif effect == "pulse":
            frames = ascii_engine.generate_pulse_frames(img, width=width, mode=mode, num_frames=16)
        elif effect == "matrix":
            frames = ascii_engine.generate_matrix_frames(img, width=width, mode=mode, num_frames=18)
        elif effect == "glitch":
            frames = ascii_engine.generate_glitch_frames(img, width=width, mode=mode, num_frames=16)
        else:
            if mode == "halfblock":
                t = ascii_engine.convert_image_to_halfblock(img, width=width, contrast=contrast, brightness=brightness)
            else:
                t = ascii_engine.convert_image_to_ascii(img, width=width, contrast=contrast, brightness=brightness)
            frames = [f"{ascii_engine.ANSI_HOME}{ascii_engine.ANSI_HIDE_CURSOR}{t}{ascii_engine.ANSI_RESET}\n"]

    return frames, fps


# --- Request Handlers ---

class StreamHandler(tornado.web.RequestHandler):
    """
    Zero-latency chunked stream handler.
    Pulls from LRU cache / SQLite and records analytics.
    """
    async def get(self, slug):
        slug = slug.strip("/").lower()
        if not slug:
            self.redirect("/")
            return

        anim = db.get_animation(slug)
        if not anim:
            self.set_status(404)
            self.set_header("Content-Type", "text/plain; charset=utf-8")
            self.write(f"Animation '{slug}' not found.\nExplore animations at: http://{self.request.host}/\n")
            return

        user_agent = self.request.headers.get("User-Agent", "").lower()
        is_terminal = any(term in user_agent for term in ["curl", "wget", "httpie", "powershell", "fetch"])
        force_raw = self.get_query_argument("raw", "0") == "1"

        if not is_terminal and not force_raw:
            self.redirect(f"/viewer?slug={slug}")
            return

        # Prepare anti-buffering chunked stream
        self.set_header("Content-Type", "text/plain; charset=utf-8")
        self.set_header("Transfer-Encoding", "chunked")
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate, no-transform")
        self.set_header("Pragma", "no-cache")
        self.set_header("X-Accel-Buffering", "no")
        self.set_header("Connection", "keep-alive")

        frames = anim.get("frames", [])
        if not frames:
            self.write("No frames found.\n")
            return

        # Record view analytics (buffered in-memory)
        db.record_view(slug)

        fps = anim.get("fps", 12)
        delay = 1.0 / max(1, fps)
        idx = 0

        self.write(f"{ascii_engine.ANSI_CLEAR}{ascii_engine.ANSI_HIDE_CURSOR}")
        await self.flush()

        try:
            while True:
                self.write(frames[idx])
                await self.flush()
                await asyncio.sleep(delay)
                idx = (idx + 1) % len(frames)
        except (tornado.iostream.StreamClosedError, asyncio.CancelledError):
            pass
        finally:
            try:
                self.write(f"{ascii_engine.ANSI_SHOW_CURSOR}{ascii_engine.ANSI_RESET}\n")
                await self.flush()
            except Exception:
                pass


class ViewerHandler(tornado.web.RequestHandler):
    """Serves the CRT Web Terminal Player."""
    def get(self):
        self.render(os.path.join(STATIC_DIR, "viewer.html"))


class StudioHandler(tornado.web.RequestHandler):
    """Serves the Interactive ASCII Studio & Creator."""
    def get(self):
        self.render(os.path.join(STATIC_DIR, "index.html"))


class HealthHandler(tornado.web.RequestHandler):
    """Healthcheck endpoint for cloud load balancers and orchestrators."""
    def get(self):
        stats = db.get_stats()
        self.set_header("Content-Type", "application/json")
        self.write({
            "status": "healthy",
            "timestamp": time.time(),
            "total_animations": stats["total_animations"],
            "total_views": stats["total_views"]
        })


class ApiStatsHandler(tornado.web.RequestHandler):
    """Returns global platform statistics."""
    def get(self):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(db.get_stats()))


class ApiListHandler(tornado.web.RequestHandler):
    """Paginated, searchable list of animations with view counts."""
    def get(self):
        host = self.request.host
        search = self.get_query_argument("q", self.get_query_argument("search", None))
        sort_by = self.get_query_argument("sort", "views")
        limit = min(100, max(1, int(self.get_query_argument("limit", "50"))))
        offset = max(0, int(self.get_query_argument("offset", "0")))

        animations = db.list_animations(limit=limit, offset=offset, search=search, sort_by=sort_by)
        for item in animations:
            item["curl_cmd"] = f"curl -s http://{host}/{item['slug']}"
            item["url"] = f"http://{host}/{item['slug']}"

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "animations": animations,
            "stats": db.get_stats(),
        }))


class ApiAnimationHandler(tornado.web.RequestHandler):
    """Returns full animation data for a slug."""
    def get(self, slug):
        slug = slug.strip("/").lower()
        anim = db.get_animation(slug)
        if not anim:
            self.set_status(404)
            self.write({"error": "Animation not found"})
            return

        host = self.request.host
        resp = dict(anim)
        resp["curl_cmd"] = f"curl -s http://{host}/{slug}"
        resp["url"] = f"http://{host}/{slug}"
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(resp))


class ApiUploadHandler(tornado.web.RequestHandler):
    """
    Non-blocking async media processing pipeline.
    Accepts image/GIF, bakes into zlib-compressed ANSI frames, and saves to SQLite.
    """
    async def post(self):
        try:
            slug = self.get_body_argument("slug", "").strip().lower()
            title = self.get_body_argument("title", "").strip()
            mode = self.get_body_argument("mode", "halfblock")
            effect = self.get_body_argument("effect", "scanner")
            width = int(self.get_body_argument("width", "54"))
            fps = int(self.get_body_argument("fps", "12"))
            contrast = float(self.get_body_argument("contrast", "1.0"))
            brightness = float(self.get_body_argument("brightness", "1.0"))

            # Normalize or auto-generate slug
            if not slug:
                slug = generate_random_slug()
            slug = "".join(c for c in slug if c.isalnum() or c in "-_")
            if not title:
                title = slug.replace("-", " ").capitalize()

            files = self.request.files.get("file")
            frames = []

            body_bytes = None
            if files and len(files) > 0:
                upload_file = files[0]
                body_bytes = upload_file["body"]

            loop = tornado.ioloop.IOLoop.current()
            frames, fps = await loop.run_in_executor(
                EXECUTOR,
                process_uploaded_media,
                body_bytes, width, mode, effect, contrast, brightness
            )

            if not frames:
                self.set_status(400)
                self.write({"error": "Failed to generate frames from input"})
                return

            # Save to SQLite with zlib compression
            db.save_animation(slug, title, fps, width, mode, effect, frames)

            host = self.request.host
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({
                "success": True,
                "slug": slug,
                "title": title,
                "curl_cmd": f"curl -s http://{host}/{slug}",
                "url": f"http://{host}/{slug}",
                "total_frames": len(frames),
                "fps": fps
            }))

        except Exception as e:
            self.set_status(500)
            self.write({"error": str(e)})


def make_app():
    return tornado.web.Application([
        (r"/", StudioHandler),
        (r"/health", HealthHandler),
        (r"/viewer", ViewerHandler),
        (r"/api/stats", ApiStatsHandler),
        (r"/api/list", ApiListHandler),
        (r"/api/animation/(.*)", ApiAnimationHandler),
        (r"/api/upload", ApiUploadHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": STATIC_DIR}),
        (r"/(.*)", StreamHandler),
    ], template_path=STATIC_DIR)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    init_default_animations()
    app = make_app()

    # Flush view analytics every 5 seconds
    tornado.ioloop.PeriodicCallback(db.flush_views_to_db, 5000).start()

    for p in range(port, port + 10):
        try:
            app.listen(p)
            print("=" * 60)
            print(f" [ASCII LIVE ART] Server running on http://localhost:{p}")
            print(f" -> Web Studio & Generator: http://localhost:{p}/")
            print(f" -> Stream in Terminal:     curl -s http://localhost:{p}/art")
            print("=" * 60)
            break
        except OSError:
            print(f"[WARN] Port {p} is in use, trying {p+1}...")

    tornado.ioloop.IOLoop.current().start()
