import math
import random
from PIL import Image, ImageSequence, ImageEnhance

# Security: Limit maximum pixels to prevent decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 16_000_000
MAX_GIF_FRAMES = 60

# --- ANSI Utilities ---

def ansi_rgb_fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def ansi_rgb_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"

ANSI_RESET = "\033[0m"
ANSI_HOME = "\033[H"
ANSI_CLEAR = "\033[2J"
ANSI_HIDE_CURSOR = "\033[?25l"
ANSI_SHOW_CURSOR = "\033[?25h"

DENSE_CHARS = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
SIMPLE_CHARS = " .:-=+*#%@"
BLOCK_CHARS = " ░▒▓█"
BINARY_CHARS = " 01"

# --- Flagship Animated ASCII Art Banner ---

def generate_flagship_art_frames(num_frames=20):
    """
    Procedural flagship animation for ASCII Live Art.
    Features an oscillating golden shimmer wave with animated audio/equalizer bars.
    """
    banner = [
        "  █████╗ ███████╗ ██████╗██╗██╗    ██╗     ██╗██╗   ██╗███████╗",
        " ██╔══██╗██╔════╝██╔════╝██║██║    ██║     ██║██║   ██║██╔════╝",
        " ███████║███████╗██║     ██║██║    ██║     ██║██║   ██║█████╗  ",
        " ██╔══██║╚════██║██║     ██║██║    ██║     ██║╚██╗ ██╔╝██╔══╝  ",
        " ██║  ██║███████║╚██████╗██║██║    ███████╗██║ ╚████╔╝ ███████╗",
        " ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝    ╚══════╝╚═╝  ╚═══╝  ╚══════╝",
        "      ═══[ A S C I I   L I V E   A R T   S T R E A M ]═══      "
    ]
    frames = []
    w = max(len(line) for line in banner) + 4
    for k in range(num_frames):
        phase = (k / num_frames) * 2 * math.pi
        lines = []
        border_top = "┌" + "─" * (w - 2) + "┐"
        border_bot = "└" + "─" * (w - 2) + "┘"
        lines.append(f"\033[38;2;120;120;140m{border_top}\033[0m")
        for y, row in enumerate(banner):
            line = "│ "
            for x, char in enumerate(row):
                if char != " ":
                    r = int(220 + 35 * math.sin(phase + x * 0.15))
                    g = int(170 + 60 * math.sin(phase + x * 0.15 + 1.0))
                    b = int(40 + 30 * math.sin(phase + x * 0.15 + 2.0))
                    line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
                else:
                    line += " "
            line += " │"
            lines.append(line)
        eq_line = "│ "
        for bar in range(w - 4):
            # Smooth neon cyber-wave with fixed 1ch width character (zero fluctuation)
            val = 0.5 + 0.5 * math.sin(phase * 2.0 + bar * 0.28)
            r = int(20 + 220 * (val ** 1.6))
            g = int(140 + 95 * val)
            b = int(245 - 190 * val)
            eq_line += f"\033[38;2;{r};{g};{b}m▀\033[0m"
        eq_line += " │"
        lines.append(eq_line)
        lines.append(f"\033[38;2;120;120;140m{border_bot}\033[0m")
        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}" + "\n".join(lines) + f"{ANSI_RESET}\n")
    return frames

# --- Image Conversion to ANSI Frames ---

