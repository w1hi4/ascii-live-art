// Standard xterm 256-color palette mapper (Exact matches for terminal RGB)
function ansi256ToRgb(code) {
  if (code < 16) {
    const std = [
      "rgb(0,0,0)", "rgb(205,0,0)", "rgb(0,205,0)", "rgb(205,205,0)",
      "rgb(0,0,238)", "rgb(205,0,205)", "rgb(0,205,205)", "rgb(229,229,229)",
      "rgb(127,127,127)", "rgb(255,0,0)", "rgb(0,255,0)", "rgb(255,255,0)",
      "rgb(92,92,255)", "rgb(255,0,255)", "rgb(0,255,255)", "rgb(255,255,255)"
    ];
    return std[code];
  }
  if (code <= 231) {
    const c = code - 16;
    const r = Math.floor(c / 36);
    const g = Math.floor((c % 36) / 6);
    const b = c % 6;
    const v = [0, 95, 135, 175, 215, 255];
    return `rgb(${v[r]},${v[g]},${v[b]})`;
  }
  const gray = 8 + (code - 232) * 10;
  return `rgb(${gray},${gray},${gray})`;
}

// Complete ANSI to HTML Parser
function ansiToHtml(text) {
  if (!text) return "";

  // Strip cursor home, clear, and visibility codes
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
          let p = parts[i];
          if (p === 0) {
            if (curFg || curBg) {
              html += "</span>";
              curFg = null;
              curBg = null;
            }
            i++;
          } else if (p >= 30 && p <= 37) {
            curFg = ansi256ToRgb(p - 30);
            i++;
          } else if (p === 39) {
            curFg = null;
            i++;
          } else if (p >= 40 && p <= 47) {
            curBg = ansi256ToRgb(p - 40);
            i++;
          } else if (p === 49) {
            curBg = null;
            i++;
          } else if (p >= 90 && p <= 97) {
            curFg = ansi256ToRgb(p - 90 + 8);
            i++;
          } else if (p >= 100 && p <= 107) {
            curBg = ansi256ToRgb(p - 100 + 8);
            i++;
          } else if (p === 38 && parts[i+1] === 5) {
            curFg = ansi256ToRgb(parts[i+2] || 0);
            i += 3;
          } else if (p === 48 && parts[i+1] === 5) {
            curBg = ansi256ToRgb(parts[i+2] || 0);
            i += 3;
          } else if (p === 38 && parts[i+1] === 2) {
            curFg = `rgb(${parts[i+2]},${parts[i+3]},${parts[i+4]})`;
            i += 5;
          } else if (p === 48 && parts[i+1] === 2) {
            curBg = `rgb(${parts[i+2]},${parts[i+3]},${parts[i+4]})`;
            i += 5;
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

// --- Toast Notification System ---
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
  }, 2800);
}

// Global copy helper
window.copyText = function(text) {
  if (!text) return;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Copied to clipboard: " + text);
    }).catch(() => {
      fallbackCopy(text);
    });
  } else {
    fallbackCopy(text);
  }
};

function fallbackCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand("copy");
    showToast("Copied to clipboard!");
  } catch (err) {
    prompt("Copy command:", text);
  }
  document.body.removeChild(ta);
}

// --- Studio State ---
let selectedFile = null;
let activeFrames = [];
let animInterval = null;
let currentFrameIdx = 0;
let currentFps = 14;

// Cache of all loaded streams for instant zero-latency filtering
let allAnimations = [];
let activeSearchQuery = "";
let serverSearchTimer = null;
let currentStreamsPage = 1;
let streamsPageSize = 4; // Default 4 streams per page to keep page compact

// Active Shell Selector: defaults to powershell on Windows, bash on Mac/Linux
const isWindowsPlatform = typeof navigator !== "undefined" && /Win/i.test(navigator.userAgent || navigator.platform);
let activeShell = "powershell";
try {
  const saved = localStorage.getItem("ascii_preferred_shell");
  if (saved) activeShell = saved;
  else activeShell = isWindowsPlatform ? "powershell" : "bash";
} catch (e) {
  activeShell = isWindowsPlatform ? "powershell" : "bash";
}

function getShellCommand(slug) {
  const proto = window.location.protocol;
  const host = window.location.host;
  const base = `${proto}//${host}/${slug}`;
  if (activeShell === "powershell") {
    return `curl.exe -sN ${base}`;
  }
  return `curl -sN ${base}`;
}

