// --- ANSI to HTML Parser ---
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

// --- Toast Notification System ---
let toastTimeout = null;
function showToast(message) {
  const toast = document.getElementById("toast");
  const msgEl = document.getElementById("toastMsg");
  if (!toast || !msgEl) return;
  
  msgEl.textContent = message;
  toast.classList.add("show");
  
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove("show");
  }, 2500);
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
let activeFilter = "all";
let activeSearchQuery = "";
let serverSearchTimer = null;

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

// Input Controls
const slugInput = document.getElementById("slugInput");
const titleInput = document.getElementById("titleInput");
const modeSelect = document.getElementById("modeSelect");
const effectSelect = document.getElementById("effectSelect");

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
    btnGenerate.disabled = true;
    const originalText = btnGenerate.innerHTML;
    btnGenerate.innerHTML = `<span class="btn-icon">⏳</span><span>Baking Animation...</span>`;

    try {
      const formData = new FormData();
      if (selectedFile) {
        formData.append("file", selectedFile);
      }
      formData.append("slug", slugInput.value || "art");
      formData.append("title", titleInput.value || "Custom Art");
      formData.append("mode", modeSelect ? modeSelect.value : "halfblock");
      formData.append("effect", effectSelect ? effectSelect.value : "scanner");
      formData.append("width", "54");
      formData.append("fps", "14");

      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const result = await res.json();
      if (result.success) {
        const proto = window.location.protocol;
        const liveCurl = `curl -s ${proto}//${window.location.host}/${result.slug}`;

        if (shareCurl) shareCurl.textContent = liveCurl;
        if (shareBanner) shareBanner.classList.add("active");

        showToast("Stream created! Ready to run.");

        // Load new animation into preview
        await loadPreview(result.slug);
        // Refresh streams table
        await loadGallery();
      } else {
        alert("Upload error: " + (result.error || "Unknown error"));
      }
    } catch (err) {
      alert("Error: " + err.message);
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
  const filter = activeFilter;

  const filtered = allAnimations.filter((item) => {
    // 1. Tag / Category Filter
    if (filter === "flagship" && item.effect !== "flagship") return false;
    if (filter === "3d" && item.effect !== "3d") return false;
    if (filter === "fire" && item.effect !== "fire") return false;
    if (filter === "halfblock" && item.mode !== "halfblock") return false;

    // 2. Search Query Matching (slug, title, mode, effect)
    if (q) {
      const matchSlug = item.slug.toLowerCase().includes(q);
      const matchTitle = (item.title || "").toLowerCase().includes(q);
      const matchMode = (item.mode || "").toLowerCase().includes(q);
      const matchEffect = (item.effect || "").toLowerCase().includes(q);
      if (!matchSlug && !matchTitle && !matchMode && !matchEffect) return false;
    }

    return true;
  });

  // Update Result Count Badge
  if (searchResultsCount) {
    if (q || filter !== "all") {
      searchResultsCount.textContent = `${filtered.length} OF ${allAnimations.length} MATCHES`;
    } else {
      searchResultsCount.textContent = `${allAnimations.length} STREAMS`;
    }
  }

  // Handle Empty State
  if (filtered.length === 0) {
    streamsBody.innerHTML = "";
    if (noResultsBox) {
      noResultsBox.style.display = "block";
      if (emptyQueryText) emptyQueryText.textContent = q || filter;
    }
    return;
  }

  if (noResultsBox) {
    noResultsBox.style.display = "none";
  }

  // Render Table / Cards
  const proto = window.location.protocol;
  const host = window.location.host;
  let html = "";

  for (let item of filtered) {
    const liveCmd = `curl -s ${proto}//${host}/${item.slug}`;
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
          <span class="stream-cmd-inline">${liveCmd}</span>
        </td>
        <td class="actions-cell">
          <button class="btn-table-copy" onclick="copyText('${liveCmd}')">Copy</button>
          <a href="/viewer?slug=${item.slug}" class="btn-table-view">View</a>
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

    if (headerStats && data.stats) {
      headerStats.textContent = `${data.stats.total_animations} STREAMS • ONLINE`;
    }

    filterAndRenderStreams();
  } catch (e) {
    console.error("Streams load error:", e);
  }
}

// --- Ultra-Fast Search Listeners ---
if (streamSearch) {
  streamSearch.addEventListener("input", (e) => {
    activeSearchQuery = e.target.value;
    
    // Toggle clear button
    if (btnSearchClear) {
      btnSearchClear.style.display = activeSearchQuery ? "inline-block" : "none";
    }

    // 1. Instant 0ms Local Memory Filter
    filterAndRenderStreams();

    // 2. Debounced Server Search (for scaling when database has thousands of entries)
    if (serverSearchTimer) clearTimeout(serverSearchTimer);
    if (activeSearchQuery.trim().length >= 2) {
      serverSearchTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/list?q=${encodeURIComponent(activeSearchQuery.trim())}`);
          if (res.ok) {
            const data = await res.json();
            if (data.animations && data.animations.length > 0) {
              // Merge server results into in-memory list
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
        }
      }, 200);
    }
  });

  if (btnSearchClear) {
    btnSearchClear.addEventListener("click", () => {
      streamSearch.value = "";
      activeSearchQuery = "";
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
    if (slugInput) slugInput.value = cleanSlug || "my-art";
    if (titleInput) titleInput.value = (cleanSlug || "My Art").replace("-", " ").toUpperCase();
    const creatorSection = document.querySelector(".creator-card");
    if (creatorSection) {
      creatorSection.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    if (dropzone) dropzone.focus();
  });
}

// Filter pills click handling
document.querySelectorAll(".filter-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
    pill.classList.add("active");
    activeFilter = pill.getAttribute("data-filter") || "all";
    filterAndRenderStreams();
  });
});

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

// Initial setup
window.addEventListener("DOMContentLoaded", () => {
  const heroCmd = document.getElementById("heroCmd");
  if (heroCmd) {
    const proto = window.location.protocol;
    heroCmd.textContent = `curl -s ${proto}//${window.location.host}/art`;
  }
  loadPreview("art");
  loadGallery();
});
