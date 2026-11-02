# 🌐 100% Free Cloud Hosting Guide for ASCII.LIVE PRO

This project is configured out-of-the-box for **100% Free 24/7 Hosting** on leading cloud platforms.

Because terminal streaming requires **chunked HTTP streaming** (`Transfer-Encoding: chunked`), we have pre-configured anti-proxy buffering headers (`X-Accel-Buffering: no`, `Cache-Control: no-transform`) so animations stream with zero lag.

---

## 🏆 Option 1: Render.com (Recommended — Easiest & 100% Free)

Render gives you **750 free hours every month** (enough to run 24/7) with free automatic SSL (`https://your-app.onrender.com`).

### Steps:
1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Deploy ASCII.LIVE PRO"
   git branch -M main
   git remote add origin https://github.com/<your-username>/ascii-live-pro.git
   git push -u origin main
   ```
2. Go to **[render.com](https://render.com)** and sign in with GitHub (Free).
3. Click **"New +"** → **"Web Service"**.
4. Select your GitHub repository.
5. Render will automatically read `render.yaml` or fill in:
   * **Name:** `ascii-live-pro` (or your choice)
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python server.py`
   * **Instance Type:** `Free`
6. Click **"Create Web Service"**.

In ~2 minutes, your live URL will be active:
```bash
# Anyone in the world can now run:
curl -s https://ascii-live-pro.onrender.com/ciarl
```

---

## 🚀 Option 2: Koyeb (100% Free Nano Instance)

Koyeb offers high-performance free edge hosting with native chunked streaming.

### Steps:
1. Sign up for free at **[koyeb.com](https://www.koyeb.com)**.
2. Click **"Create App"** → **"GitHub"**.
3. Select your repository.
4. Koyeb detects the `Dockerfile` automatically.
5. Choose the **Free Eco (Nano)** instance.
6. Click **"Deploy"**.

Your live URL: `https://<your-app>.koyeb.app/ciarl`

---

## 🤗 Option 3: Hugging Face Spaces (100% Free 16GB RAM Docker)

Hugging Face allows unlimited free public Docker Spaces with 16GB RAM.

### Steps:
1. Go to **[huggingface.co/spaces](https://huggingface.co/spaces)**.
2. Click **"Create new Space"**.
3. Space SDK: Select **Docker** (Blank).
4. Push your files (`Dockerfile`, `server.py`, `ascii_engine.py`, `static/`, etc.) to the Space git repo.
5. Hugging Face builds and boots the container in 60 seconds!

---

## ⚡ Option 4: Instant Public URL (0 Signup, 0 Install, Test in 5 Seconds)

Want to give a friend a live link **right now** directly from your computer without setting up a cloud account?

1. Make sure your local server is running (`start.bat`).
2. Double-click [`instant_public_tunnel.bat`](file:///d:/KAWACH%20AI/instant_public_tunnel.bat).
3. It opens an instant free SSH tunnel via `serveo.net` and gives you a temporary HTTPS URL (e.g., `https://ciarl-stream.serveo.net`).
4. Anyone can run:
   ```bash
   curl -s https://<assigned-url>.serveo.net/ciarl
   ```

---

## 🔒 Cloud Readiness Checklist (Already Configured)

* [x] **Dynamic Port:** Server reads `os.environ.get("PORT", 8080)` for cloud orchestrators.
* [x] **Anti-Buffering:** Emits `X-Accel-Buffering: no` so cloud load balancers and Cloudflare won't buffer stream chunks.
* [x] **Health Check:** `/health` endpoint configured for cloud auto-healing and zero downtime.
* [x] **HTTPS Protocol Auto-Detection:** UI automatically matches whether the site is accessed via `http` or `https` and formats the `curl` command.
* [x] **Production Docker Container:** Multi-stage slim image (`Dockerfile`) ready for any container platform.

