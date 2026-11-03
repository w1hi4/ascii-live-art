import os
import sys
import re
import json
import time
import math
import random
import asyncio
import tempfile
import string
import threading
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

RESERVED_SLUGS = frozenset([
    "api", "health", "viewer", "static", "favicon", "favicon.ico", 
    "art", "donut", "fire", "admin", "login", "root", "system"
])

# --- Security: Rate Limiting Engine ---

class RateLimiter:
    """Thread-safe sliding-window IP rate limiter to protect against DoS and spam."""
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window = window_seconds
        self.history = {}
        self.lock = threading.Lock()

    def is_allowed(self, ip):
        now = time.time()
        with self.lock:
            timestamps = self.history.get(ip, [])
            cutoff = now - self.window
            valid = [t for t in timestamps if t > cutoff]
            if len(valid) >= self.max_requests:
                self.history[ip] = valid
                return False
            valid.append(now)
            self.history[ip] = valid
            return True

UPLOAD_LIMITER = RateLimiter(max_requests=30, window_seconds=60) # 30 uploads per min per IP
API_LIMITER = RateLimiter(max_requests=180, window_seconds=60)   # 180 requests per min per IP

def get_client_ip(handler):
    """Safely extracts real client IP behind reverse proxies (Render, Cloudflare, Nginx)."""
    x_forwarded = handler.request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return handler.request.headers.get("X-Real-IP", handler.request.remote_ip or "127.0.0.1")

def get_request_proto(handler):
    """Accurately determines protocol (HTTPS / HTTP) behind reverse proxies."""
    proto = handler.request.headers.get("X-Forwarded-Proto")
    if proto:
        return proto.split(",")[0].strip()
    host = handler.request.host.lower()
    if "localhost" not in host and "127.0.0.1" not in host:
        return "https"
    return handler.request.protocol or "http"

# --- Security: Slug Generator & Validator ---

def generate_random_slug(length=6):
    """Generates a clean, unique, URL-friendly slug."""
    adjectives = ["cyber", "retro", "quantum", "neon", "cosmic", "hyper", "glitch", "matrix", "pixel", "synth"]
    nouns = ["wave", "pulse", "stream", "core", "grid", "beam", "flux", "void", "nova", "laser"]
    for _ in range(30):
        s = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(10, 99)}"
        if not db.is_slug_taken(s):
            return s
    chars = string.ascii_lowercase + string.digits
    for _ in range(30):
        s = "".join(random.choice(chars) for _ in range(length))
        if not db.is_slug_taken(s):
            return s
    return f"stream-{int(time.time())}"

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
        chars_fire = " .:-=+*#%@"
        palette = [
            (0, 0, 0), (7, 7, 7), (31, 7, 7), (47, 15, 7),
            (71, 15, 7), (87, 23, 7), (103, 31, 7), (119, 31, 7),
            (143, 39, 7), (159, 47, 7), (175, 63, 7), (191, 71, 7),
            (199, 71, 7), (223, 79, 7), (223, 87, 7), (223, 87, 7),
            (215, 95, 7), (215, 103, 15), (207, 111, 15), (207, 119, 15),
            (207, 127, 15), (207, 135, 23), (199, 135, 23), (199, 143, 23),
            (199, 151, 31), (191, 159, 31), (191, 159, 31), (191, 167, 39),
            (191, 167, 39), (191, 175, 47), (183, 175, 47), (183, 183, 47),
            (183, 183, 55), (207, 207, 111), (223, 223, 159), (239, 239, 199),
            (255, 255, 255)
        ]
        fire_buf = [0] * (w_f * h_f)
        for x in range(w_f): fire_buf[(h_f - 1) * w_f + x] = 36
        fire_frames = []
        for _ in range(24):
            for x in range(w_f):
                for y in range(1, h_f):
                    src = y * w_f + x
                    p = fire_buf[src]
                    if p == 0: fire_buf[src - w_f] = 0
                    else:
                        rnd = random.randint(0, 3)
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

# --- Security: Magic Byte & Image Payload Validation ---

