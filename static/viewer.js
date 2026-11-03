// --- Standalone CRT Terminal Player Script ---

// ANSI to HTML Parser
function ansiToHtml(text) {
  if (!text) return "";

  // Strip cursor control codes
  let clean = text.replace(/\x1b\[\?25[lh]/g, "")
                  .replace(/\x1b\[2J/g, "")
                  .replace(/\x1b\[H/g, "");

  let html = "";
  let curFg = null;
  let curBg = null;

  const tokens = clean.split(/(\x1b\[[0-9;]*m)/g);

  for (let token of tokens) {
    if (token.startsWith("\x1b[")) {
      let code = token.slice(2, -1);
      if (code === "" || code === "0") {
        if (curFg || curBg) {
          html += "</span>";
          curFg = null;
          curBg = null;
        }
      } else {
        let parts = code.split(";").map(Number);
        let i = 0;
        while (i < parts.length) {
          if (parts[i] === 0) {
            if (curFg || curBg) {
              html += "</span>";
              curFg = null;
              curBg = null;
            }
            i++;
          } else if (parts[i] === 38 && parts[i+1] === 2) {
            curFg = `rgb(${parts[i+2]},${parts[i+3]},${parts[i+4]})`;
            i += 5;
          } else if (parts[i] === 48 && parts[i+1] === 2) {
            curBg = `rgb(${parts[i+2]},${parts[i+3]},${parts[i+4]})`;
            i += 5;
          } else if (parts[i] === 38 && parts[i+1] === 5) {
            let c = parts[i+2];
            curFg = `hsl(${c * 1.4}, 80%, 60%)`;
            i += 3;
          } else if (parts[i] === 49) {
            curBg = null;
            i++;
          } else {
            i++;
          }
        }

        let style = "";
        if (curFg) style += `color: ${curFg}; `;
        if (curBg) style += `background-color: ${curBg}; `;
        if (style) {
          html += `<span style="${style}">`;
        }
      }
    } else {
      let escaped = token
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      html += escaped;
    }
  }

  if (curFg || curBg) html += "</span>";
  return html;
}

// Toast notification
let toastTimeout = null;
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  const msgEl = document.getElementById("toastMsg") || toast;
  msgEl.textContent = message;
  toast.classList.add("show");

  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("show");
  }, 2400);
}

function copyText(text) {
  if (!text) return;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Copied command to clipboard!");
    }).catch(() => {
      fallbackCopy(text);
    });
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const area = document.createElement("textarea");
  area.value = text;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.focus();
  area.select();
  try {
    document.execCommand("copy");
    showToast("Copied command to clipboard!");
  } catch (err) {
    showToast("Failed to copy command");
  }
  document.body.removeChild(area);
}

// Viewer state
const urlParams = new URLSearchParams(window.location.search);
const slug = (urlParams.get('slug') || 'art').replace(/[^a-z0-9_-]/gi, '');
const display = document.getElementById('crtDisplay');
const curlCmd = document.getElementById('curlCmd');
const frameMeta = document.getElementById('frameMeta');
const btnPause = document.getElementById('btnPause');

let viewerFrames = [];
let viewerFps = 14;
let viewerIdx = 0;
let viewerTimer = null;
let isPlaying = true;

async function initViewer() {
  const proto = window.location.protocol;
  if (curlCmd) {
    curlCmd.textContent = `curl -sL ${proto}//${window.location.host}/${slug}`;
  }
  try {
    const res = await fetch(`/api/animation/${slug}`);
    if (!res.ok) {
      if (display) display.textContent = `Animation '${slug}' not found.`;
      if (frameMeta) frameMeta.textContent = "Not found";
      return;
    }
    const data = await res.json();
    viewerFrames = data.frames || [];
    viewerFps = data.fps || 14;
    if (frameMeta) {
      frameMeta.textContent = `${data.title} • ${data.width || 54} cols • ${viewerFps} FPS`;
    }

    startViewerLoop();
  } catch (e) {
    if (display) display.textContent = `Error loading animation: ${e.message}`;
  }
}

function startViewerLoop() {
  if (viewerTimer) clearInterval(viewerTimer);
  if (!viewerFrames || viewerFrames.length === 0) return;
  
  const delay = Math.max(20, Math.floor(1000 / viewerFps));
  viewerTimer = setInterval(() => {
    if (display && viewerFrames[viewerIdx]) {
      display.innerHTML = ansiToHtml(viewerFrames[viewerIdx]);
    }
    viewerIdx = (viewerIdx + 1) % viewerFrames.length;
  }, delay);
}

function togglePlay() {
  if (isPlaying) {
    clearInterval(viewerTimer);
    if (btnPause) btnPause.textContent = "▶️ Play";
    isPlaying = false;
  } else {
    startViewerLoop();
    if (btnPause) btnPause.textContent = "⏸️ Pause";
    isPlaying = true;
  }
}

function toggleScanlines() {
  if (display) display.classList.toggle('scanlines');
}

function copyCurl() {
  if (curlCmd) copyText(curlCmd.textContent);
}

// --- Dynamic Animated Favicon in Chrome Tab ---
function initAnimatedFavicon() {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 32;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const link = document.getElementById("dynamicFavicon") || document.querySelector("link[rel*='icon']");
  if (!link) return;

  let step = 0;
  function drawFaviconFrame() {
    if (document.hidden) return;

    ctx.clearRect(0, 0, 32, 32);

    ctx.fillStyle = "#0c1018";
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(1, 1, 30, 30, 7);
    } else {
      ctx.rect(1, 1, 30, 30);
    }
    ctx.fill();

    ctx.strokeStyle = (step % 2 === 0) ? "#ffd700" : "#38bdf8";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.strokeStyle = "#ffd700";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(8, 10);
    ctx.lineTo(15, 16);
    ctx.lineTo(8, 22);
    ctx.stroke();

    if (step % 2 === 0) {
      ctx.strokeStyle = (step === 0) ? "#22c55e" : "#38bdf8";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.moveTo(18, 22);
      ctx.lineTo(25, 22);
      ctx.stroke();
    }

    step = (step + 1) % 4;
    link.href = canvas.toDataURL("image/png");
  }

  setInterval(drawFaviconFrame, 450);
}

// Bind button listeners without inline handlers for CSP compliance
document.addEventListener('DOMContentLoaded', () => {
  initAnimatedFavicon();
  const btnCopy = document.getElementById('btnCopyCurl');
  if (btnCopy) btnCopy.addEventListener('click', copyCurl);

  const btnPauseEl = document.getElementById('btnPause');
  if (btnPauseEl) btnPauseEl.addEventListener('click', togglePlay);

  const btnScan = document.getElementById('btnToggleScanlines');
  if (btnScan) btnScan.addEventListener('click', toggleScanlines);

  // Keyboard controls
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.key === 's' || e.key === 'S') {
      toggleScanlines();
    } else if (e.key === 'c' || e.key === 'C') {
      copyCurl();
    }
  });

  initViewer();
});