def is_light_background(img_rgba):
    """Detects if image has a solid white or near-white background canvas."""
    w, h = img_rgba.size
    if w < 4 or h < 4:
        return False
    corners = [
        img_rgba.getpixel((0, 0)),
        img_rgba.getpixel((w - 1, 0)),
        img_rgba.getpixel((0, h - 1)),
        img_rgba.getpixel((w - 1, h - 1))
    ]
    # Check if all 4 corners are opaque and near-white (luminance >= 238)
    return all(a > 200 and (r + g + b) // 3 >= 238 for r, g, b, a in corners)


def convert_image_to_halfblock(img, width=54, contrast=1.0, brightness=1.0):
    img = img.convert("RGBA")
    if contrast != 1.0:
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(contrast)
    if brightness != 1.0:
        enh = ImageEnhance.Brightness(img)
        img = enh.enhance(brightness)

    orig_w, orig_h = img.size
    aspect = orig_h / max(1, orig_w)
    # Clamp height so it fits within standard 24-line terminals (44-46 halfblock rows = 22-23 text lines)
    height = max(8, min(46, int(width * aspect)))
    if height % 2 != 0:
        height += 1

    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    light_bg = is_light_background(resized)
    lines = []

    for y in range(0, height, 2):
        line = ""
        cur_fg = None
        cur_bg = None

        for x in range(width):
            r1, g1, b1, a1 = resized.getpixel((x, y))
            r2, g2, b2, a2 = resized.getpixel((x, y + 1))

            # Smart background detection: clear near-white canvas
            top_bg = light_bg and (r1 + g1 + b1) // 3 >= 236
            bot_bg = light_bg and (r2 + g2 + b2) // 3 >= 236

            top_solid = a1 > 40 and not top_bg
            bot_solid = a2 > 40 and not bot_bg

            # If black subject/drawing on white background, illuminate as neon gold
            if light_bg and top_solid and (r1 + g1 + b1) // 3 < 45:
                r1, g1, b1 = 255, 215, 0
            if light_bg and bot_solid and (r2 + g2 + b2) // 3 < 45:
                r2, g2, b2 = 255, 215, 0

            if not top_solid and not bot_solid:
                if cur_fg is not None or cur_bg is not None:
                    line += ANSI_RESET
                    cur_fg, cur_bg = None, None
                line += " "
            elif top_solid and not bot_solid:
                if cur_bg is not None:
                    line += "\033[49m"
                    cur_bg = None
                if cur_fg != (r1, g1, b1):
                    line += ansi_rgb_fg(r1, g1, b1)
                    cur_fg = (r1, g1, b1)
                line += "▀"
            elif not top_solid and bot_solid:
                if cur_bg is not None:
                    line += "\033[49m"
                    cur_bg = None
                if cur_fg != (r2, g2, b2):
                    line += ansi_rgb_fg(r2, g2, b2)
                    cur_fg = (r2, g2, b2)
                line += "▄"
            else:
                if cur_fg != (r1, g1, b1):
                    line += ansi_rgb_fg(r1, g1, b1)
                    cur_fg = (r1, g1, b1)
                if cur_bg != (r2, g2, b2):
                    line += ansi_rgb_bg(r2, g2, b2)
                    cur_bg = (r2, g2, b2)
                line += "▀"

        if cur_fg is not None or cur_bg is not None:
            line += ANSI_RESET
        lines.append(line)

    return "\n".join(lines)


def convert_image_to_ascii(img, width=54, char_set=None, contrast=1.0, brightness=1.0):
    if char_set is None:
        char_set = DENSE_CHARS
    img = img.convert("RGBA")
    if contrast != 1.0:
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(contrast)
    if brightness != 1.0:
        enh = ImageEnhance.Brightness(img)
        img = enh.enhance(brightness)

    orig_w, orig_h = img.size
    aspect = orig_h / max(1, orig_w)
    # Clamp height to fit within standard 24-line terminals (max 22 lines)
    height = max(6, min(22, int(width * aspect * 0.48)))

    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    light_bg = is_light_background(resized)
    lines = []
    num_chars = len(char_set)

    for y in range(height):
        line = ""
        cur_fg = None
        for x in range(width):
            r, g, b, a = resized.getpixel((x, y))
            is_bg = a < 40 or (light_bg and (r + g + b) // 3 >= 236)

            if is_bg:
                if cur_fg is not None:
                    line += ANSI_RESET
                    cur_fg = None
                line += " "
            else:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                # Dark subject on white canvas: invert and colorize with golden neon
                if light_bg and gray < 50:
                    r, g, b = 255, 215, 0
                    gray = 220

                char_idx = min(num_chars - 1, max(0, gray * num_chars // 256))
                char = char_set[char_idx]

                if cur_fg != (r, g, b):
                    line += ansi_rgb_fg(r, g, b)
                    cur_fg = (r, g, b)
                line += char

        if cur_fg is not None:
            line += ANSI_RESET
        lines.append(line)

    return "\n".join(lines)


# --- Procedural Animation Generators for Static Images ---

def prepare_animation_base(img, width=54, mode="halfblock"):
    """Pre-scales image to target terminal dimensions before effect loops for a 300x performance boost."""
    base = img.convert("RGBA")

    # Auto-enhance contrast and sharpness so details and lines pop in ASCII
    try:
        enh_con = ImageEnhance.Contrast(base)
        base = enh_con.enhance(1.25)
        enh_shp = ImageEnhance.Sharpness(base)
        base = enh_shp.enhance(1.4)
    except Exception:
        pass

    orig_w, orig_h = base.size
    aspect = orig_h / max(1, orig_w)
    if mode == "halfblock":
        # 1 character cell is 2 vertical pixels; clamp to max 46 pixels (23 text lines)
        height = max(8, min(46, int(width * aspect)))
        if height % 2 != 0:
            height += 1
    else:
        # Standard character cell aspect ratio ~2:1; clamp to max 22 lines
        height = max(6, min(22, int(width * aspect * 0.48)))

    return base.resize((width, height), Image.Resampling.LANCZOS)


def generate_scanner_frames(img, width=54, mode="halfblock", num_frames=18):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        progress = (k / num_frames) * 2 * math.pi
        scan_ratio = 0.5 - 0.5 * math.cos(progress)
        scan_y = int(scan_ratio * (h - 1))

        frame_img = base.copy()
        pixels = frame_img.load()
        band = max(2, int(h * 0.18))

        for y in range(h):
            dist = abs(y - scan_y)
            if dist < band:
                intensity = 1.0 - (dist / band)
                boost = int(180 * intensity)
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if a > 30:
                        nr = min(255, int(r + boost * 0.85))
                        ng = min(255, int(g + boost * 0.95))
                        nb = min(255, int(b + boost * 1.1))
                        pixels[x, y] = (nr, ng, nb, a)
            else:
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if a > 30:
                        pixels[x, y] = (int(r * 0.85), int(g * 0.85), int(b * 0.85), a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=DENSE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_pulse_frames(img, width=54, mode="halfblock", num_frames=18):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        phase = (k / num_frames) * 2 * math.pi

        frame_img = base.copy()
        pixels = frame_img.load()

        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a > 30:
                    wave = 0.5 + 0.5 * math.sin(phase * 2.0 + (x / max(1, w)) * 3.5 + (y / max(1, h)) * 2.0)
                    pulse_r = min(255, int(r * (0.8 + 0.45 * wave) + 40 * wave))
                    pulse_g = min(255, int(g * (0.75 + 0.4 * wave) + 25 * wave))
                    pulse_b = min(255, int(b * (0.65 + 0.25 * wave)))
                    pixels[x, y] = (pulse_r, pulse_g, pulse_b, a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=DENSE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_matrix_frames(img, width=54, mode="halfblock", num_frames=20):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []
    num_cols = max(4, w // 3)
    col_x = [int(i * (w / num_cols)) for i in range(num_cols)]
    drops = [(random.randint(0, h), random.randint(3, 8)) for _ in range(num_cols)]

    for k in range(num_frames):
        frame_img = base.copy()
        pixels = frame_img.load()

        for i, (y_head, tail_len) in enumerate(drops):
            current_head = (y_head + int(k * 1.8)) % max(1, h)
            x_pos = min(w - 1, col_x[i])

            for t in range(tail_len):
                y_pos = (current_head - t) % max(1, h)
                intensity = 1.0 - (t / max(1, tail_len))
                r, g, b, a = pixels[x_pos, y_pos]
                if a > 30:
                    if t == 0:
                        pixels[x_pos, y_pos] = (235, 255, 240, a)
                    else:
                        mg = min(255, int(g * 0.5 + 220 * intensity))
                        mr = min(255, int(r * 0.3 + 30 * intensity))
                        mb = min(255, int(b * 0.3 + 50 * intensity))
                        pixels[x_pos, y_pos] = (mr, mg, mb, a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=BINARY_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_glitch_frames(img, width=54, mode="halfblock", num_frames=18):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        frame_img = base.copy()
        pixels = frame_img.load()

        if k % 2 == 1:
            glitch_y = random.randint(0, max(0, h - 3))
            glitch_h = random.randint(1, max(2, h // 5))
            shift_x = random.choice([-3, -2, 2, 3, 5])

            for y in range(glitch_y, min(h, glitch_y + glitch_h)):
                row_pixels = [pixels[x, y] for x in range(w)]
                for x in range(w):
                    rx = (x - shift_x) % w
                    cx = (x + shift_x) % w
                    r, _, _, a = row_pixels[rx]
                    _, g, b, _ = row_pixels[cx]
                    pixels[x, y] = (min(255, r + 40), g, min(255, b + 50), a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=DENSE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


# --- GIF Handler ---

def convert_gif_to_frames(gif_path, width=54, mode="halfblock", max_frames=MAX_GIF_FRAMES):
    gif = Image.open(gif_path)
    frames = []
    durations = []

    for idx, frame in enumerate(ImageSequence.Iterator(gif)):
        if idx >= max_frames:
            break
        dur = frame.info.get("duration", 100)
        durations.append(dur)
        rgba = frame.convert("RGBA")

        if mode == "halfblock":
            text = convert_image_to_halfblock(rgba, width=width)
        else:
            text = convert_image_to_ascii(rgba, width=width, char_set=SIMPLE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    avg_duration = sum(durations) / max(1, len(durations))
    delay_ms = int(avg_duration) if avg_duration > 20 else 80
    return frames, delay_ms


# --- Donut 3D Math Generator ---

def generate_donut_frames(num_frames=24, width=50, height=22):
    frames = []
    for k in range(num_frames):
        A = (k / num_frames) * 2 * math.pi
        B = (k / num_frames) * math.pi

        cosA, sinA = math.cos(A), math.sin(A)
        cosB, sinB = math.cos(B), math.sin(B)

        b = [" "] * (width * height)
        z = [0.0] * (width * height)

        for j in range(0, 628, 7):
            cosj, sinj = math.cos(j / 100), math.sin(j / 100)
            for i in range(0, 628, 2):
                sini, cosi = math.sin(i / 100), math.cos(i / 100)
                h_val = cosj + 2
                D = 1 / (sini * h_val * sinA + sinj * cosA + 5)
                t = sini * h_val * cosA - sinj * sinA
                x = int(width / 2 + 30 * D * (cosi * h_val * cosB - t * sinB))
                y = int(height / 2 + 15 * D * (cosi * h_val * sinB + t * cosB))
                o = x + width * y
                N = int(8 * ((sinj * sinA - sini * cosj * cosA) * cosB - sini * cosj * sinA - sinj * cosA - cosi * cosj * sinB))

                if 0 <= y < height and 0 <= x < width and D > z[o]:
                    z[o] = D
                    idx = max(0, min(11, N))
                    char = ".,-~:;=!*#$@"[idx]
                    color_code = 196 + idx * 5
                    b[o] = f"\033[38;5;{color_code}m{char}\033[0m"

        lines = ["".join(b[row * width : (row + 1) * width]) for row in range(height)]
        frame_text = "\n".join(lines)
        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{frame_text}{ANSI_RESET}\n")

    return frames
