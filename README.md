# 🛡️ ASCII.LIVE PRO - Real-Time Terminal Animation Studio

An advanced, high-performance ASCII live streaming server and studio inspired by `ascii.live` and `parrot.live`.

Pre-loaded with the **CIARL Cyber Shield** logo, 3D mathematical spinning donut, Demoscene Doom fire, and an interactive Web Studio to upload your own images/GIFs and generate shareable `curl` links for anyone to stream in real time.

---

## ⚡ Quick Start

### 1. Launch the Server
Double-click `start.bat` or run:
```bash
python server.py 8080
```

### 2. Stream into Any Terminal
Open your terminal (PowerShell, Command Prompt, macOS Terminal, Linux Bash/Zsh) and run:
```bash
# Stream the CIARL Cyber Shield Laser Scanner
curl -s http://localhost:8080/ciarl

# Stream the CIARL Golden Energy Pulse
curl -s http://localhost:8080/ciarl-pulse

# Stream the 3D Mathematical Spinning Donut
curl -s http://localhost:8080/donut

# Stream the Demoscene Doom Fire
curl -s http://localhost:8080/fire
```

### 3. Open the Interactive Web Studio
Open your browser to:
```
http://localhost:8080/
```
* **Drag & Drop** any image (PNG, JPG) or animated GIF.
* **Choose Effect:** Laser Scanner, Golden Pulse, Matrix Rain, or Cyberpunk Glitch.
* **Choose Render Engine:** Ultra-Res Half-Block (24-bit Truecolor), Classic ASCII, or Matrix Code.
* **1-Click Publish:** Generates a custom slug and gives you a `curl` command that anyone on your network can run immediately!

### 4. CRT Web Terminal Player
If a friend or coworker doesn't have a terminal open, they can view the animation in an authentic retro CRT monitor:
```
http://localhost:8080/viewer?slug=ciarl
```

---

## 💻 Offline Terminal Player (No Server Needed)
You can also run animations directly in your terminal without starting the HTTP server:
```bash
python play_ascii.py ciarl
python play_ascii.py ciarl-pulse
python play_ascii.py donut
python play_ascii.py fire
```

---

## 🛠️ Architecture & Under the Hood

```
[ Real Terminal ]   <--- (HTTP Chunked ANSI Stream) ---   [ Tornado Server (server.py) ]
  (curl / wget)                                                      |
       |                                                    [ In-Memory Store ]
  Interprets ANSI Codes:                                             |
  \033[H (Cursor Home)                                   [ ascii_engine.py ]
  \033[?25l (Hide Cursor)                                            |
  \033[38;2;R;G;Bm (24-bit RGB)                       +---------------+---------------+
                                                      |                               |
                                               [ Static Images ]               [ Animated GIFs ]
                                              Procedural Shaders:              Extracts frames &
                                              - Laser Scanner                  maintains native
                                              - Gold Pulse                     millisecond timing
                                              - Matrix Rain
                                              - Cyber Glitch
```

* **Chunked Transfer Encoding:** Server streams text chunks continuously over HTTP without buffering.
* **Half-Block Ultra-Resolution (`▀` / `▄`):** Uses Unicode upper/lower half-blocks with dual 24-bit RGB foreground and background codes for 2x vertical resolution.
* **Smart User-Agent Routing:** `curl` gets raw ANSI stream, web browsers get the interactive CRT Player.