def validate_image_payload(body_bytes):
    """
    Validates magic bytes, file integrity, and dimensions.
    Rejects scripts, SVGs, polyglots, and decompression bombs.
    """
    if not body_bytes or len(body_bytes) < 8:
        raise ValueError("Invalid file content: empty or truncated file.")
    
    if len(body_bytes) > 8 * 1024 * 1024:
        raise ValueError("File exceeds maximum allowed size (8MB).")

    is_png = body_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = body_bytes.startswith(b"\xff\xd8\xff")
    is_gif = body_bytes.startswith(b"GIF87a") or body_bytes.startswith(b"GIF89a")
    is_webp = body_bytes.startswith(b"RIFF") and len(body_bytes) > 12 and body_bytes[8:12] == b"WEBP"

    if not (is_png or is_jpeg or is_gif or is_webp):
        raise ValueError("Unsupported file format. Only genuine PNG, JPG, GIF, and WEBP files are permitted.")

    # Integrity check with Pillow verify
    try:
        verify_img = Image.open(BytesIO(body_bytes))
        verify_img.verify()
    except Exception:
        raise ValueError("Corrupted or malformed image data.")

    # Re-open after verify
    img = Image.open(BytesIO(body_bytes))
    w, h = img.size
    if w > 3000 or h > 3000:
        raise ValueError(f"Image dimensions ({w}x{h}) exceed maximum allowed 3000x3000 limit.")
    if w < 2 or h < 2:
        raise ValueError("Image dimensions are too small.")

    return img, is_gif

def process_uploaded_media(body_bytes, width, mode, effect, contrast, brightness):
    """Worker function executed in thread pool for CPU-heavy frame baking with security bounds."""
    if not body_bytes:
        return ascii_engine.generate_flagship_art_frames(num_frames=20), 14

    img, is_gif = validate_image_payload(body_bytes)
    frames = []
    fps = 14

    # Sanitize and clamp numeric parameters
    width = max(20, min(100, int(width)))
    contrast = max(0.2, min(3.0, float(contrast)))
    brightness = max(0.2, min(3.0, float(brightness)))
    mode = mode if mode in ("halfblock", "ascii") else "ascii"
    effect = effect if effect in ("scanner", "pulse", "matrix", "glitch") else "scanner"

    if is_gif:
        tmp_gif = os.path.join(tempfile.gettempdir(), f"upload_{time.time()}_{random.randint(1000, 9999)}.gif")
        try:
            with open(tmp_gif, "wb") as f_out:
                f_out.write(body_bytes)
            frames, gif_delay = ascii_engine.convert_gif_to_frames(
                tmp_gif, width=width, mode=mode, max_frames=ascii_engine.MAX_GIF_FRAMES
            )
            if gif_delay > 0:
                fps = max(1, min(30, int(1000 / gif_delay)))
        finally:
            if os.path.exists(tmp_gif):
                try:
                    os.remove(tmp_gif)
                except Exception:
                    pass
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

# --- Hardened Base Request Handler ---

class BaseHandler(tornado.web.RequestHandler):
    """Secure base request handler with hardened HTTP headers and sanitized error handling."""
    def set_default_headers(self):
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.set_header("X-XSS-Protection", "1; mode=block")
        self.set_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.set_header("Permissions-Policy", "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()")
        self.set_header("Content-Security-Policy", (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        ))
        self.clear_header("Server")

    def write_error(self, status_code, **kwargs):
        """Sanitized error responses without leaking tracebacks or system internals."""
        self.set_header("Content-Type", "application/json; charset=utf-8")
        msg = "An unexpected error occurred."
        if status_code == 404:
            msg = "Resource not found."
        elif status_code == 400:
            msg = "Bad request."
        elif status_code == 403:
            msg = "Forbidden."
        elif status_code == 409:
            msg = "Resource conflict."
        elif status_code == 413:
            msg = "Payload too large. Maximum upload size is 8MB."
        elif status_code == 429:
            msg = "Rate limit exceeded. Please wait a few minutes before trying again."
        
        self.finish(json.dumps({
            "success": False,
            "status": status_code,
            "error": msg
        }))

# --- Request Handlers ---

class StreamHandler(BaseHandler):
    """
    Zero-latency chunked stream handler.
    Pulls from LRU cache / SQLite and records analytics.
    """
    async def get(self, slug):
        slug = slug.strip("/").lower()
        if not slug:
            self.redirect("/")
            return

        # Sanitize slug
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        anim = db.get_animation(slug)
        if not anim:
            self.set_status(404)
            self.set_header("Content-Type", "text/plain; charset=utf-8")
            self.write(f"Animation '{slug}' not found.\nExplore active streams at: http://{self.request.host}/\n")
            return

        user_agent = self.request.headers.get("User-Agent", "").lower()
        is_terminal = any(term in user_agent for term in ["curl", "wget", "httpie", "powershell", "fetch", "python", "aiohttp", "urllib"])
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

        fps = anim.get("fps", 14)
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


