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

def convert_image_to_halfblock(img, width=54, contrast=1.0, brightness=1.0):
    img = img.convert("RGBA")
    if contrast != 1.0:
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(contrast)
    if brightness != 1.0:
        enh = ImageEnhance.Brightness(img)
        img = enh.enhance(brightness)

    orig_w, orig_h = img.size
    aspect = orig_h / orig_w
    height = int(width * aspect)
    if height % 2 != 0:
        height += 1

    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    lines = []

    for y in range(0, height, 2):
        line = ""
        cur_fg = None
        cur_bg = None

        for x in range(width):
            r1, g1, b1, a1 = resized.getpixel((x, y))
            r2, g2, b2, a2 = resized.getpixel((x, y + 1))

            top_solid = a1 > 40
            bot_solid = a2 > 40

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


def convert_image_to_ascii(img, width=54, char_set=SIMPLE_CHARS, contrast=1.0, brightness=1.0):
    img = img.convert("RGBA")
    if contrast != 1.0:
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(contrast)
    if brightness != 1.0:
        enh = ImageEnhance.Brightness(img)
        img = enh.enhance(brightness)

    orig_w, orig_h = img.size
    height = int(width * (orig_h / orig_w) * 0.48)
    if height < 1:
        height = 1

    resized = img.resize((width, height), Image.Resampling.LANCZOS)
    lines = []
    num_chars = len(char_set)

    for y in range(height):
        line = ""
        cur_fg = None
        for x in range(width):
            r, g, b, a = resized.getpixel((x, y))
            if a < 40:
                if cur_fg is not None:
                    line += ANSI_RESET
                    cur_fg = None
                line += " "
            else:
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
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
    orig_w, orig_h = base.size
    aspect = orig_h / max(1, orig_w)
    if mode == "halfblock":
        height = int(width * aspect)
        if height % 2 != 0:
            height += 1
    else:
        height = max(4, int(width * aspect * 0.5))
    height = max(4, min(100, height))
    return base.resize((width, height), Image.Resampling.LANCZOS)


def generate_scanner_frames(img, width=54, mode="halfblock", num_frames=16):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        progress = (k / num_frames) * 2 * math.pi
        scan_ratio = 0.5 - 0.5 * math.cos(progress)
        scan_y = int(scan_ratio * h)

        frame_img = base.copy()
        pixels = frame_img.load()
        band = max(2, int(h * 0.12))

        for y in range(h):
            dist = abs(y - scan_y)
            if dist < band:
                intensity = 1.0 - (dist / band)
                boost = int(140 * intensity)
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if a > 30:
                        nr = min(255, r + boost)
                        ng = min(255, g + boost)
                        nb = min(255, b + int(boost * 0.5))
                        pixels[x, y] = (nr, ng, nb, a)
            else:
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if a > 30:
                        pixels[x, y] = (int(r * 0.88), int(g * 0.88), int(b * 0.88), a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=SIMPLE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_pulse_frames(img, width=54, mode="halfblock", num_frames=16):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        phase = (k / num_frames) * 2 * math.pi
        pulse = 0.75 + 0.35 * math.sin(phase)

        frame_img = base.copy()
        pixels = frame_img.load()

        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a > 30:
                    nr = min(255, int(r * pulse * 1.1))
                    ng = min(255, int(g * pulse * 1.05))
                    nb = min(255, int(b * pulse * 0.85))
                    pixels[x, y] = (nr, ng, nb, a)

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=SIMPLE_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_matrix_frames(img, width=54, mode="halfblock", num_frames=18):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []
    drops = [random.randint(0, h) for _ in range(max(1, w // 4))]

    for k in range(num_frames):
        frame_img = base.copy()
        pixels = frame_img.load()

        for col_idx in range(len(drops)):
            drops[col_idx] = (drops[col_idx] + int(h * 0.12)) % max(1, h)
            x_pos = min(w - 1, col_idx * 4 + 2)
            y_head = drops[col_idx]

            for tail in range(min(8, h)):
                y_pos = (y_head - tail) % max(1, h)
                intensity = max(0.0, 1.0 - (tail / 8.0))
                r, g, b, a = pixels[x_pos, y_pos]
                if a > 30:
                    pixels[x_pos, y_pos] = (
                        min(255, int(r + 100 * intensity)),
                        min(255, int(g + 180 * intensity)),
                        min(255, int(b + 50 * intensity)),
                        a
                    )

        if mode == "halfblock":
            text = convert_image_to_halfblock(frame_img, width=width)
        else:
            text = convert_image_to_ascii(frame_img, width=width, char_set=BINARY_CHARS)

        frames.append(f"{ANSI_HOME}{ANSI_HIDE_CURSOR}{text}{ANSI_RESET}\n")

    return frames


def generate_glitch_frames(img, width=54, mode="halfblock", num_frames=16):
    base = prepare_animation_base(img, width=width, mode=mode)
    w, h = base.size
    frames = []

    for k in range(num_frames):
        frame_img = base.copy()
        pixels = frame_img.load()

        if k % 3 == 0:
            glitch_y = random.randint(max(0, h // 6), max(1, h - h // 6))
            glitch_h = random.randint(1, max(2, h // 10))
            shift_x = random.randint(-4, 4)

            for y in range(glitch_y, min(h, glitch_y + glitch_h)):
                row_pixels = [pixels[x, y] for x in range(w)]
                for x in range(w):
                    src_x = (x - shift_x) % w
                    pixels[x, y] = row_pixels[src_x]

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