// --- DOM Elements ---
const terminalScreen = document.getElementById("terminalScreen");
const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const dropText = document.getElementById("dropText");
const btnGenerate = document.getElementById("btnGenerate");
const shareBanner = document.getElementById("shareBanner");
const shareCurl = document.getElementById("shareCurl");
const streamsBody = document.getElementById("streamsBody");
const headerStats = document.getElementById("headerStats");
const previewFps = document.getElementById("previewFps");
const searchResultsCount = document.getElementById("searchResultsCount");
const streamSearch = document.getElementById("streamSearch");
const btnSearchClear = document.getElementById("btnSearchClear");
const noResultsBox = document.getElementById("noResultsBox");
const emptyQueryText = document.getElementById("emptyQueryText");
const btnCreateFromSearch = document.getElementById("btnCreateFromSearch");
const capacityLabel = document.getElementById("capacityLabel");
const capacityBar = document.getElementById("capacityBar");
const slugStatus = document.getElementById("slugStatus");

// Input Controls
const slugInput = document.getElementById("slugInput");
const titleInput = document.getElementById("titleInput");
const modeSelect = document.getElementById("modeSelect");
const effectSelect = document.getElementById("effectSelect");

// --- Real-time Capacity UI Updater ---
function updateCapacityUI(capacity) {
  if (!capacity) return;
  const current = capacity.current || 0;
  const max = capacity.max || 50;
  if (capacityLabel) {
    capacityLabel.textContent = `${current} / ${max} SLOTS`;
  }
  if (capacityBar) {
    const pct = Math.min(100, Math.max(0, (current / max) * 100));
    capacityBar.style.width = `${pct}%`;
  }
}

// --- Live Slug Availability Checker ---
if (slugInput && slugStatus) {
  slugInput.addEventListener("input", () => {
    const raw = slugInput.value.trim().toLowerCase();
    const clean = raw.replace(/[^a-z0-9_-]/g, "");
    if (!clean) {
      slugStatus.textContent = "✓ Auto-generated";
      slugStatus.className = "slug-status-hint";
      return;
    }
    const isTaken = allAnimations.some(a => a.slug === clean) || ["art", "donut", "fire", "api", "health", "viewer"].includes(clean);
    if (isTaken) {
      slugStatus.textContent = "✗ Already taken";
      slugStatus.className = "slug-status-hint taken";
    } else {
      slugStatus.textContent = "✓ Available";
      slugStatus.className = "slug-status-hint";
    }
  });
}

// --- Animation Loop in Terminal Window ---
function playFrames(frames, fps = 14) {
  activeFrames = frames;
  currentFps = fps;
  currentFrameIdx = 0;
  if (previewFps) previewFps.textContent = `${fps} FPS`;
  restartAnimationLoop();
}

function restartAnimationLoop() {
  if (animInterval) clearInterval(animInterval);
  if (!activeFrames || activeFrames.length === 0) return;

  const delay = Math.max(20, Math.floor(1000 / currentFps));
  animInterval = setInterval(() => {
    const rawFrame = activeFrames[currentFrameIdx];
    if (terminalScreen) {
      terminalScreen.innerHTML = ansiToHtml(rawFrame);
    }
    currentFrameIdx = (currentFrameIdx + 1) % activeFrames.length;
  }, delay);
}