class ViewerHandler(BaseHandler):
    """Serves the CRT Web Terminal Player."""
    def get(self):
        self.render(os.path.join(STATIC_DIR, "viewer.html"))


class StudioHandler(BaseHandler):
    """Serves the Interactive ASCII Studio & Creator."""
    def get(self):
        self.render(os.path.join(STATIC_DIR, "index.html"))


class HealthHandler(BaseHandler):
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


class ApiStatsHandler(BaseHandler):
    """Returns global platform statistics."""
    def get(self):
        client_ip = get_client_ip(self)
        if not API_LIMITER.is_allowed(client_ip):
            self.set_status(429)
            self.write(json.dumps({"success": False, "error": "Rate limit exceeded"}))
            return
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(db.get_stats()))


class ApiListHandler(BaseHandler):
    """Paginated, searchable list of animations with view counts."""
    def get(self):
        client_ip = get_client_ip(self)
        if not API_LIMITER.is_allowed(client_ip):
            self.set_status(429)
            self.write(json.dumps({"success": False, "error": "Rate limit exceeded"}))
            return

        host = self.request.host
        search = self.get_query_argument("q", self.get_query_argument("search", None))
        sort_by = self.get_query_argument("sort", "views")
        limit = min(db.MAX_CAPACITY, max(1, int(self.get_query_argument("limit", "50"))))
        offset = max(0, int(self.get_query_argument("offset", "0")))

        # Sanitize search term
        if search:
            search = re.sub(r"[^\w\s-]", "", search)[:50]

        animations = db.list_animations(limit=limit, offset=offset, search=search, sort_by=sort_by)
        proto = get_request_proto(self)
        for item in animations:
            item["curl_cmd"] = f"curl -sL {proto}://{host}/{item['slug']}"
            item["url"] = f"{proto}://{host}/{item['slug']}"

        self.set_header("Content-Type", "application/json")
        self.write(json.dumps({
            "animations": animations,
            "stats": db.get_stats(),
            "capacity": db.get_capacity_stats()
        }))


class ApiAnimationHandler(BaseHandler):
    """Returns full animation data for a slug."""
    def get(self, slug):
        client_ip = get_client_ip(self)
        if not API_LIMITER.is_allowed(client_ip):
            self.set_status(429)
            self.write(json.dumps({"success": False, "error": "Rate limit exceeded"}))
            return

        slug = re.sub(r"[^a-z0-9-]", "", slug.strip("/").lower())
        anim = db.get_animation(slug)
        if not anim:
            self.set_status(404)
            self.write({"error": "Animation not found"})
            return

        host = self.request.host
        proto = get_request_proto(self)
        resp = dict(anim)
        resp["curl_cmd"] = f"curl -sL {proto}://{host}/{slug}"
        resp["url"] = f"{proto}://{host}/{slug}"
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(resp))


class ApiUploadHandler(BaseHandler):
    """
    Non-blocking async media processing pipeline with defense-in-depth security.
    Validates magic bytes, rate limits IPs, enforces unique slugs, and retention limits.
    """
    async def post(self):
        # 1. IP Rate Limiting Check
        client_ip = get_client_ip(self)
        if not UPLOAD_LIMITER.is_allowed(client_ip):
            self.set_status(429)
            self.write(json.dumps({
                "success": False,
                "error": "Rate limit exceeded. Maximum 6 animations per 5 minutes per IP."
            }))
            return

        try:
            slug = self.get_body_argument("slug", "").strip().lower()
            title = self.get_body_argument("title", "").strip()
            mode = self.get_body_argument("mode", "halfblock")
            effect = self.get_body_argument("effect", "scanner")
            width = self.get_body_argument("width", "54")
            fps = self.get_body_argument("fps", "14")
            contrast = self.get_body_argument("contrast", "1.0")
            brightness = self.get_body_argument("brightness", "1.0")

            # 2. Strict Slug Validation (Anti-Path Traversal, Anti-Injection)
            if slug:
                slug = re.sub(r"[^a-z0-9-]", "", slug).strip("-")
                if not re.match(r"^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$", slug) or len(slug) < 2:
                    self.set_status(400)
                    self.write(json.dumps({
                        "success": False,
                        "error": "Slug must be between 2 and 32 characters, starting and ending with alphanumeric characters (a-z, 0-9, hyphens)."
                    }))
                    return
                if slug in RESERVED_SLUGS:
                    self.set_status(400)
                    self.write(json.dumps({"success": False, "error": f"Slug '/{slug}' is a reserved system stream name."}))
                    return
                if db.is_slug_taken(slug):
                    self.set_status(409)
                    self.write(json.dumps({
                        "success": False,
                        "error": f"Slug '/{slug}' is currently occupied in the 50 active slots. All active URLs must be unique. Choose another name or wait until it cycles out."
                    }))
                    return
            else:
                slug = generate_random_slug()

            # 3. Title Sanitization (Strip ANSI escapes & control characters)
            title = re.sub(r"[\x00-\x1f\x7f-\x9f\x1b]", "", title).strip()
            title = title[:60] if title else slug.replace("-", " ").capitalize()

            # 4. File payload validation
            files = self.request.files.get("file")
            body_bytes = None
            if files and len(files) > 0:
                upload_file = files[0]
                body_bytes = upload_file["body"]
                if len(body_bytes) > 8 * 1024 * 1024:
                    self.set_status(413)
                    self.write(json.dumps({"success": False, "error": "File size exceeds 8MB limit"}))
                    return

            loop = tornado.ioloop.IOLoop.current()
            frames, fps = await loop.run_in_executor(
                EXECUTOR,
                process_uploaded_media,
                body_bytes, width, mode, effect, contrast, brightness
            )

            if not frames:
                self.set_status(400)
                self.write(json.dumps({"success": False, "error": "Failed to generate frames from input"}))
                return

            # Save to SQLite with zlib compression & enforce max 50 capacity retention
            db.save_animation(slug, title, fps, width, mode, effect, frames)

            host = self.request.host
            proto = get_request_proto(self)
            capacity_stats = db.get_capacity_stats()
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({
                "success": True,
                "slug": slug,
                "title": title,
                "curl_cmd": f"curl -sL {proto}://{host}/{slug}",
                "url": f"{proto}://{host}/{slug}",
                "total_frames": len(frames),
                "fps": fps,
                "capacity": capacity_stats
            }))

        except ValueError as ve:
            self.set_status(400)
            self.write(json.dumps({"success": False, "error": str(ve)}))
        except Exception:
            self.set_status(500)
            self.write(json.dumps({"success": False, "error": "An internal error occurred while processing media."}))


class FaviconHandler(tornado.web.RequestHandler):
    """Directly serves browser favicon requests."""
    def get(self):
        self.set_header("Content-Type", "image/x-icon")
        self.set_header("Cache-Control", "public, max-age=86400")
        ico_path = os.path.join(STATIC_DIR, "favicon.ico")
        if os.path.exists(ico_path):
            with open(ico_path, "rb") as f:
                self.write(f.read())
        else:
            self.set_status(404)


def make_app():
    return tornado.web.Application([
        (r"/", StudioHandler),
        (r"/health", HealthHandler),
        (r"/viewer", ViewerHandler),
        (r"/favicon\.ico", FaviconHandler),
        (r"/api/stats", ApiStatsHandler),
        (r"/api/list", ApiListHandler),
        (r"/api/animation/(.*)", ApiAnimationHandler),
        (r"/api/upload", ApiUploadHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": STATIC_DIR}),
        (r"/(.*)", StreamHandler),
    ], 
    template_path=STATIC_DIR,
    debug=False,
    serve_traceback=False,
    compiled_template_cache=True
    )


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
            app.listen(p, max_buffer_size=8 * 1024 * 1024)
            print("=" * 60)
            print(f" [ASCII LIVE ART] Server running on http://localhost:{p}")
            print(f" -> Web Studio & Generator: http://localhost:{p}/")
            print(f" -> Stream in Terminal:     curl -s http://localhost:{p}/art")
            print("=" * 60)
            break
        except OSError:
            print(f"[WARN] Port {p} is in use, trying {p+1}...")

    tornado.ioloop.IOLoop.current().start()