// --- Load Pre-baked Animation into Preview ---
async function loadPreview(slug) {
  try {
    const res = await fetch(`/api/animation/${slug}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.frames && data.frames.length > 0) {
      playFrames(data.frames, data.fps || 14);
    }
  } catch (e) {
    console.error("Preview error:", e);
  }
}

// --- Drag & Drop Setup ---
if (dropzone && fileInput) {
  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });
}

function handleFile(file) {
  selectedFile = file;
  const name = file.name.replace(/\.[^/.]+$/, "");
  if (slugInput && !slugInput.value) {
    slugInput.value = name.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    slugInput.dispatchEvent(new Event("input"));
  }
  if (titleInput && !titleInput.value) {
    titleInput.value = name;
  }
  if (dropText) {
    dropText.innerHTML = `<strong>Selected:</strong> ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  }
}

// --- Publish Animation ---
if (btnGenerate) {
  btnGenerate.addEventListener("click", async () => {
    if (!selectedFile) {
      showToast("Please choose or drop an image or GIF first!");
      if (dropzone) {
        dropzone.classList.add("dragover");
        setTimeout(() => dropzone.classList.remove("dragover"), 1200);
        dropzone.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return;
    }

    btnGenerate.disabled = true;
    const originalText = btnGenerate.innerHTML;
    btnGenerate.innerHTML = `<span class="btn-spinner"></span><span>Baking Animation...</span>`;

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("slug", slugInput ? slugInput.value : "");
      formData.append("title", titleInput ? titleInput.value : "");
      formData.append("mode", modeSelect ? modeSelect.value : "ascii");
      formData.append("effect", effectSelect ? effectSelect.value : "scanner");
      formData.append("width", "62");
      formData.append("fps", "14");

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();
      if (result.success) {
        if (shareCurl) {
          shareCurl.setAttribute("data-slug", result.slug);
          shareCurl.textContent = getShellCommand(result.slug);
        }
        const viewerBtn = document.getElementById("btnShareViewer");
        if (viewerBtn) {
          viewerBtn.href = `/viewer?slug=${encodeURIComponent(result.slug)}`;
        }
        if (shareBanner) {
          shareBanner.classList.add("active");
          shareBanner.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        showToast("Stream created successfully!");

        if (result.capacity) {
          updateCapacityUI(result.capacity);
        }

        // Load new animation into preview
        await loadPreview(result.slug);
        // Refresh streams table
        await loadGallery();
      } else {
        showToast("Error: " + (result.error || "Failed to create stream"));
      }
    } catch (err) {
      showToast("Network error: " + err.message);
    } finally {
      btnGenerate.disabled = false;
      btnGenerate.innerHTML = originalText;
    }
  });
}

// --- Text Highlighter Utility ---
function highlightText(text, query) {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  return text.replace(regex, `<mark class="search-match">$1</mark>`);
}

// --- Instant Search & Filter Function (0ms Local Execution) ---
function filterAndRenderStreams() {
  if (!streamsBody) return;

  const q = activeSearchQuery.trim().toLowerCase();

  const filtered = allAnimations.filter((item) => {
    // Search Query Matching (slug, title, mode, effect)
    if (q) {
      const matchSlug = item.slug.toLowerCase().includes(q);
      const matchTitle = (item.title || "").toLowerCase().includes(q);
      const matchMode = (item.mode || "").toLowerCase().includes(q);
      const matchEffect = (item.effect || "").toLowerCase().includes(q);
      if (!matchSlug && !matchTitle && !matchMode && !matchEffect) return false;
    }

    return true;
  });

  // Calculate Pagination Slices (Default 4 streams per page)
  const totalItems = filtered.length;
  const isAll = streamsPageSize === "all";
  const perPage = isAll ? Math.max(1, totalItems) : streamsPageSize;
  const totalPages = Math.max(1, Math.ceil(totalItems / perPage));

  if (currentStreamsPage > totalPages) currentStreamsPage = totalPages;
  if (currentStreamsPage < 1) currentStreamsPage = 1;

  const startIdx = isAll ? 0 : (currentStreamsPage - 1) * perPage;
  const endIdx = isAll ? totalItems : Math.min(startIdx + perPage, totalItems);
  const pageItems = filtered.slice(startIdx, endIdx);

  // Update Result Count Badge
  if (searchResultsCount) {
    if (q) {
      searchResultsCount.textContent = `${filtered.length} OF ${allAnimations.length} MATCHES`;
    } else {
      searchResultsCount.textContent = `${allAnimations.length} STREAMS`;
    }
  }

  // Update Pagination & Page Size UI Controls
  const paginationBar = document.getElementById("paginationBar");
  if (paginationBar) {
    if (totalItems === 0) {
      paginationBar.style.display = "none";
    } else {
      paginationBar.style.display = "flex";
      const rangeText = document.getElementById("pageRangeText");
      const totalText = document.getElementById("pageTotalText");
      const numText = document.getElementById("pageNumberText");
      const prevBtn = document.getElementById("btnPrevPage");
      const nextBtn = document.getElementById("btnNextPage");

      if (rangeText) rangeText.textContent = totalItems === 0 ? "0" : `${startIdx + 1}–${endIdx}`;
      if (totalText) totalText.textContent = totalItems;
      if (numText) numText.textContent = isAll ? "All items" : `Page ${currentStreamsPage} of ${totalPages}`;
      if (prevBtn) prevBtn.disabled = isAll || currentStreamsPage <= 1;
      if (nextBtn) nextBtn.disabled = isAll || currentStreamsPage >= totalPages;
    }
  }

  // Handle Empty State
  if (filtered.length === 0) {
    streamsBody.innerHTML = "";
    if (noResultsBox) {
      noResultsBox.style.display = "block";
      if (emptyQueryText) emptyQueryText.textContent = q;
    }
    return;
  }

  if (noResultsBox) {
    noResultsBox.style.display = "none";
  }

  // Render Table / Cards for the current page
  const proto = window.location.protocol;
  const host = window.location.host;
  let html = "";

  for (let item of pageItems) {
    const liveCmd = getShellCommand(item.slug);
    const modeBadge = item.mode === "halfblock" ? "24-bit Truecolor" : "ASCII Density";
    const highlightedSlug = highlightText("/" + item.slug, q);
    const highlightedTitle = highlightText(item.title || item.slug, q);

    html += `
      <tr>
        <td>
          <a href="/viewer?slug=${item.slug}" class="stream-slug-link">
            <span>${highlightedSlug}</span>
          </a>
          <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 2px;">${highlightedTitle}</div>
        </td>
        <td>
          <span class="badge-mode">${modeBadge}</span>
          <span class="badge-fps">${item.fps || 14} FPS</span>
        </td>
        <td>
          <span class="stream-cmd-inline" data-slug="${item.slug}">${liveCmd}</span>
        </td>
        <td class="actions-cell">
          <button class="btn-table-copy" onclick="copyText(getShellCommand('${item.slug}'))" aria-label="Copy stream command">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
            <span>Copy</span>
          </button>
          <a href="/viewer?slug=${item.slug}" class="btn-table-view" aria-label="Play stream">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            <span>Play</span>
          </a>
        </td>
      </tr>
    `;
  }

  streamsBody.innerHTML = html;
}

// --- Fetch & Populate Streams ---
async function loadGallery() {
  try {
    const res = await fetch("/api/list?sort=views");
    const data = await res.json();

    allAnimations = data.animations || [];

    if (data.capacity) {
      updateCapacityUI(data.capacity);
    }

    filterAndRenderStreams();
  } catch (e) {
    console.error("Streams load error:", e);
  }
}

// --- Ultra-Fast Search Listeners with Professional Debounce ---
const searchSpinner = document.getElementById("searchSpinner");
let searchDebounceTimer = null;

if (streamSearch) {
  streamSearch.addEventListener("input", (e) => {
    const val = e.target.value;
    
    // Toggle clear button
    if (btnSearchClear) {
      btnSearchClear.style.display = val ? "inline-block" : "none";
    }

    if (searchSpinner) searchSpinner.style.display = "inline-block";

    // Instant local filter debounced to prevent stutter
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      activeSearchQuery = val;
      currentStreamsPage = 1;
      filterAndRenderStreams();
      if (searchSpinner) searchSpinner.style.display = "none";
    }, 150);

    // Debounced Server Search
    if (serverSearchTimer) clearTimeout(serverSearchTimer);
    if (val.trim().length >= 2) {
      serverSearchTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/list?q=${encodeURIComponent(val.trim())}`);
          if (res.ok) {
            const data = await res.json();
            if (data.animations && data.animations.length > 0) {
              const existingSlugs = new Set(allAnimations.map(a => a.slug));
              for (let a of data.animations) {
                if (!existingSlugs.has(a.slug)) {
                  allAnimations.push(a);
                }
              }
              filterAndRenderStreams();
            }
          }
        } catch (err) {
          // Ignore network search errors silently
        } finally {
          if (searchSpinner) searchSpinner.style.display = "none";
        }
      }, 250);
    }
  });

  if (btnSearchClear) {
    btnSearchClear.addEventListener("click", () => {
      streamSearch.value = "";
      activeSearchQuery = "";
      currentStreamsPage = 1;
      btnSearchClear.style.display = "none";
      filterAndRenderStreams();
      streamSearch.focus();
    });
  }
}

// Empty state action button: creates a stream with the search query
if (btnCreateFromSearch) {
  btnCreateFromSearch.addEventListener("click", () => {
    const cleanSlug = activeSearchQuery.toLowerCase().replace(/[^a-z0-9_-]/g, "-").replace(/^-+|-+$/g, "");
    if (slugInput) {
      slugInput.value = cleanSlug || "my-art";
      slugInput.dispatchEvent(new Event("input"));
    }
    if (titleInput) {
      titleInput.value = (cleanSlug || "My Art").replace("-", " ").toUpperCase();
    }
    const creatorSection = document.querySelector(".creator-card");
    if (creatorSection) {
      creatorSection.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (dropzone) dropzone.focus();
  });
}

// Page size selector buttons (4, 8, 12, All)
document.querySelectorAll(".btn-page-size").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".btn-page-size").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const sizeVal = btn.getAttribute("data-size");
    streamsPageSize = sizeVal === "all" ? "all" : parseInt(sizeVal, 10);
    currentStreamsPage = 1;
    filterAndRenderStreams();
  });
});

// Pagination Navigation buttons
const btnPrevPage = document.getElementById("btnPrevPage");
const btnNextPage = document.getElementById("btnNextPage");

if (btnPrevPage) {
  btnPrevPage.addEventListener("click", () => {
    if (currentStreamsPage > 1) {
      currentStreamsPage--;
      filterAndRenderStreams();
      const streamsTable = document.querySelector(".table-container");
      if (streamsTable) streamsTable.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });
}

if (btnNextPage) {
  btnNextPage.addEventListener("click", () => {
    currentStreamsPage++;
    filterAndRenderStreams();
    const streamsTable = document.querySelector(".table-container");
    if (streamsTable) streamsTable.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}

// Global Keyboard Shortcut: Press '/' anywhere to focus search
window.addEventListener("keydown", (e) => {
  const activeEl = document.activeElement;
  const isInput = activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.tagName === "SELECT");

  if (e.key === "/" && !isInput && streamSearch) {
    e.preventDefault();
    streamSearch.focus();
    streamSearch.select();
  } else if (e.key === "Escape" && streamSearch && document.activeElement === streamSearch) {
    streamSearch.value = "";
    activeSearchQuery = "";
    if (btnSearchClear) btnSearchClear.style.display = "none";
    filterAndRenderStreams();
    streamSearch.blur();
  }
});

// --- Animated Cyber Terminal Favicon in Chrome Tab ---
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

    // Dark rounded background
    ctx.fillStyle = "#0c1018";
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(1, 1, 30, 30, 7);
    } else {
      ctx.rect(1, 1, 30, 30);
    }
    ctx.fill();

    // Golden / cyan border pulse
    ctx.strokeStyle = (step % 2 === 0) ? "#ffd700" : "#38bdf8";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Terminal prompt '>' in glowing gold
    ctx.strokeStyle = "#ffd700";
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(8, 10);
    ctx.lineTo(15, 16);
    ctx.lineTo(8, 22);
    ctx.stroke();

    // Blinking terminal cursor '_' in neon green / cyan
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

// --- Shell Switcher UI Handlers ---
function updateShellUI() {
  document.querySelectorAll(".shell-tab").forEach(tab => {
    const isCur = tab.getAttribute("data-shell") === activeShell;
    tab.classList.toggle("active", isCur);
    tab.setAttribute("aria-selected", isCur ? "true" : "false");
  });

  const heroCmd = document.getElementById("heroCmd");
  const heroPromptSym = document.getElementById("heroPromptSym");
  const shellNoteText = document.getElementById("shellNoteText");

  if (heroCmd) {
    heroCmd.textContent = getShellCommand("art");
  }

  if (heroPromptSym) {
    if (activeShell === "powershell") heroPromptSym.textContent = "PS >";
    else if (activeShell === "cmd") heroPromptSym.textContent = "C:\\>";
    else heroPromptSym.textContent = "$";
  }

  if (shellNoteText) {
    if (activeShell === "powershell") {
      shellNoteText.innerHTML = "Windows PowerShell &amp; Terminal: uses <code>curl.exe</code> to bypass the built-in Invoke-WebRequest alias.";
    } else if (activeShell === "cmd") {
      shellNoteText.innerHTML = "Windows Command Prompt: native <code>curl -sN</code> execution.";
    } else {
      shellNoteText.innerHTML = "macOS, Linux, WSL, &amp; Git Bash: native <code>curl -sN</code> stream.";
    }
  }

  const shareCurl = document.getElementById("shareCurl");
  if (shareCurl && shareCurl.getAttribute("data-slug")) {
    shareCurl.textContent = getShellCommand(shareCurl.getAttribute("data-slug"));
  }

  // Update table inline commands
  document.querySelectorAll(".stream-cmd-inline").forEach(el => {
    const slug = el.getAttribute("data-slug");
    if (slug) {
      el.textContent = getShellCommand(slug);
    }
  });
}

function setShell(shell) {
  activeShell = shell;
  try {
    localStorage.setItem("ascii_preferred_shell", shell);
  } catch (e) {}
  updateShellUI();
}

function initShellTabs() {
  document.querySelectorAll(".shell-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const shell = tab.getAttribute("data-shell");
      if (shell) setShell(shell);
    });
  });
  updateShellUI();
}

// Initial setup
window.addEventListener("DOMContentLoaded", () => {
  initShellTabs();
  initAnimatedFavicon();
  loadPreview("art");
  loadGallery();
});
