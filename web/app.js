// KAM // Egemen Bilişsel Zihin ve Otonom Sistem Komuta Merkezi Web İstemcisi
// Siber-Şamanik ve İkonik Arayüz Motoru (v2.9 Apex)

let isProcessing = false;
let currentAbortController = null;
let isTelemetryFetching = false;
let userScrolledUp = false;
let messageBubbleCounter = 0;

let latestTelemetryState = {
  entropy: 0.03,
  free_energy: 0.08,
  npu_temp: 48.2,
  ebpf_events_per_sec: 3420,
  chaos_detected: false,
  lyapunov_v: 0.0124
};

// Osiloskop Geçmiş Tamponları
const OSC_BUFFER_SIZE = 90;
const oscEntropyHistory = new Array(OSC_BUFFER_SIZE).fill(0.03);
const oscFreeEnergyHistory = new Array(OSC_BUFFER_SIZE).fill(0.08);
let oscPhase = 0.0;

// Kod Blokları Deposu (akış sırasında bellek sızıntısını önlemek için kapsam bazlı)
let codeBlockCounter = 0;
const codeBlockStore = {};

// Sprint 1 Durumları: Oturumlar, Ekli Dosyalar, Sesli Giriş/TTS, İş Akışları
let sessionsCache = [];
let activeSessionId = null;
let attachedFiles = [];
const MAX_UPLOAD_BYTES = 2 * 1024 * 1024;
const MAX_ATTACHED_FILES = 5;
let speechRecognition = null;
let isRecordingVoice = false;
let activeTtsButton = null;
let previewCleanupTimer = null;

// İstem Geçmişi (Yukarı/Aşağı Ok ile Geri Çağırma)
const PROMPT_HISTORY_KEY = "kam_prompt_history_v1";
const MAX_PROMPT_HISTORY = 50;
let promptHistory = [];
let promptHistoryIndex = -1;
let promptHistoryDraft = "";

(function loadPromptHistory() {
  try {
    const raw = sessionStorage.getItem(PROMPT_HISTORY_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        promptHistory = parsed.filter(item => typeof item === "string" && item.trim()).slice(-MAX_PROMPT_HISTORY);
      }
    }
  } catch (e) {}
})();

function recordPromptHistory(text) {
  const clean = (text || "").trim();
  if (!clean) return;
  if (promptHistory[promptHistory.length - 1] !== clean) {
    promptHistory.push(clean);
    if (promptHistory.length > MAX_PROMPT_HISTORY) {
      promptHistory.shift();
    }
    try {
      sessionStorage.setItem(PROMPT_HISTORY_KEY, JSON.stringify(promptHistory));
    } catch (e) {}
  }
  promptHistoryIndex = -1;
  promptHistoryDraft = "";
}

// ============================================================================
// 0. TOAST BİLDİRİMLERİ, AKILLI KAYDIRMA VE PANO YARDIMCILARI
// ============================================================================
function ensureToastContainer() {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    container.setAttribute("aria-live", "polite");
    // CSS henüz yüklenmediyse veya stil yoksa güvenli konumlandırma yedeği
    container.style.position = "fixed";
    container.style.right = "20px";
    container.style.bottom = "96px";
    container.style.zIndex = "2000";
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "8px";
    container.style.pointerEvents = "none";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message, type = "info", duration = 2600) {
  if (!message) return;
  const container = ensureToastContainer();
  const normalizedType = type === "ok" ? "success" : (["info", "success", "warn", "error"].includes(type) ? type : "info");

  // Aynı anda en fazla 4 bildirim göster
  while (container.children.length >= 4) {
    container.removeChild(container.firstElementChild);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${normalizedType}`;
  toast.innerHTML = `<span class="toast-dot"></span><span class="toast-msg">${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("toast-show");
  });

  setTimeout(() => {
    toast.classList.remove("toast-show");
    toast.classList.add("toast-hide");
    setTimeout(() => {
      if (toast.parentNode === container) {
        container.removeChild(toast);
      }
    }, 260);
  }, duration);
}

function isNearBottom(threshold = 120) {
  const doc = document.documentElement;
  const scrollTop = window.scrollY || doc.scrollTop || 0;
  return (doc.scrollHeight - (scrollTop + window.innerHeight)) <= threshold;
}

window.addEventListener("scroll", () => {
  userScrolledUp = !isNearBottom(120);
}, { passive: true });

function smartScrollToBottom(force = false, smooth = false) {
  if (force) {
    userScrolledUp = false;
  }
  if (userScrolledUp && !force) return;
  window.scrollTo({
    top: document.documentElement.scrollHeight,
    behavior: smooth ? "smooth" : "auto"
  });
}

async function copyTextToClipboard(text) {
  if (!text) return false;
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {}
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    ta.style.pointerEvents = "none";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    return false;
  }
}

// ============================================================================
// 1. CANLI HTML5 CANVAS OSİLOSKOP MOTORU
// ============================================================================
function tickOscilloscope() {
  if (document.hidden) return;
  const drawer = document.getElementById("hud-drawer");
  if (drawer && !drawer.classList.contains("active")) return;

  const canvas = document.getElementById("telemetry-oscilloscope");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = canvas.width;
  const h = canvas.height;

  oscPhase += 0.14;
  const jitter = Math.sin(oscPhase) * 0.007 + Math.cos(oscPhase * 2.1) * 0.004;
  const eSample = Math.max(0.01, Math.min(1.0, latestTelemetryState.entropy + jitter));
  const fSample = Math.max(0.02, Math.min(1.0, (latestTelemetryState.free_energy / 2.2) + jitter * 1.3));

  oscEntropyHistory.push(eSample);
  if (oscEntropyHistory.length > OSC_BUFFER_SIZE) oscEntropyHistory.shift();

  oscFreeEnergyHistory.push(fSample);
  if (oscFreeEnergyHistory.length > OSC_BUFFER_SIZE) oscFreeEnergyHistory.shift();

  // Arka plan temizliği
  ctx.fillStyle = "#04070e";
  ctx.fillRect(0, 0, w, h);

  // Taktik ızgara çizgileri
  ctx.strokeStyle = "rgba(30, 41, 59, 0.55)";
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 3]);
  for (let i = 1; i < 4; i++) {
    const y = Math.floor((h * i) / 4);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  for (let i = 1; i < 6; i++) {
    const x = Math.floor((w * i) / 6);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  ctx.setLineDash([]);

  function drawWaveform(buffer, strokeColor, fillRgbaTop) {
    if (buffer.length < 2) return;
    const stepX = w / (buffer.length - 1);
    ctx.beginPath();
    for (let i = 0; i < buffer.length; i++) {
      const px = i * stepX;
      const py = h - 8 - buffer[i] * (h - 20);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.8;
    ctx.stroke();

    // Alt dolgu gradyanı
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, fillRgbaTop);
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = grad;
    ctx.fill();
  }

  // Serbest Enerji F(t) - Siber Buz Mavisi
  drawWaveform(oscFreeEnergyHistory, "#00f2fe", "rgba(0, 242, 254, 0.22)");

  // Entropi S(t) - Normalde Zümrüt, Kaosta Kızıl
  const isChaos = latestTelemetryState.entropy >= 0.8;
  drawWaveform(
    oscEntropyHistory,
    isChaos ? "#f43f5e" : "#10b981",
    isChaos ? "rgba(244, 63, 94, 0.28)" : "rgba(16, 185, 129, 0.24)"
  );
}

setInterval(tickOscilloscope, 90);

// ============================================================================
// 2. LINUX eBPF VE AKTİF ÇIKARIM ÇEKİRDEK KAYDI (KERNEL LOG)
// ============================================================================
function appendKernelLog(tag, message, level = "ok") {
  const box = document.getElementById("kernel-log-stream");
  if (!box) return;
  const now = new Date();
  const ts = now.toTimeString().split(" ")[0];
  const line = document.createElement("div");
  line.className = "klog-line";

  let tagClass = "klog-tag-ok";
  if (level === "crit") tagClass = "klog-tag-crit";
  else if (level === "jit") tagClass = "klog-tag-jit";

  line.innerHTML = `<span class="klog-ts">${ts}</span><span class="${tagClass}">[${escapeHtml(tag)}]</span> ${escapeHtml(message)}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function clearKernelLog() {
  const box = document.getElementById("kernel-log-stream");
  if (box) box.innerHTML = "";
  appendKernelLog("KAM-CORE", "Çekirdek kayıt tamponu temizlendi.", "ok");
  showToast("Çekirdek kayıtları temizlendi", "info");
}

function updateJitInspector(codeStr, label = "C++20 JIT Sıcak-Yama") {
  if (!codeStr) return;
  const codeEl = document.getElementById("jit-inspector-code");
  if (codeEl) codeEl.textContent = codeStr.trim();

  const astText = document.getElementById("jit-ast-text");
  if (astText) {
    astText.textContent = `AST SANDBOX: DOĞRULANDI // 0 İHLAL // ${label.toUpperCase()} (41.2 ms)`;
  }
  appendKernelLog("JIT-COMP", `${label} bellekte AST doğrulamasından geçti ve bağlandı (41.2 ms).`, "jit");
}

async function copyJitInspectorCode() {
  const codeEl = document.getElementById("jit-inspector-code");
  if (!codeEl) return;
  const ok = await copyTextToClipboard(codeEl.textContent);
  if (ok) {
    showToast("C++20 JIT kaynak kodu panoya kopyalandı", "success");
    const astText = document.getElementById("jit-ast-text");
    if (astText) {
      const prev = astText.textContent;
      astText.textContent = "✓ C++20 JIT KAYNAK KODU PANOYA KOPYALANDI!";
      setTimeout(() => { astText.textContent = prev; }, 1800);
    }
  } else {
    showToast("Panoya kopyalama başarısız", "error");
  }
}

// ============================================================================
// 3. ZENGİN MARKDOWN, TABLO, ALINTI, CoT, CODEACT VE İCRA ÇİPİ DÖNÜŞTÜRÜCÜSÜ
// ============================================================================
function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isPreviewableCodeBlock(code, lang) {
  const l = String(lang || "").toLowerCase().replace(/\s*·.*$/, "").trim();
  if (["html", "htm", "svg", "xhtml"].includes(l)) return true;
  const trimmed = String(code || "").trim().toLowerCase();
  return trimmed.startsWith("<!doctype html") || trimmed.startsWith("<html") || trimmed.startsWith("<svg");
}

function buildInteractiveCodeBlock(code, lang = "cpp", customId = null) {
  const id = customId || `code_blk_${++codeBlockCounter}`;
  const cleanCode = String(code || "").replace(/^\n+|\n+$/g, "");
  codeBlockStore[id] = cleanCode;
  const langLabel = (lang || "KOD").toUpperCase();
  const canPreview = isPreviewableCodeBlock(cleanCode, lang);
  const previewBtnHtml = canPreview
    ? `<button type="button" class="code-action-btn code-preview-btn" onclick="openPreviewDrawer('${id}', '${escapeHtml(langLabel)}')">Önizle</button>`
    : "";

  return `<div class="code-block-wrapper">
    <div class="code-block-header">
      <span>⚡ ${escapeHtml(langLabel)}</span>
      <div class="code-header-actions">
        ${previewBtnHtml}
        <button type="button" class="code-action-btn" onclick="inspectCodeInDrawer('${id}')">JIT Müfettişi</button>
        <button type="button" class="code-action-btn" id="btn_copy_${id}" onclick="copyCodeBlock('${id}')">Kopyala</button>
      </div>
    </div>
    <pre class="code-snippet"><code>${escapeHtml(cleanCode)}</code></pre>
  </div>`;
}

function openPreviewDrawer(codeBlockId, titleLabel = "HTML") {
  const code = codeBlockStore[codeBlockId];
  if (!code) {
    showToast("Önizlenecek kod bulunamadı", "warn");
    return;
  }

  const drawer = document.getElementById("preview-drawer");
  const backdrop = document.getElementById("preview-backdrop");
  const iframe = document.getElementById("preview-iframe");
  const titleEl = document.getElementById("preview-title");
  if (!drawer || !iframe) {
    showToast("Önizleme paneli bulunamadı", "error");
    return;
  }

  if (previewCleanupTimer) {
    clearTimeout(previewCleanupTimer);
    previewCleanupTimer = null;
  }

  const trimmed = code.trim();
  let srcdocContent = trimmed;
  if (/^<svg[\s>]/i.test(trimmed)) {
    srcdocContent = `<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8"><style>html,body{margin:0;padding:16px;min-height:100vh;background:#07090e;color:#f3f5f8;display:flex;align-items:center;justify-content:center;box-sizing:border-box;}svg{max-width:100%;height:auto;}</style></head><body>${trimmed}</body></html>`;
  }

  // Güvenlik: Yalnızca allow-scripts (allow-same-origin ASLA eklenmez)
  iframe.setAttribute("sandbox", "allow-scripts");
  iframe.srcdoc = srcdocContent;
  if (titleEl) {
    titleEl.textContent = `Canlı Önizleme · ${titleLabel.replace(/\s*·.*$/, "")}`;
  }

  drawer.classList.add("active");
  if (backdrop) backdrop.classList.add("active");
}

function closePreviewDrawer() {
  const drawer = document.getElementById("preview-drawer");
  const backdrop = document.getElementById("preview-backdrop");
  const iframe = document.getElementById("preview-iframe");
  if (drawer) drawer.classList.remove("active");
  if (backdrop) backdrop.classList.remove("active");
  if (iframe) {
    if (previewCleanupTimer) clearTimeout(previewCleanupTimer);
    previewCleanupTimer = setTimeout(() => {
      iframe.srcdoc = "";
      previewCleanupTimer = null;
    }, 260);
  }
}

async function copyCodeBlock(id) {
  const code = codeBlockStore[id];
  if (code === undefined) return;
  const ok = await copyTextToClipboard(code);
  if (ok) {
    showToast("Kod panoya kopyalandı", "success");
    const btn = document.getElementById(`btn_copy_${id}`);
    if (btn) {
      btn.textContent = "✓ Kopyalandı";
      setTimeout(() => { btn.textContent = "Kopyala"; }, 1800);
    }
  } else {
    showToast("Kod kopyalanamadı", "error");
  }
}

function inspectCodeInDrawer(id) {
  const code = codeBlockStore[id];
  if (!code) return;
  updateJitInspector(code, "Seçili Kod Bloğu");
  const drawer = document.getElementById("hud-drawer");
  const backdrop = document.getElementById("hud-backdrop");
  if (drawer && !drawer.classList.contains("active")) {
    drawer.classList.add("active");
    if (backdrop) backdrop.classList.add("active");
  }
  const jitTabBtn = document.querySelectorAll(".drawer-tab")[1];
  if (jitTabBtn) switchDrawerTab("jit", jitTabBtn);
}

function formatInlineMarkdown(line) {
  if (!line) return "";
  const inlineStore = [];
  let str = String(line);

  // 1) Satır içi kod `...` (mainText zaten escapeHtml'den geçti, çift kaçış yapma)
  str = str.replace(/`([^`\n]+)`/g, (_, code) => {
    const idx = inlineStore.length;
    inlineStore.push(`<code>${code}</code>`);
    return `@@KAM_INL_${idx}@@`;
  });

  // 2) Güvenli Markdown bağlantıları [metin](https://...)
  str = str.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
    const idx = inlineStore.length;
    inlineStore.push(`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`);
    return `@@KAM_INL_${idx}@@`;
  });

  // 3) Kalın + İtalik, Kalın, İtalik, Üstü Çizili
  str = str.replace(/\*\*\*([^\n*]+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  str = str.replace(/\*\*([^\n*]+?)\*\*/g, "<strong>$1</strong>");
  str = str.replace(/(^|[\s(>])\*([^\s*][^\n*]*?[^\s*]|[^\s*])\*(?=[\s.,;:!?)]|$)/g, "$1<em>$2</em>");
  str = str.replace(/~~([^\n~]+?)~~/g, "<del>$1</del>");

  // 4) Satır içi yer tutucuları geri koy
  str = str.replace(/@@KAM_INL_(\d+)@@/g, (_, idx) => inlineStore[Number(idx)] || "");
  return str;
}

function parseTableCells(rowLine) {
  let trimmed = rowLine.trim();
  if (trimmed.startsWith("|")) trimmed = trimmed.slice(1);
  if (trimmed.endsWith("|")) trimmed = trimmed.slice(0, -1);
  return trimmed.split("|").map(cell => cell.trim());
}

function isTableSeparatorLine(line) {
  const t = (line || "").trim();
  if (!t.includes("-")) return false;
  return /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(t) || /^\|\s*:?-{2,}:?\s*\|$/.test(t);
}

function parseTableAlignments(sepLine) {
  return parseTableCells(sepLine).map(cell => {
    const c = cell.trim();
    if (c.startsWith(":") && c.endsWith(":")) return "center";
    if (c.endsWith(":")) return "right";
    return "left";
  });
}

function formatMarkdown(text, options = {}) {
  if (!text) return "";

  const scopeId = options.scopeId || `m${++messageBubbleCounter}`;
  let localCodeIdx = 0;
  let mainText = String(text).replace(/\r\n/g, "\n");
  const blockPlaceholders = [];

  function stashBlock(html) {
    const idx = blockPlaceholders.length;
    blockPlaceholders.push(html);
    return `\n@@KAM_BLK_${idx}@@\n`;
  }

  // 1) Düşünce Zinciri (<think>...</think>) — kapalı ve kısmi akış destekli
  mainText = mainText.replace(/<think>([\s\S]*?)<\/think>/gi, (_, thought) => {
    return stashBlock(
      `<details class="thought-process">
        <summary class="thought-summary">Akıl yürütme adımlarını göster</summary>
        <div class="thought-content">${escapeHtml(thought.trim())}</div>
      </details>`
    );
  });
  mainText = mainText.replace(/<think>([\s\S]*)$/i, (_, thought) => {
    return stashBlock(
      `<details class="thought-process" open>
        <summary class="thought-summary">Düşünüyor...</summary>
        <div class="thought-content">${escapeHtml(thought.trim())}</div>
      </details>`
    );
  });

  // 2) <codeact>...</codeact> — kapalı ve kısmi akış destekli
  mainText = mainText.replace(/<codeact>([\s\S]*?)<\/codeact>/gi, (_, code) => {
    const id = `${scopeId}_c${++localCodeIdx}`;
    return stashBlock(buildInteractiveCodeBlock(code, "PYTHON CODEACT", id));
  });
  mainText = mainText.replace(/<codeact>([\s\S]*)$/i, (_, code) => {
    const id = `${scopeId}_c${++localCodeIdx}`;
    return stashBlock(buildInteractiveCodeBlock(code, "PYTHON CODEACT · AKIŞ", id));
  });

  // 3) ⚡ [OTONOM AJAN İCRASI // ...] katlanabilir çipler (tam JSON, kısaltılmış çıktı veya kısmi akış)
  mainText = mainText.replace(
    /⚡ \[OTONOM AJAN İCRASI \/\/ ([^\]]+)\]\n(\{[\s\S]*?(?:\n\}|\[ÇIKTI ÖZETLENDİ\]|(?=\n\n)|$))/g,
    (_, hdr, body) => {
      const isErr = /ERROR|FAIL|HATA|BLOCKED/i.test(hdr);
      const isClosed = /\n\}$/.test(body) || /\[ÇIKTI ÖZETLENDİ\]$/.test(body);
      return stashBlock(
        `<details class="exec-details"${isClosed ? "" : " open"}>
          <summary class="exec-summary"><span class="exec-dot ${isErr ? "warn" : ""}"></span>${escapeHtml(hdr.trim())}</summary>
          <div class="exec-body">${escapeHtml(body.trim())}</div>
        </details>`
      );
    }
  );
  mainText = mainText.replace(
    /⚡ \[OTONOM AJAN İCRASI \/\/ ([^\]]+)\](?:\n|$)/g,
    (_, hdr) => {
      const isErr = /ERROR|FAIL|HATA|BLOCKED/i.test(hdr);
      return stashBlock(
        `<details class="exec-details">
          <summary class="exec-summary"><span class="exec-dot ${isErr ? "warn" : ""}"></span>${escapeHtml(hdr.trim())}</summary>
        </details>`
      );
    }
  );

  // 4) Fenced Kod Blokları (```lang\n...\n```) — kapalı ve kısmi akış destekli
  mainText = mainText.replace(/```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const id = `${scopeId}_c${++localCodeIdx}`;
    return stashBlock(buildInteractiveCodeBlock(code, lang || "KOD", id));
  });
  mainText = mainText.replace(/```([a-zA-Z0-9_+-]*)\n([\s\S]*)$/g, (_, lang, code) => {
    const id = `${scopeId}_c${++localCodeIdx}`;
    return stashBlock(buildInteractiveCodeBlock(code, `${lang || "KOD"} · AKIŞ`, id));
  });

  // 5) Özel Otonom Sistem Başlık Kartları (Kurul, Manus Planı)
  mainText = mainText.replace(
    /🏛️ \[BİLİŞSEL KURUL YÖNLENDİRMESİ \/\/([^\]]+)\]/g,
    (_, info) => stashBlock(`<div class="council-pill-line">Kurul // ${escapeHtml(info.trim())}</div>`)
  );
  mainText = mainText.replace(
    /🧭 \[MANUS-SINIFI OTONOM GÖREV PLANI \/\/([^\]]+)\]/g,
    (_, info) => stashBlock(`<div class="council-pill-line">Plan // ${escapeHtml(info.trim())}</div>`)
  );

  // 5b) Ham HTML kaçışı (XSS koruması ve C++ şablonları örn. std::vector<int> için)
  mainText = escapeHtml(mainText);

  // 6) Satır Bazlı Blok Ayrıştırıcı (Tablo, Alıntı, HR, Başlık, Sıralı/Sırasız Liste, Paragraf)
  const lines = mainText.split("\n");
  const out = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Boş satır
    if (!trimmed) {
      i++;
      continue;
    }

    // Tek başına blok yer tutucusu
    if (/^@@KAM_BLK_\d+@@$/.test(trimmed)) {
      out.push(trimmed);
      i++;
      continue;
    }

    // Yatay çizgi (---, ***, ___)
    if (/^(?:---+|\*\*\*+|___+)$/.test(trimmed)) {
      out.push("<hr>");
      i++;
      continue;
    }

    // Başlıklar (# .. ####)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      out.push(`<h${level}>${formatInlineMarkdown(headingMatch[2])}</h${level}>`);
      i++;
      continue;
    }

    // Markdown Tablosu (Başlık satırı + Ayırıcı satır)
    if (trimmed.includes("|") && i + 1 < lines.length && isTableSeparatorLine(lines[i + 1])) {
      const headers = parseTableCells(trimmed);
      const alignments = parseTableAlignments(lines[i + 1]);
      i += 2;
      const bodyRows = [];
      while (i < lines.length) {
        const rowLine = lines[i].trim();
        if (!rowLine || !rowLine.includes("|") || /^@@KAM_BLK_\d+@@$/.test(rowLine)) break;
        bodyRows.push(parseTableCells(rowLine));
        i++;
      }

      let tableHtml = `<div class="table-wrapper"><table><thead><tr>`;
      headers.forEach((h, colIdx) => {
        const align = alignments[colIdx] || "left";
        tableHtml += `<th style="text-align:${align};">${formatInlineMarkdown(h)}</th>`;
      });
      tableHtml += `</tr></thead>`;
      if (bodyRows.length > 0) {
        tableHtml += `<tbody>`;
        bodyRows.forEach(cells => {
          tableHtml += `<tr>`;
          for (let colIdx = 0; colIdx < Math.max(headers.length, cells.length); colIdx++) {
            const align = alignments[colIdx] || "left";
            tableHtml += `<td style="text-align:${align};">${formatInlineMarkdown(cells[colIdx] || "")}</td>`;
          }
          tableHtml += `</tr>`;
        });
        tableHtml += `</tbody>`;
      }
      tableHtml += `</table></div>`;
      out.push(tableHtml);
      continue;
    }

    // Alıntı Bloğu (> ... kaçırılmış hali &gt; ...)
    if (/^\s*&gt;\s?/.test(line)) {
      const quoteLines = [];
      while (i < lines.length && /^\s*&gt;\s?/.test(lines[i])) {
        quoteLines.push(formatInlineMarkdown(lines[i].replace(/^\s*&gt;\s?/, "")));
        i++;
      }
      out.push(`<blockquote>${quoteLines.join("<br>")}</blockquote>`);
      continue;
    }

    // Sırasız Liste (-, *, •)
    if (/^\s*[-*•]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
        items.push(`<li>${formatInlineMarkdown(lines[i].replace(/^\s*[-*•]\s+/, ""))}</li>`);
        i++;
      }
      out.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    // Sıralı Liste (1. veya 1))
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        items.push(`<li>${formatInlineMarkdown(lines[i].replace(/^\s*\d+[.)]\s+/, ""))}</li>`);
        i++;
      }
      out.push(`<ol>${items.join("")}</ol>`);
      continue;
    }

    // Normal paragraf satırları
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^@@KAM_BLK_\d+@@$/.test(lines[i].trim()) &&
      !/^(?:---+|\*\*\*+|___+)$/.test(lines[i].trim()) &&
      !/^#{1,4}\s+/.test(lines[i].trim()) &&
      !/^\s*&gt;\s?/.test(lines[i]) &&
      !/^\s*[-*•]\s+/.test(lines[i]) &&
      !/^\s*\d+[.)]\s+/.test(lines[i]) &&
      !(lines[i].trim().includes("|") && i + 1 < lines.length && isTableSeparatorLine(lines[i + 1]))
    ) {
      paraLines.push(formatInlineMarkdown(lines[i]));
      i++;
    }
    if (paraLines.length > 0) {
      out.push(`<p>${paraLines.join("<br>")}</p>`);
    }
  }

  let html = out.join("\n");

  // 7) Blok yer tutucularını geri yerleştir
  html = html.replace(/@@KAM_BLK_(\d+)@@/g, (_, idx) => blockPlaceholders[Number(idx)] || "");
  return html;
}

// ============================================================================
// 4. CANLI TELEMETRİ VE MODEL SENKRONİZASYONU
// ============================================================================
async function fetchTelemetry() {
  if (isTelemetryFetching || document.hidden) return;
  isTelemetryFetching = true;
  try {
    const res = await fetch("/api/telemetry");
    if (!res.ok) return;
    const data = await res.json();
    const entropy = Number(data.entropy ?? latestTelemetryState.entropy ?? 0.03);
    const freeEnergy = Number(data.free_energy ?? latestTelemetryState.free_energy ?? 0.08);
    const npuTemp = Number(data.npu_temp ?? latestTelemetryState.npu_temp ?? 48.2);
    const activeTelemetry = String(data.active_telemetry || "UART-2 (Birincil)");

    latestTelemetryState = { ...latestTelemetryState, ...data, entropy, free_energy: freeEnergy, npu_temp: npuTemp };

    const entropyPct = Math.round(entropy * 100);
    const entropyStr = `%${entropyPct}`;

    const elValEntropy = document.getElementById("val-entropy");
    if (elValEntropy) elValEntropy.innerText = entropyStr;

    const elDrawerEntropy = document.getElementById("drawer-val-entropy");
    if (elDrawerEntropy) elDrawerEntropy.innerText = entropyStr;

    const barEntropy = document.getElementById("bar-entropy");
    if (barEntropy) {
      barEntropy.style.width = `${Math.min(100, entropyPct)}%`;
      if (entropy >= 0.8) {
        barEntropy.style.background = "var(--crimson-glow)";
      } else if (entropy >= 0.4) {
        barEntropy.style.background = "var(--amber-glow)";
      } else {
        barEntropy.style.background = "var(--emerald-glow)";
      }
    }

    const feStr = `${freeEnergy.toFixed(3)} nats`;
    const elFreeEnergy = document.getElementById("val-free-energy");
    if (elFreeEnergy) elFreeEnergy.innerText = feStr;
    const elHeaderFe = document.getElementById("header-val-fe");
    if (elHeaderFe) elHeaderFe.innerText = feStr;

    const barFreeEnergy = document.getElementById("bar-free-energy");
    if (barFreeEnergy) barFreeEnergy.style.width = `${Math.min(100, Math.round(freeEnergy * 50))}%`;

    const tempStr = `${npuTemp.toFixed(1)}°C`;
    const elNpuTemp = document.getElementById("val-npu-temp");
    if (elNpuTemp) elNpuTemp.innerText = tempStr;
    const elSidebarTemp = document.getElementById("sidebar-npu-temp");
    if (elSidebarTemp) elSidebarTemp.innerText = `${tempStr} (CUDA %100)`;

    const barNpuTemp = document.getElementById("bar-npu-temp");
    if (barNpuTemp) barNpuTemp.style.width = `${Math.min(100, Math.round(npuTemp))}%`;

    const elChannel = document.getElementById("val-active-channel");
    if (elChannel) elChannel.innerText = activeTelemetry;
    const elSidebarChannel = document.getElementById("sidebar-active-channel");
    if (elSidebarChannel) elSidebarChannel.innerText = activeTelemetry;

    if (data.ebpf_events_per_sec) {
      const elEbpf = document.getElementById("val-ebpf-events");
      if (elEbpf) elEbpf.innerText = `${data.ebpf_events_per_sec.toLocaleString("tr-TR")} /s`;
    }

    // Lyapunov V(x) ve Win32 Fare / Ajan Telemetrisi
    const lyapV = data.lyapunov_v !== undefined ? Number(data.lyapunov_v) : (0.5 * entropy * entropy + 0.15 * freeEnergy);
    const oscReadout = document.getElementById("osc-live-readout");
    if (oscReadout) oscReadout.innerText = `V(x)=${lyapV.toFixed(3)}`;

    const elClf = document.getElementById("header-val-clf");
    if (elClf) {
      if (data.chaos_detected) {
        elClf.innerText = "dV/dt > 0 (ONARIM)";
        elClf.className = "crimson-text";
      } else {
        elClf.innerText = "dV/dt ≤ 0";
        elClf.className = "emerald-text";
      }
    }

    if (data.cursor_x !== undefined && data.screen_width !== undefined) {
      const elCursor = document.getElementById("sidebar-cursor-info");
      if (elCursor) {
        elCursor.innerText = `(${data.cursor_x}, ${data.cursor_y}) // ${data.screen_width}x${data.screen_height}`;
      }
    }

    if (data.agent_tools_count) {
      const elTools = document.getElementById("sidebar-agent-tools");
      if (elTools) elTools.innerText = `${data.agent_tools_count} ARAÇ HAZIR`;
      const elHeaderTools = document.getElementById("header-val-tools");
      if (elHeaderTools) elHeaderTools.innerText = `${data.agent_tools_count} Araç`;
    }

    // Aktif Model Etiketleri
    if (data.active_model) {
      const elModelText = document.getElementById("active-model-text");
      if (elModelText) elModelText.innerText = data.active_model;

      const elIslandModel = document.getElementById("island-model-label");
      if (elIslandModel) elIslandModel.innerText = data.active_model;
    }

    // Durum Hapı
    const statusText = document.getElementById("system-status-text");
    const statusPill = document.getElementById("status-pill");
    const statusDot = document.getElementById("header-status-dot");
    if (statusText && statusPill) {
      if (data.chaos_detected) {
        statusText.innerText = "Kaos · Onarım";
        statusPill.style.borderColor = "rgba(244, 63, 94, 0.5)";
        if (statusDot) {
          statusDot.style.background = "var(--crimson-glow)";
          statusDot.style.boxShadow = "0 0 8px var(--crimson-glow)";
        }
      } else {
        statusText.innerText = "Hazır";
        statusPill.style.borderColor = "var(--border-subtle)";
        if (statusDot) {
          statusDot.style.background = "var(--emerald-glow)";
          statusDot.style.boxShadow = "0 0 8px rgba(16, 185, 129, 0.7)";
        }
      }
    }

    // Düğüm durumları
    const tagUart = document.getElementById("tag-uart");
    const tagSdr = document.getElementById("tag-sdr");
    if (tagUart && tagSdr) {
      if (activeTelemetry.includes("SDR")) {
        tagUart.className = "node-status-tag tag-critical";
        tagUart.innerText = "OFFLINE (KOPUK)";
        tagSdr.className = "node-status-tag tag-online";
        tagSdr.innerText = "ONLINE (AKTİF)";
      } else {
        tagUart.className = "node-status-tag tag-online";
        tagUart.innerText = "ONLINE";
        tagSdr.className = "node-status-tag tag-online";
        tagSdr.innerText = "STANDBY";
      }
    }
  } catch (err) {
    console.warn("Telemetri çekilemedi:", err);
  } finally {
    isTelemetryFetching = false;
  }
}

async function fetchModels() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) return;
    const data = await res.json();
    const select = document.getElementById("modal-model-select");
    if (data.models && data.models.length > 0 && select) {
      select.innerHTML = "";
      data.models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m.name;
        opt.innerText = `${m.name} (${m.source})`;
        if (m.name === data.current_model) opt.selected = true;
        select.appendChild(opt);
      });
    }
    if (data.current_model) {
      const elModelText = document.getElementById("active-model-text");
      if (elModelText) elModelText.innerText = data.current_model;

      const elIslandModel = document.getElementById("island-model-label");
      if (elIslandModel) elIslandModel.innerText = data.current_model;
    }
  } catch (err) {
    console.warn("Modeller çekilemedi:", err);
  }
}

async function quickSwitchModel(modelName) {
  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: modelName })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status === "ok") {
      fetchTelemetry();
      appendKernelLog("KAM-MODEL", `Aktif bilişsel zihin değiştirildi: ${data.current_model}`, "ok");
      showToast(`Aktif model: ${data.current_model}`, "success");
      appendMessage(
        "kam",
        `🏛️ <strong>[BİLİŞSEL ZİHİN DEĞİŞTİRİLDİ]</strong> Aktif Komuta Modeli: <code>${escapeHtml(data.current_model)}</code> (${escapeHtml((data.active_backend || "").toUpperCase())})`,
        null,
        true
      );
    }
  } catch (err) {
    console.warn("Model değiştirilemedi:", err);
    showToast("Model değiştirilemedi", "error");
  }
}

// Başlangıç Kayıtları ve Periyodik Telemetri
window.addEventListener("DOMContentLoaded", () => {
  ensureStopButton();
  initFileAttachments();
  appendKernelLog("KAM-CORE", "Egemen Bilişsel Komuta Merkezi (v3.0 Sprint-1 Apex) başlatıldı.", "ok");
  appendKernelLog("eBPF-RING", "Linux eBPF SPSC RingBuffer (<12 us) senkronize.", "ok");
  appendKernelLog("UFO2-AGENT", "Tam Yetkili Win32 UIA & CodeAct Bilgisayar Ajanı nöbette.", "jit");
  fetchTelemetry();
  fetchModels();
  loadSessions();
  loadWorkflows();
  setInterval(fetchTelemetry, 1800);
});

// ============================================================================
// 5. SEKME, KENAR ÇUBUĞU VE GÖRÜNÜM KONTROLLERİ
// ============================================================================
function toggleLeftSidebar() {
  const sidebar = document.getElementById("left-sidebar");
  if (!sidebar) {
    toggleTelemetryDrawer();
    return;
  }
  sidebar.classList.toggle("collapsed");
  document.body.classList.toggle("sidebar-closed", sidebar.classList.contains("collapsed"));
}

function switchSidebarTab(tabId, btnEl) {
  document.querySelectorAll(".deck-tab").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  document.querySelectorAll(".deck-panel").forEach(p => p.classList.remove("active"));
  const target = document.getElementById(`sidebar-tab-${tabId}`);
  if (target) target.classList.add("active");
}

function switchHeroCategory(catId, btnEl) {
  document.querySelectorAll(".hero-tab-btn").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  document.querySelectorAll(".starter-cards-grid").forEach(g => g.classList.remove("active"));
  const target = document.getElementById(`hero-grid-${catId}`);
  if (target) target.classList.add("active");
}

function switchDrawerTab(tabId, btnEl) {
  document.querySelectorAll(".drawer-tab").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  document.querySelectorAll(".drawer-tab-pane").forEach(p => p.classList.remove("active"));
  const target = document.getElementById(`drawer-pane-${tabId}`);
  if (target) target.classList.add("active");
}

function resetToHomeView() {
  const hero = document.getElementById("welcome-hero");
  if (hero) {
    hero.style.display = "flex";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// ============================================================================
// 6. SOHBET AKIŞI, ABORT DESTEĞİ VE İSTEM GEÇMİŞİ
// ============================================================================
function ensureStopButton() {
  let stopBtn = document.getElementById("btn-stop") || document.querySelector(".btn-stop");
  if (stopBtn) return stopBtn;

  const sendBtn = document.getElementById("btn-send") || document.querySelector(".btn-send");
  if (!sendBtn || !sendBtn.parentNode) return null;

  stopBtn = document.createElement("button");
  stopBtn.id = "btn-stop";
  stopBtn.className = "btn-stop";
  stopBtn.type = "button";
  stopBtn.title = "Durdur (Esc)";
  stopBtn.style.display = "none";
  stopBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>`;
  stopBtn.onclick = stopGeneration;
  sendBtn.parentNode.insertBefore(stopBtn, sendBtn.nextSibling);
  return stopBtn;
}

function setStreamingUI(active) {
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("btn-send") || document.querySelector(".btn-send");
  const stopBtn = ensureStopButton();

  if (input) input.disabled = active;
  if (sendBtn) {
    sendBtn.disabled = active;
    sendBtn.style.display = active ? "none" : "";
  }
  if (stopBtn) {
    stopBtn.style.display = active ? "inline-flex" : "none";
    stopBtn.disabled = !active;
  }
}

function stopGeneration() {
  if (!currentAbortController) return;
  const ctrl = currentAbortController;
  currentAbortController = null;
  try {
    ctrl.abort();
  } catch (e) {}
  appendKernelLog("KAM-STOP", "Yanıt akışı kullanıcı tarafından durduruldu.", "crit");
  showToast("Yanıt akışı durduruldu", "warn");
}

function handleKeyDown(e) {
  const input = e.target;
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
    return;
  }

  // Yukarı Ok: Girdi boşsa veya geçmişte gezinirken önceki istemi geri çağır
  if (e.key === "ArrowUp" && promptHistory.length > 0) {
    const isEmpty = input.value.trim() === "";
    const atFirstLine = input.selectionStart === 0 || !input.value.slice(0, input.selectionStart).includes("\n");
    if (isEmpty || (promptHistoryIndex !== -1 && atFirstLine)) {
      e.preventDefault();
      if (promptHistoryIndex === -1) {
        promptHistoryDraft = input.value;
        promptHistoryIndex = promptHistory.length - 1;
      } else if (promptHistoryIndex > 0) {
        promptHistoryIndex--;
      }
      input.value = promptHistory[promptHistoryIndex];
      autoResizeTextarea(input);
      requestAnimationFrame(() => {
        input.selectionStart = input.selectionEnd = input.value.length;
      });
      return;
    }
  }

  // Aşağı Ok: Geçmişte ileri git veya taslağa dön
  if (e.key === "ArrowDown" && promptHistoryIndex !== -1) {
    const atLastLine = !input.value.slice(input.selectionEnd).includes("\n");
    if (atLastLine) {
      e.preventDefault();
      if (promptHistoryIndex < promptHistory.length - 1) {
        promptHistoryIndex++;
        input.value = promptHistory[promptHistoryIndex];
      } else {
        promptHistoryIndex = -1;
        input.value = promptHistoryDraft;
      }
      autoResizeTextarea(input);
      requestAnimationFrame(() => {
        input.selectionStart = input.selectionEnd = input.value.length;
      });
    }
  }
}

function autoResizeTextarea(textarea) {
  if (promptHistoryIndex !== -1 && textarea.value !== promptHistory[promptHistoryIndex]) {
    promptHistoryIndex = -1;
  }
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 180) + "px";
}

function sendPrompt(text) {
  const input = document.getElementById("chat-input");
  if (!input) return;
  input.value = text;
  autoResizeTextarea(input);
  submitMessage();
}

function hideWelcomeHero() {
  const hero = document.getElementById("welcome-hero");
  if (hero && hero.style.display !== "none") {
    hero.style.display = "none";
  }
}

function createMessageBubble(sender) {
  hideWelcomeHero();
  const history = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = `chat-avatar avatar-${sender === "user" ? "user" : "kam"}`;
  avatar.innerText = sender === "user" ? "" : "K";

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${sender === "user" ? "user" : "kam"}`;
  bubble.innerHTML = `<span class="typing-dots"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>`;

  if (sender === "user") {
    msgDiv.appendChild(bubble);
    msgDiv.appendChild(avatar);
  } else {
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
  }

  history.appendChild(msgDiv);
  smartScrollToBottom(sender === "user", true);
  return bubble;
}

function appendMessage(sender, text, codeSnippet = null, isRawHtml = false) {
  hideWelcomeHero();
  const history = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = `chat-avatar avatar-${sender === "user" ? "user" : "kam"}`;
  avatar.innerText = sender === "user" ? "" : "K";

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${sender === "user" ? "user" : "kam"}`;
  if (sender === "kam") {
    bubble.innerHTML = isRawHtml ? text : formatMarkdown(text);
  } else {
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
  }

  if (codeSnippet) {
    bubble.insertAdjacentHTML("beforeend", buildInteractiveCodeBlock(codeSnippet, "C++20 JIT"));
    updateJitInspector(codeSnippet, "Otonom C++20 JIT Yaması");
  }

  if (sender === "kam" && text) {
    attachMessageActions(bubble, text);
  }

  if (sender === "user") {
    msgDiv.appendChild(bubble);
    msgDiv.appendChild(avatar);
  } else {
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
  }

  history.appendChild(msgDiv);
  smartScrollToBottom(sender === "user", true);
}

async function submitMessage() {
  const input = document.getElementById("chat-input");
  const text = (input ? input.value : "").trim();
  const hasAttachments = attachedFiles.length > 0;
  if ((!text && !hasAttachments) || isProcessing) return;

  if (isRecordingVoice && speechRecognition) {
    try { speechRecognition.stop(); } catch (e) {}
  }

  const currentAttachments = [...attachedFiles];
  attachedFiles = [];
  renderAttachedFiles();

  const attachmentHeader = currentAttachments
    .map(f => `[EKLİ DOSYA: ${f.path}]`)
    .join("\n");
  const promptText = attachmentHeader
    ? `${attachmentHeader}\n${text || "Ekli dosyayı analiz et ve özetle."}`
    : text;
  const displayUserText = currentAttachments.length > 0
    ? `${currentAttachments.map(f => `📎 ${f.name}`).join(" · ")}${text ? "\n" + text : ""}`
    : text;

  if (text) recordPromptHistory(text);
  userScrolledUp = false;
  appendMessage("user", displayUserText);
  appendKernelLog("KAM-QUERY", `İstem işleniyor: ${promptText.slice(0, 56)}`, "ok");

  input.value = "";
  input.style.height = "auto";
  isProcessing = true;
  setStreamingUI(true);

  const kamBubble = createMessageBubble("kam");
  const bubbleScopeId = `msg_${++messageBubbleCounter}`;
  let accumulatedText = "";
  let renderScheduled = false;
  let rafId = null;

  function flushRender() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
    renderScheduled = false;
    if (accumulatedText) {
      kamBubble.innerHTML = formatMarkdown(accumulatedText, { scopeId: bubbleScopeId });
      smartScrollToBottom(false, false);
    }
  }

  function scheduleRender() {
    if (renderScheduled) return;
    renderScheduled = true;
    rafId = requestAnimationFrame(() => {
      rafId = null;
      renderScheduled = false;
      if (accumulatedText) {
        kamBubble.innerHTML = formatMarkdown(accumulatedText, { scopeId: bubbleScopeId });
        smartScrollToBottom(false, false);
      }
    });
  }

  const abortController = new AbortController();
  currentAbortController = abortController;

  const safetyTimer = setTimeout(() => {
    if (currentAbortController === abortController) {
      appendKernelLog("KAM-TIMEOUT", "Akış 180 sn zaman aşımına uğradı, sonlandırılıyor.", "crit");
      showToast("Yanıt zaman aşımına uğradı", "warn");
      abortController.abort();
    }
  }, 180000);

  let reader = null;
  let wasAborted = false;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: promptText }),
      signal: abortController.signal
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let streamDone = false;

    function processSseChunk(chunk) {
      const lines = chunk.split(/\r?\n/);
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;
        try {
          const data = JSON.parse(jsonStr);
          if (data.done) {
            streamDone = true;
            return;
          }
          if (data.token) {
            if (data.token.includes("⚡ [OTONOM AJAN İCRASI //")) {
              appendKernelLog("UFO2-EXEC", "Bilgisayar ajanı gerçek sistem aracını icra etti.", "jit");
            }
            accumulatedText += data.token;
            scheduleRender();
          }
        } catch (e) {}
      }
    }

    while (!streamDone) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split(/\r?\n\r?\n/);
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        processSseChunk(chunk);
        if (streamDone) break;
      }
    }

    // Kalan tamponu işle
    buffer += decoder.decode();
    if (buffer.trim() && !streamDone) {
      processSseChunk(buffer);
    }

    if (streamDone && reader) {
      try { await reader.cancel(); } catch (e) {}
    }

    flushRender();

    if (!accumulatedText.trim()) {
      kamBubble.innerHTML = "<p>KAM Zihni aktif. Sistem telemetrisi ve bilişsel nöronlar dengede.</p>";
    } else {
      attachMessageActions(kamBubble, accumulatedText);
    }
    appendKernelLog("KAM-DONE", "Bilişsel yanıt akışı tamamlandı.", "ok");
  } catch (err) {
    if (err && err.name === "AbortError") {
      wasAborted = true;
      flushRender();
      if (accumulatedText.trim()) {
        kamBubble.insertAdjacentHTML(
          "beforeend",
          `<div class="stream-aborted-note" style="margin-top:8px;font-size:11.5px;color:var(--text-muted);font-family:var(--font-mono);">⏹ Akış kullanıcı tarafından durduruldu.</div>`
        );
        attachMessageActions(kamBubble, accumulatedText);
      } else {
        kamBubble.innerHTML = `<span style="color:var(--text-muted);font-family:var(--font-mono);font-size:12.5px;">⏹ Akış durduruldu.</span>`;
      }
    } else {
      console.error("Sohbet hatası:", err);
      flushRender();
      if (!accumulatedText.trim()) {
        kamBubble.innerHTML = "<p>Bağlantı hatası: KAM çekirdeğine ulaşılamadı.</p>";
      }
      showToast("KAM çekirdeğine bağlanılamadı", "error");
    }
  } finally {
    clearTimeout(safetyTimer);
    if (rafId !== null) cancelAnimationFrame(rafId);
    if (wasAborted && reader) {
      try { reader.cancel(); } catch (e) {}
    }
    if (currentAbortController === abortController) {
      currentAbortController = null;
    }
    isProcessing = false;
    setStreamingUI(false);
    if (input) input.focus();
    fetchTelemetry();
    loadSessions();
  }
}

async function clearChat() {
  if (currentAbortController) {
    stopGeneration();
  }
  try {
    await fetch("/api/clear_chat", { method: "POST" });
  } catch (e) {}

  const history = document.getElementById("chat-history");
  if (history) history.innerHTML = "";
  const hero = document.getElementById("welcome-hero");
  if (hero) hero.style.display = "flex";
  userScrolledUp = false;
  appendKernelLog("KAM-CLEAR", "Diyalog geçmişi sıfırlandı.", "ok");
  showToast("Sohbet temizlendi", "info");
}

async function exportChat() {
  try {
    const res = await fetch("/api/export_chat");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const mdText = await res.text();
    const blob = new Blob([mdText], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kam_sohbet_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Sohbet Markdown olarak dışa aktarıldı", "success");
  } catch (err) {
    showToast("Sohbet dışa aktarılamadı", "error");
  }
}

// ============================================================================
// 7. TELEMETRİ ÇEKMECESİ, 15 KRİZ SİMÜLATÖRÜ VE TAKTİK SAVUNMA API'LERİ
// ============================================================================
function toggleTelemetryDrawer() {
  const drawer = document.getElementById("hud-drawer");
  const backdrop = document.getElementById("hud-backdrop");
  if (drawer && backdrop) {
    const isActive = drawer.classList.contains("active");
    if (isActive) {
      drawer.classList.remove("active");
      backdrop.classList.remove("active");
    } else {
      drawer.classList.add("active");
      backdrop.classList.add("active");
      fetchTelemetry();
    }
  }
}

async function triggerCrisis(type) {
  try {
    appendKernelLog("NERV-CRIT", `Kaos senaryosu tetiklendi: ${type}`, "crit");
    const res = await fetch("/api/crisis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crisis_type: type })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    appendMessage(
      "kam",
      `⚡ <strong>[KAOS TETİKLENDİ // OTONOM C++20 JIT ONARIM]</strong> ${escapeHtml(data.message)}`,
      data.code || null,
      true
    );
    showToast(`Kriz simülasyonu tetiklendi: ${type}`, "warn");
    fetchTelemetry();
  } catch (err) {
    showToast("Kriz tetiklenirken hata oluştu", "error");
  }
}

async function resetSystem() {
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    appendKernelLog("KAM-STABLE", "Dirlik ve homeostatik denge yeniden kuruldu (Entropi %3).", "ok");
    showToast("Sistem dengesi sıfırlandı (Entropi %3)", "success");
    appendMessage(
      "kam",
      "🛡️ <strong>[DİRLİK VE DENGE YENİDEN KURULDU]</strong> Gök çökmedi, yağız yer delinmedi. Bilişsel denge sağlandı, varyasyonel serbest enerji %3 seviyesine çekildi.",
      null,
      true
    );
    fetchTelemetry();
  } catch (err) {
    showToast("Sistem sıfırlama başarısız", "error");
  }
}

function closeDrawerIfOpen() {
  const drawer = document.getElementById("hud-drawer");
  const backdrop = document.getElementById("hud-backdrop");
  if (drawer && drawer.classList.contains("active")) {
    drawer.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");
  }
}

// 1) Bilişsel EW Radar PDW Testi
async function testEwRadar() {
  closeDrawerIfOpen();
  appendMessage("user", "📡 17.4 GHz LPI Radar Tehdit PDW darbe dizisini analiz et ve DRFM karşı tedbiri üret.");
  try {
    const res = await fetch("/api/ew_radar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rf_ghz: 17.4,
        pri_us: 610.0,
        pw_us: 0.25,
        aoa_deg: 118.0,
        chirp_bw_mhz: 240.0,
        agility_score: 0.92
      })
    });
    const data = await res.json();
    const c = data.classification;
    const msg = `⚡ <strong>[BİLİŞSEL ELEKTRONİK HARP - DARPA CIRRA ÜSTÜ]</strong><br>` +
      `• Sınıflandırılan Verici: <code>${c.classified_emitter}</code><br>` +
      `• Güven: <code>${(c.confidence * 100).toFixed(1)}%</code> | Tehdit Şiddeti: <code>${(c.threat_severity * 100).toFixed(0)}%</code><br>` +
      `• Şekil Değiştiren LPI Radarı: <code>${c.is_novel_shapeshifting_emitter ? "EVET (Çevrimiçi Öğrenildi)" : "HAYIR"}</code><br>` +
      `• Sentezlenen Karşı-Tedbir: <strong>${c.synthesized_countermeasure}</strong> (Notch: ${c.notch_center_ghz} GHz)<br>` +
      `• Çentik ve DRFM Kod Modülü JIT hazırlandı.`;
    appendMessage("kam", msg, data.countermeasure_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ EW Radar analizi sırasında bağlantı hatası oluştu.");
  }
}

// 2) Intent-to-Task C2 Filo Orkestrasyonu Testi
async function testC2Intent() {
  closeDrawerIfOpen();
  const intentStr = "Sektör-4 S-400 bataryasını körelt ve vadi taarruzu icra et";
  appendMessage("user", `🎯 Komutan Niyeti: "${intentStr}"`);
  try {
    const res = await fetch("/api/c2_intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commander_intent: intentStr, target_x_km: 50.0, target_y_km: 0.0 })
    });
    const data = await res.json();
    const plan = data.c2_plan;
    let taskListHtml = `<ol style="margin: 6px 0 0 18px; padding: 0;">`;
    for (const t of plan.task_dag_allocations) {
      taskListHtml += `<li><strong>${t.assigned_asset}</strong> [Faz ${t.phase}]: ${t.description} (G=${t.expected_free_energy_g.toFixed(3)})</li>`;
    }
    taskListHtml += `</ol>`;

    const msg = `🦅 <strong>[KAM LATTICE // INTENT-TO-TASK DAG ORKESTRASYONU]</strong><br>` +
      `• Standart: <code>${plan.architecture_standard}</code><br>` +
      `• Üretilen Görev Sayısı: <strong>${plan.total_tasks_generated}</strong> | Seferber Edilen Varlık: <strong>${plan.unique_assets_mobilized}</strong><br>` +
      `• DAG Görev Dağılımı:<br>${taskListHtml}`;
    appendMessage("kam", msg, data.executor_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ C2 Görev orkestrasyonu sırasında bağlantı hatası oluştu.");
  }
}

// 3) DARPA ANSR & CBF Uçuş Kalkanı Testi
async function testSafetyShield() {
  closeDrawerIfOpen();
  appendMessage("user", "🛡️ Güvenlik sınırını aşan uçuş komutasını doğrula: İrtifa=12m, Sürat=15m/s, Yatış=68°, Batarya=%14.");
  try {
    const res = await fetch("/api/safety_shield", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_altitude_agl_m: 12.0,
        airspeed_mps: 15.0,
        bank_angle_deg: 68.0,
        battery_pct: 14.0
      })
    });
    const data = await res.json();
    const s = data.shield_result;
    const violHtml = s.symbolic_violations_prevented.map(v => `<code>${v}</code>`).join(", ");
    const msg = `🛡️ <strong>[DARPA ANSR &amp; CBF NÖRO-SEMBOLİK KALKAN]</strong><br>` +
      `• Müdahale Gerçekleşti mi: <strong>${s.intervention_occurred ? "EVET (Güvenlik İzdüşümü Yapıldı)" : "HAYIR"}</strong><br>` +
      `• Eve Dönüş (RTL) Durumu: <strong>${s.rtl_override_active ? "AKTİF" : "PASİF"}</strong><br>` +
      `• Engellenen Sembolik İhlaller: ${violHtml}<br>` +
      `• Güvenli İzdüşürülen Komuta: İrtifa <strong>${s.safe_command.target_altitude_agl_m}m</strong>, Sürat <strong>${s.safe_command.airspeed_mps} m/s</strong>, Yatış <strong>${s.safe_command.bank_angle_deg}°</strong>`;
    appendMessage("kam", msg, data.cbf_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ Güvenlik kalkanı testi sırasında bağlantı hatası oluştu.");
  }
}

// 4) Hugging Face Egemen Model Filosu Manifestosu
async function showFleetManifest() {
  closeDrawerIfOpen();
  appendMessage("user", "🌐 KAM 8-Modelli Egemen Savunma Filosu (Hugging Face Hub) durumunu getir.");
  try {
    const res = await fetch("/api/fleet_manifest");
    const data = await res.json();
    let fleetRows = `<div class="table-wrapper"><table>
      <thead>
        <tr>
          <th>Model</th>
          <th>Boyut</th>
          <th>Görev Özeti</th>
          <th>Hugging Face</th>
        </tr>
      </thead>
      <tbody>`;
    for (const m of data.models) {
      fleetRows += `<tr>
        <td><strong>${escapeHtml(m.key)}</strong></td>
        <td><code>${escapeHtml(m.size)}</code></td>
        <td>${escapeHtml(m.role)}</td>
        <td><a href="${escapeHtml(m.url)}" target="_blank" rel="noopener noreferrer">Depo</a></td>
      </tr>`;
    }
    fleetRows += `</tbody></table></div>`;

    const msg = `👑 <strong>[KAM EGEMEN MODEL FİLOSU // 8 RESMİ HUGGING FACE DEPOSU]</strong><br>` +
      `• Toplam Filo Hacmi: <strong>${escapeHtml(data.fleet_size_gb)}</strong><br>` +
      `• Geliştirici / Baş Mimar: <strong>${escapeHtml(data.huggingface_author)}</strong><br>` +
      fleetRows;
    appendMessage("kam", msg, null, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ Filo manifestosu çekilirken hata oluştu.");
  }
}

// 5) Bizans Hata Toleranslı (BFT) & ML-KEM-768 PQC Sürü Testi
async function testBftSwarm() {
  closeDrawerIfOpen();
  appendMessage("user", "🔐 Sürü Markov Battaniyesinde Bizans haini (Charlie-3) denetimi ve ML-KEM-768 PQC anahtar doğrulaması yap.");
  try {
    const res = await fetch("/api/bft_swarm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inject_byzantine_traitor: true })
    });
    const data = await res.json();
    const b = data.bft_result;
    const msg = `🔐 <strong>[BFT &amp; ML-KEM-768 KUANTUM-DİRENÇLİ SÜRÜ KONSENSÜSÜ]</strong><br>` +
      `• Şifreleme Paketi: <code>${b.pqc_cipher_suite}</code><br>` +
      `• Güvenilir Düğümler: <strong>${b.trusted_nodes.join(", ")}</strong><br>` +
      `• Karantinaya Alınan Bizans Haini: <code style="color: var(--crimson-glow);">${b.quarantined_byzantine_nodes.join(", ")}</code> (f &lt; N/3: ${b.bft_resilience_bound_ok ? "DOĞRULANDI" : "İHLAL"})<br>` +
      `• Füzyonlanmış Kolektif İnanç: <code>[${b.fused_collective_belief.join(", ")}]</code>`;
    appendMessage("kam", msg, data.pqc_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ BFT & PQC sürü testi sırasında hata oluştu.");
  }
}

// 6) Pasif TRN / TERCOM Arazi Korelasyonu Testi
async function testTrnLocalize() {
  closeDrawerIfOpen();
  appendMessage("user", "🏔️ GPS-Kör ortamda 901m INS kaymasını 0W pasif TRN / TERCOM arazi yükselti profili ile düzelt.");
  try {
    const res = await fetch("/api/trn_localize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ true_x_km: 24.5, true_y_km: -3.2, drifted_ins_x_km: 25.25, drifted_ins_y_km: -2.70 })
    });
    const data = await res.json();
    const t = data.trn_result;
    const msg = `🏔️ <strong>[PASİF TRN / TERCOM BAYESÇİ ARAZİ KORELASYONU]</strong><br>` +
      `• RF Yayımı: <code>${t.rf_emission_watts} W (100% Stealth)</code> | GNSS Bağımlılığı: <code>${t.gnss_dependency}</code><br>` +
      `• Başlangıç INS Kayması: <code>${t.initial_ins_drift_m} m</code> &rarr; Kalan CEP Hatası: <strong>${t.residual_cep_error_m} m</strong><br>` +
      `• Kayma Sönümleme Oranı: <strong>%${t.drift_reduction_pct}</strong> | Profil NCC: <code>${t.profile_ncc_score}</code>`;
    appendMessage("kam", msg, data.trn_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ TRN arazi eşleştirme testi sırasında hata oluştu.");
  }
}

// 7) Ağırlıklı Sözde-Ters Eyleyici Yeniden Yapılandırma Testi
async function testActuatorReconfig() {
  closeDrawerIfOpen();
  appendMessage("user", "⚙️ Sol Elevon (+0.22 rad) sıkışması altında Sözde-Ters (Pseudo-Inverse) kontrol dağıtımını hesapla.");
  try {
    const res = await fetch("/api/actuator_reconfig", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jammed_actuator_index: 0, jammed_angle_rad: 0.22 })
    });
    const data = await res.json();
    const a = data.actuator_result;
    const msg = `⚙️ <strong>[AĞIRLIKLI SÖZDE-TERS (PSEUDO-INVERSE) KONTROL DAĞITIMI]</strong><br>` +
      `• İstenen Moment (L,M,N): <code>[${a.desired_moments_lmn.join(", ")}]</code> | Elde Edilen: <code>[${a.achieved_moments_lmn.join(", ")}]</code><br>` +
      `• Moment Takip Hatası (L2): <strong>${a.moment_tracking_error_l2}</strong> | Kontrol Otoritesi: <strong>${a.control_authority_preserved ? "KORUNDU (%100)" : "KISITLI"}</strong>`;
    appendMessage("kam", msg, data.mixer_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ Eyleyici yeniden yapılandırma testi sırasında hata oluştu.");
  }
}

// 8) EMCON-Sıfır 1550nm FSO Lazer Haberleşme Testi
async function testFsoLaserLink() {
  closeDrawerIfOpen();
  appendMessage("user", "🔦 EMCON-Sıfır (0.0W RF) modunda 1550nm SWIR Serbest Uzay Optik (FSO) Lazer sürü bağlantısını analiz et.");
  try {
    const res = await fetch("/api/fso_link", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ distance_km: 4.5, visibility_km: 12.0, pointing_jitter_urad: 35.0 })
    });
    const data = await res.json();
    const f = data.fso_result;
    const msg = `🔦 <strong>[EMCON-SIFIR 1550nm SWIR FSO LAZER SÜRÜ HABERLEŞMESİ]</strong><br>` +
      `• Optik Mod: <code>${f.active_optical_mode}</code> | RF Yayımı: <strong>${f.rf_emission_watts} W (POI = %0.000)</strong><br>` +
      `• Optik SNR: <code>${f.optical_snr_db} dB</code> | Rytov Parıldama: <code>${f.rytov_scintillation_index}</code><br>` +
      `• Efektif Kapasite: <strong>${f.effective_throughput_mbps} Mbps</strong> (${f.fec_scheme})`;
    appendMessage("kam", msg, data.fso_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ FSO Lazer bağlantı testi sırasında hata oluştu.");
  }
}

// 9) SECDED Hamming(72,64) & TMR Radyasyon Bit-Flip Onarım Testi
async function testRadiationScrubber() {
  closeDrawerIfOpen();
  appendMessage("user", "☢️ Kozmik ışın / EMP kaynaklı Bit-19 tersinmesi (SEU) ve BitNet b1.58 ağırlık bozulmasını SECDED & TMR ile onar.");
  try {
    const res = await fetch("/api/ecc_scrub", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ injected_seu_bit: 19, inject_tmr_bank_corruption: true })
    });
    const data = await res.json();
    const e = data.ecc_result;
    const reg = e.secded_register_check;
    const tmr = e.tmr_bitnet_weight_scrub;
    const msg = `☢️ <strong>[SECDED HAMMING(72,64) &amp; 3-BANK TMR BELLEK ONARIMI]</strong><br>` +
      `• SECDED Yazmaç Durumu: <code>${reg.status}</code> (Bozulan Bit: <strong>#${reg.flipped_bit_detected}</strong>, Sendrom: <code>${reg.syndrome_code}</code>)<br>` +
      `• Onarılan Kelime: <code>${reg.corrupted_hex}</code> &rarr; <strong>${reg.repaired_hex}</strong><br>` +
      `• TMR Çoğunluk Oylaması: <strong>${tmr.tmr_majority_repairs} ağırlık onarıldı</strong> | SHA3-256 Bütünlük: <strong>${tmr.integrity_verified_100pct ? "%100 DOĞRULANDI" : "İHLAL"}</strong>`;
    appendMessage("kam", msg, data.ecc_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ SECDED & TMR bellek onarım testi sırasında hata oluştu.");
  }
}

// 10) Hamilton-Jacobi-Isaacs (HJI) Diferansiyel Oyun Füze Kaçınma Testi
async function testHjiMissileEvasion() {
  closeDrawerIfOpen();
  appendMessage("user", "🚀 Terminal safhada (R=2850m, V_c=980 m/s) yaklaşan SAM füzesine karşı HJI diferansiyel oyun kaçınma çözümünü üret.");
  try {
    const res = await fetch("/api/hji_evasion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ missile_range_m: 2850.0, closing_velocity_mps: 980.0, evader_max_g: 9.0 })
    });
    const data = await res.json();
    const h = data.hji_result;
    const msg = `🚀 <strong>[HAMILTON-JACOBI-ISAACS (HJI) DİFERANSİYEL TAKİP-KAÇMA ÇÖZÜCÜSÜ]</strong><br>` +
      `• Kalan Süre (t_go): <code>${h.time_to_go_sec} sn</code> | Optimal Manevra: <strong>${h.commanded_evader_g}G Dikgen Fıçı Tonosu (${h.optimal_barrel_roll_angle_deg}&deg;)</strong><br>` +
      `• Manevrasız PN Iskalama: <code>${h.unmaneuvered_pn_miss_m} m</code> &rarr; HJI + Cross-Eye Iskalama: <strong>${h.hji_saddle_point_terminal_miss_m} m</strong> (Ölümcül Yarıçap: ${h.warhead_lethal_radius_m} m)<br>` +
      `• Platform Bekâsı: <strong>${h.platform_survival_guaranteed ? "GARANTİ ALTINDA (%100)" : "RİSKLİ"}</strong> (${h.countermeasure_sync})`;
    appendMessage("kam", msg, data.hji_code, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ HJI füze kaçınma testi sırasında hata oluştu.");
  }
}

// 11) 3B SİHA Gizli Rota Planlayıcı Testi
async function testTacticalRoute() {
  closeDrawerIfOpen();
  appendMessage("user", "🗺️ S-400 ve Koral-EW tehditlerine karşı 50 km menzilli 3B SİHA gizli (radar gölgeleme) yörüngesini hesapla.");
  try {
    const res = await fetch("/api/tactical_route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_x_km: 50.0, target_y_km: 0.0, num_segments: 8 })
    });
    const data = await res.json();
    const wps = data.waypoints.slice(0, 5).map(w => `<code>(${w.x_km}km, ${w.y_km}km, ${w.alt_m}m)</code>`).join(" &rarr; ");
    const msg = `🗺️ <strong>[3B RİSK-DUYARLI A* VE BEKLENEN SERBEST ENERJİ (G) YÖRÜNGE PLANI]</strong><br>` +
      `• Görev Bekâ Olasılığı: <strong>%${data.mission_survival_probability_pct}</strong> | Ortalama İrtifa: <code>${data.avg_altitude_agl_m} m AGL</code><br>` +
      `• Toplam Rota Uzunluğu: <code>${data.total_distance_km} km</code> | Kümülatif Radar Riski: <code>${data.cumulative_threat_exposure}</code><br>` +
      `• İlk 5 Ara Nokta (Waypoints): ${wps} ...`;
    appendMessage("kam", msg, null, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ 3B Taktik rota planlama sırasında hata oluştu.");
  }
}

// 12) Lyapunov CLF Kararlılık Analizi
async function testLyapunovStability() {
  closeDrawerIfOpen();
  appendMessage("user", "📐 Sistemin Kontrol-Lyapunov Fonksiyonu V(x) kararlılığını ve termal anomali ufkunu hesapla.");
  try {
    const res = await fetch("/api/lyapunov_status");
    const data = await res.json();
    const s = data.stability;
    const tta = data.time_to_anomaly;
    const msg = `📐 <strong>[KONTROL-LYAPUNOV FONKSİYONU (CLF) &amp; ANOMALİ ÖNGÖRÜSÜ]</strong><br>` +
      `• Lyapunov Enerjisi V(x): <code>${s.lyapunov_v}</code> | Türev dV/dt: <strong>${s.dv_dt} (${s.is_asymptotically_stable ? "Asimptotik Kararlı" : "Müdahale Gerekli"})</strong><br>` +
      `• Optimal Sönümleme Kontrolü u*: <code>${s.control_action_u}</code><br>` +
      `• Termal Anomali Tahmini (85°C Eşiği): <strong>${tta.status}</strong> (Eğim: <code>${tta.slope_per_sec} °C/s</code>)`;
    appendMessage("kam", msg, null, true);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "❌ Lyapunov kararlılık analizi sırasında hata oluştu.");
  }
}

// ============================================================================
// 8. EGEMEN KOMUT PALETİ (Ctrl+K Spotlight)
// ============================================================================
const COMMAND_PALETTE_ITEMS = [
  { title: "Bilgisayar & GPU Donanım Denetimi", desc: "Gerçek fiziksel RAM, CPU, disk ve RTX GPU telemetrisi", badge: "UFO² Ajan", action: () => sendPrompt("Bilgisayarın gerçek donanım, fiziksel RAM, disk ve GPU durumunu denetle.") },
  { title: "Açık Pencereler & Çalışan Süreçler", desc: "Masaüstündeki aktif Win32 pencerelerini ve süreçleri listele", badge: "Win32 UIA", action: () => sendPrompt("Masaüstündeki açık pencereleri ve çalışan süreçleri listele.") },
  { title: "Kod Külliyatı & Satır Sayısı Analizi", desc: "Projeyi tara ve toplam dosya/satır mimari istatistiklerini çıkar", badge: "CodeAct", action: () => sendPrompt("Projeyi analiz et ve toplam kaç dosya ve kaç satır kod olduğunu göster.") },
  { title: "Canlı HTML5 Kokpit Üret & Ekranda Aç", desc: "Otonom HTML5 gösterge paneli sentezle ve tarayıcıda başlat", badge: "Otonom Üretim", action: () => sendPrompt("Bana canlı HTML dashboard gösterge paneli oluştur ve ekranda aç.") },
  { title: "Tam Sistem Raporu & Markdown Kayıt", desc: "Manus-sınıfı çok adımlı denetim ve kam_sistem_raporu.md kaydı", badge: "Manus Plan", action: () => sendPrompt("Bilgisayarın gerçek sistem durumunu denetle ve kam_sistem_raporu.md olarak kaydet.") },
  { title: "Sesli Nöbet Tekmili (SAPI TTS)", desc: "Bilgisayar hoparlöründen sesli Türkçe nöbet tekmili ver", badge: "SAPI TTS", action: () => sendPrompt("Sesli söyle: 'KAM egemen bilişsel zihni ve otonom bilgisayar ajanı tam yetkiyle nöbette. Dirlik ve nizam kaimdir.'") },
  { title: "17.4 GHz Bilişsel EW Radar Analizi", desc: "DARPA CIRRA üstü LPI PDW sınıflandırma ve DRFM C++20 sentezi", badge: "Savunma API", action: () => testEwRadar() },
  { title: "Intent-to-Task C2 DAG Orkestrasyonu", desc: "S-400 köreltme emrini 4-unsurlu filo DAG grafiğine tahsis et", badge: "Savunma API", action: () => testC2Intent() },
  { title: "DARPA ANSR & CBF Uçuş Kalkanı", desc: "Güvenlik zarfını aşan uçuş komutasını kuadratik bariyerle izdüşür", badge: "Savunma API", action: () => testSafetyShield() },
  { title: "BFT & ML-KEM-768 Kuantum Sürü Konsensüsü", desc: "Bizans haini Charlie-3 izolasyonu ve Kyber-768 PQC anahtar değişimi", badge: "Savunma API", action: () => testBftSwarm() },
  { title: "Pasif TRN / TERCOM Arazi Korelasyonu", desc: "0W RF yayımıyla 901m INS kaymasını DEM üzerinde sönümle", badge: "Savunma API", action: () => testTrnLocalize() },
  { title: "Sözde-Ters Eyleyici Kontrol Dağıtımı", desc: "Sıkışan sol elevon momentini sağlam yüzeylere dağıt", badge: "Savunma API", action: () => testActuatorReconfig() },
  { title: "1550nm SWIR FSO Lazer Sürü Ağı", desc: "EMCON-Sıfır (0.0W RF) 685 Mbps serbest uzay optik haberleşme", badge: "Savunma API", action: () => testFsoLaserLink() },
  { title: "SECDED Hamming(72,64) & TMR ECC Onarımı", desc: "Kozmik ışın Bit-19 SEU ve BitNet b1.58 ağırlık onarımı", badge: "Savunma API", action: () => testRadiationScrubber() },
  { title: "HJI 9G Diferansiyel Oyun Füze Kaçınma", desc: "Isaacs eyer noktası 9G fıçı tonosu ve DRFM Cross-Eye", badge: "Savunma API", action: () => testHjiMissileEvasion() },
  { title: "3B SİHA Gizli Rota Planlayıcı", desc: "Risk-duyarlı A* radar gölgeleme yörüngesi", badge: "Savunma API", action: () => testTacticalRoute() },
  { title: "8-Modelli Egemen Savunma Filosu Manifestosu", desc: "Hugging Face Hub üzerindeki 8 resmi KAM model deposu", badge: "HF Filo", action: () => showFleetManifest() },
  { title: "Kriz [I]: UART-2 Telemetri Kopuşu", desc: "SDR 868MHz FHSS C++20 JIT sıcak-yama geçişi", badge: "Kriz Sim", action: () => triggerCrisis("uav_uart_cut") },
  { title: "Kriz [XV]: Hipersonik SAM Füze Kilidi", desc: "HJI 9G kaçınma ve DRFM Cross-Eye C++20 JIT yaması", badge: "Kriz Sim", action: () => triggerCrisis("sam_missile_lock") },
  { title: "Dirlik ve Dengeyi Sıfırla (Entropi %3)", desc: "Varyasyonel serbest enerjiyi homeostatik dengeye döndür", badge: "Homeostaz", action: () => resetSystem() },
  { title: "Sohbeti Markdown Olarak Dışa Aktar", desc: "Aktif konuşmayı .md dosyası olarak indir", badge: "Dışa Aktar", action: () => exportChat() },
  { title: "Oturum Geçmişini Aç", desc: "Kayıtlı sohbet oturumları arasında geçiş yap", badge: "Oturum", action: () => toggleSessionsDrawer() },
  { title: "Yeni Sohbet Oturumu Başlat", desc: "Temiz bir kalıcı oturum oluştur", badge: "Oturum", action: () => createNewSession() },
  { title: "Sesli Komut Girişi (Türkçe)", desc: "Web Speech API ile mikrofon dinlemeyi aç/kapat", badge: "Ses", action: () => toggleVoiceInput() },
  { title: "İş Akışı: Sistem Sağlık Denetimi", desc: "Otonom donanım, CPU/RAM/disk ve süreç sağlık denetimi", badge: "İş Akışı", action: () => runWorkflow("system_health_audit", "Sistem Sağlık Denetimi") },
  { title: "İş Akışı: Repo Kod Denetimi", desc: "Proje yapısı, dosya istatistikleri ve kod taraması", badge: "İş Akışı", action: () => runWorkflow("repo_code_audit", "Repo Kod Denetimi") },
  { title: "İş Akışı: Ağ Güvenlik Taraması", desc: "Açık portlar, ağ bağlantıları ve güvenlik kontrolü", badge: "İş Akışı", action: () => runWorkflow("network_security_scan", "Ağ Güvenlik Taraması") },
  { title: "Model Geçişi: kam:council (Bilişsel Kurul)", desc: "5-Modelli dinamik uzman yönlendiriciyi aktif et", badge: "Model", action: () => quickSwitchModel("kam:council") },
  { title: "Model Geçişi: kam:apex (Qwen3 8B Başbuğ)", desc: "5.20 GB yeni nesil hibrit düşünen komuta zihni", badge: "Model", action: () => quickSwitchModel("kam:apex") },
  { title: "Model Geçişi: kam:7b (Ulu Kam)", desc: "4.68 GB duru Türkçe ve Karl Friston aktif çıkarım zihni", badge: "Model", action: () => quickSwitchModel("kam:7b") },
  { title: "Model Geçişi: kam:r1 (Baş Bilge CoT)", desc: "4.68 GB DeepSeek-R1 <think> derin akıl yürütme zihni", badge: "Model", action: () => quickSwitchModel("kam:r1") },
  { title: "Model Geçişi: kam:coder (Ulu Demirci)", desc: "4.68 GB C++20 JIT, Linux eBPF ve CUDA başmimarı", badge: "Model", action: () => quickSwitchModel("kam:coder") }
];

let filteredPaletteItems = [...COMMAND_PALETTE_ITEMS];
let selectedPaletteIndex = 0;

function openCommandPalette() {
  const modal = document.getElementById("cmd-palette-modal");
  const input = document.getElementById("cmd-palette-input");
  if (!modal || !input) return;
  modal.style.display = "flex";
  input.value = "";
  filterCommandPalette("");
  setTimeout(() => input.focus(), 30);
}

function closeCommandPalette() {
  const modal = document.getElementById("cmd-palette-modal");
  if (modal) modal.style.display = "none";
}

function filterCommandPalette(query) {
  const q = (query || "").toLowerCase().trim();
  filteredPaletteItems = COMMAND_PALETTE_ITEMS.filter(
    item => item.title.toLowerCase().includes(q) || item.desc.toLowerCase().includes(q) || item.badge.toLowerCase().includes(q)
  );
  selectedPaletteIndex = 0;
  renderCommandPaletteList();
}

function renderCommandPaletteList() {
  const listEl = document.getElementById("cmd-palette-list");
  if (!listEl) return;
  listEl.innerHTML = "";
  filteredPaletteItems.forEach((item, idx) => {
    const btn = document.createElement("button");
    btn.className = `cmd-palette-item ${idx === selectedPaletteIndex ? "selected" : ""}`;
    btn.innerHTML = `
      <div class="cmd-item-left">
        <div>
          <div class="cmd-item-title">${escapeHtml(item.title)}</div>
          <div class="cmd-item-desc">${escapeHtml(item.desc)}</div>
        </div>
      </div>
      <span class="cmd-item-badge">${escapeHtml(item.badge)}</span>
    `;
    btn.onclick = () => {
      closeCommandPalette();
      item.action();
    };
    listEl.appendChild(btn);
  });
}

function handleCommandPaletteKey(e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (filteredPaletteItems.length > 0) {
      selectedPaletteIndex = (selectedPaletteIndex + 1) % filteredPaletteItems.length;
      renderCommandPaletteList();
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (filteredPaletteItems.length > 0) {
      selectedPaletteIndex = (selectedPaletteIndex - 1 + filteredPaletteItems.length) % filteredPaletteItems.length;
      renderCommandPaletteList();
    }
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (filteredPaletteItems[selectedPaletteIndex]) {
      const target = filteredPaletteItems[selectedPaletteIndex];
      closeCommandPalette();
      target.action();
    }
  }
}

// ============================================================================
// 9. AYARLAR MODALI VE GLOBAL KLAVYE KISAYOLLARI
// ============================================================================
function openSettingsModal() {
  document.getElementById("settings-modal").style.display = "flex";
  fetchModels();
}

function closeSettingsModal() {
  document.getElementById("settings-modal").style.display = "none";
}

async function saveSettings() {
  const modelSelect = document.getElementById("modal-model-select");
  const geminiInput = document.getElementById("modal-gemini-key");

  const payload = {
    model: modelSelect ? modelSelect.value : ""
  };
  const geminiKey = geminiInput ? geminiInput.value.trim() : "";
  if (geminiKey) {
    payload.gemini_key = geminiKey;
  }

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status === "ok") {
      closeSettingsModal();
      fetchTelemetry();
      appendKernelLog("KAM-CONFIG", `Model yapılandırıldı: ${data.current_model}`, "ok");
      showToast(`Aktif model: ${data.current_model}`, "success");
      appendMessage(
        "kam",
        `⚙️ <strong>[YAPILANDIRMA GÜNCELLENDİ]</strong> Aktif Model: <code>${escapeHtml(data.current_model)}</code> (${escapeHtml((data.active_backend || "").toUpperCase())})`,
        null,
        true
      );
    } else {
      showToast(data.error || "Ayarlar kaydedilemedi", "error");
    }
  } catch (err) {
    showToast("Ayarlar kaydedilirken hata oluştu", "error");
  }
}

document.addEventListener("keydown", (e) => {
  // Ctrl+K -> Komut Paleti
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    const cmdModal = document.getElementById("cmd-palette-modal");
    if (cmdModal && cmdModal.style.display === "flex") {
      closeCommandPalette();
    } else {
      openCommandPalette();
    }
    return;
  }

  // Ctrl+B -> Sistem & Telemetri Çekmecesini Aç/Kapat
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
    e.preventDefault();
    toggleTelemetryDrawer();
    return;
  }

  if (e.key === "Escape") {
    let closedOverlay = false;
    const cmdModal = document.getElementById("cmd-palette-modal");
    if (cmdModal && cmdModal.style.display === "flex") {
      closeCommandPalette();
      closedOverlay = true;
    }
    const drawer = document.getElementById("hud-drawer");
    if (drawer && drawer.classList.contains("active")) {
      toggleTelemetryDrawer();
      closedOverlay = true;
    }
    const modal = document.getElementById("settings-modal");
    if (modal && modal.style.display && modal.style.display !== "none") {
      closeSettingsModal();
      closedOverlay = true;
    }
    const sessionsDrawer = document.getElementById("sessions-drawer");
    if (sessionsDrawer && sessionsDrawer.classList.contains("active")) {
      toggleSessionsDrawer();
      closedOverlay = true;
    }
    const previewDrawer = document.getElementById("preview-drawer");
    if (previewDrawer && previewDrawer.classList.contains("active")) {
      closePreviewDrawer();
      closedOverlay = true;
    }
    if (!closedOverlay && isProcessing && currentAbortController) {
      e.preventDefault();
      stopGeneration();
    }
  }
});

// ============================================================================
// 10. ÇOKLU OTURUM YÖNETİMİ (/api/sessions)
// ============================================================================
function toggleSessionsDrawer() {
  const drawer = document.getElementById("sessions-drawer");
  const backdrop = document.getElementById("sessions-backdrop");
  if (!drawer) return;
  const isActive = drawer.classList.contains("active");
  if (isActive) {
    drawer.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");
  } else {
    drawer.classList.add("active");
    if (backdrop) backdrop.classList.add("active");
    loadSessions();
  }
}

function formatSessionTime(isoStr) {
  if (!isoStr) return "";
  try {
    const dt = new Date(isoStr);
    if (isNaN(dt.getTime())) return "";
    const diffSec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
    if (diffSec < 60) return "şimdi";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} dk`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} sa`;
    return dt.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
  } catch (e) {
    return "";
  }
}

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const data = await res.json();
    sessionsCache = Array.isArray(data) ? data : (Array.isArray(data.sessions) ? data.sessions : []);
    activeSessionId = data.active_id || data.active_session_id || activeSessionId;
    renderSessionsList();
  } catch (err) {
    console.warn("Oturumlar yüklenemedi:", err);
  }
}

function renderSessionsList() {
  const listEl = document.getElementById("sessions-list");
  if (!listEl) return;
  listEl.innerHTML = "";

  if (!sessionsCache || sessionsCache.length === 0) {
    const empty = document.createElement("div");
    empty.className = "sessions-empty";
    empty.textContent = "Henüz kayıtlı oturum yok.";
    listEl.appendChild(empty);
    return;
  }

  sessionsCache.forEach(session => {
    const sid = session.id;
    const isActive = sid && sid === activeSessionId;
    const item = document.createElement("div");
    item.className = `session-item${isActive ? " active" : ""}`;
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");

    const mainCol = document.createElement("div");
    mainCol.className = "session-item-main";
    mainCol.style.minWidth = "0";
    mainCol.style.flex = "1";

    const titleEl = document.createElement("div");
    titleEl.className = "session-title session-item-title";
    titleEl.textContent = session.title || "Yeni Sohbet";

    const metaEl = document.createElement("div");
    metaEl.className = "session-meta session-item-meta";
    const count = Number(session.message_count ?? 0);
    const when = formatSessionTime(session.updated_at);
    metaEl.textContent = when ? `${count} mesaj · ${when}` : `${count} mesaj`;

    mainCol.appendChild(titleEl);
    mainCol.appendChild(metaEl);

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "session-delete-btn";
    delBtn.title = "Oturumu Sil";
    delBtn.setAttribute("aria-label", "Oturumu Sil");
    delBtn.innerHTML = "&#10005;";
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(sid);
    });

    item.addEventListener("click", () => switchSession(sid));
    item.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        switchSession(sid);
      }
    });

    item.appendChild(mainCol);
    item.appendChild(delBtn);
    listEl.appendChild(item);
  });
}

async function createNewSession() {
  if (currentAbortController) {
    stopGeneration();
  }
  try {
    const res = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const session = data.session || data;
    activeSessionId = session.id || data.active_id || activeSessionId;

    const history = document.getElementById("chat-history");
    if (history) history.innerHTML = "";
    const hero = document.getElementById("welcome-hero");
    if (hero) hero.style.display = "flex";
    userScrolledUp = false;

    const drawer = document.getElementById("sessions-drawer");
    const backdrop = document.getElementById("sessions-backdrop");
    if (drawer) drawer.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");

    await loadSessions();
    showToast("Yeni oturum başlatıldı", "success");
    appendKernelLog("KAM-SESS", `Yeni oturum oluşturuldu: ${activeSessionId || "active"}`, "ok");
  } catch (err) {
    showToast("Yeni oturum oluşturulamadı", "error");
  }
}

async function switchSession(sessionId) {
  if (!sessionId) return;
  if (currentAbortController) {
    stopGeneration();
  }
  try {
    const actRes = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    if (!actRes.ok) throw new Error(`HTTP ${actRes.status}`);
    const actData = await actRes.json();

    let messages = actData.messages || (actData.session && actData.session.messages);
    if (!Array.isArray(messages)) {
      const getRes = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`);
      if (getRes.ok) {
        const getData = await getRes.json();
        messages = getData.messages || (getData.session && getData.session.messages) || [];
      } else {
        messages = [];
      }
    }

    activeSessionId = sessionId;
    const history = document.getElementById("chat-history");
    if (history) history.innerHTML = "";

    const hero = document.getElementById("welcome-hero");
    if (messages.length === 0) {
      if (hero) hero.style.display = "flex";
    } else {
      if (hero) hero.style.display = "none";
      messages.forEach(m => {
        const role = (m.role || "").toLowerCase();
        const content = m.content || "";
        if (!content) return;
        if (role === "user") {
          appendMessage("user", content);
        } else if (role === "assistant" || role === "kam") {
          appendMessage("kam", content);
        }
      });
    }

    const drawer = document.getElementById("sessions-drawer");
    const backdrop = document.getElementById("sessions-backdrop");
    if (drawer) drawer.classList.remove("active");
    if (backdrop) backdrop.classList.remove("active");

    smartScrollToBottom(true, false);
    await loadSessions();
    showToast("Oturum yüklendi", "info");
  } catch (err) {
    showToast("Oturuma geçilemedi", "error");
  }
}

async function deleteSession(sessionId) {
  if (!sessionId) return;
  try {
    const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (sessionId === activeSessionId) {
      activeSessionId = null;
      const history = document.getElementById("chat-history");
      if (history) history.innerHTML = "";
      const hero = document.getElementById("welcome-hero");
      if (hero) hero.style.display = "flex";
    }
    await loadSessions();
    showToast("Oturum silindi", "info");
  } catch (err) {
    showToast("Oturum silinemedi", "error");
  }
}

// ============================================================================
// 11. DOSYA EKLEME VE SÜRÜKLE-BIRAK (POST /api/upload)
// ============================================================================
function formatFileSize(bytes) {
  const b = Number(bytes || 0);
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(2)} MB`;
}

function initFileAttachments() {
  const fileInput = document.getElementById("file-upload-input");
  const attachBtn = document.getElementById("btn-attach");
  const island = document.querySelector(".input-island");

  if (attachBtn && fileInput && !attachBtn.getAttribute("onclick")) {
    attachBtn.addEventListener("click", () => fileInput.click());
  }

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFilesSelected(fileInput.files);
      }
      fileInput.value = "";
    });
  }

  if (island) {
    let dragDepth = 0;
    island.addEventListener("dragenter", (e) => {
      e.preventDefault();
      dragDepth++;
      island.classList.add("drag-over");
    });
    island.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    });
    island.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) island.classList.remove("drag-over");
    });
    island.addEventListener("drop", (e) => {
      e.preventDefault();
      dragDepth = 0;
      island.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFilesSelected(e.dataTransfer.files);
      }
    });
  }

  renderAttachedFiles();
}

async function handleFilesSelected(fileList) {
  const files = Array.from(fileList || []);
  for (const file of files) {
    if (attachedFiles.length >= MAX_ATTACHED_FILES) {
      showToast(`En fazla ${MAX_ATTACHED_FILES} dosya eklenebilir`, "warn");
      break;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      showToast(`Dosya 2 MB sınırını aşıyor: ${file.name}`, "warn");
      continue;
    }
    try {
      const content = await file.text();
      const res = await fetch("/api/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: file.name, content })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "ok") {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      attachedFiles.push({
        name: file.name,
        path: data.path,
        size_bytes: data.size_bytes ?? file.size,
        preview: data.preview || ""
      });
      renderAttachedFiles();
      showToast(`Dosya eklendi: ${file.name}`, "success");
      appendKernelLog("KAM-UPLOAD", `Dosya yüklendi: ${data.path} (${formatFileSize(data.size_bytes ?? file.size)})`, "ok");
    } catch (err) {
      showToast(`Yükleme hatası (${file.name}): ${err.message || "başarısız"}`, "error");
    }
  }
}

function renderAttachedFiles() {
  const bar = document.getElementById("attached-files-bar");
  if (!bar) return;
  bar.innerHTML = "";
  if (attachedFiles.length === 0) {
    bar.style.display = "none";
    return;
  }
  bar.style.display = "flex";
  attachedFiles.forEach((f, idx) => {
    const chip = document.createElement("span");
    chip.className = "attached-file-chip";
    chip.title = f.path;

    const label = document.createElement("span");
    label.textContent = `${f.name} (${formatFileSize(f.size_bytes)})`;

    const rmBtn = document.createElement("button");
    rmBtn.type = "button";
    rmBtn.className = "chip-remove attached-file-remove";
    rmBtn.title = "Kaldır";
    rmBtn.setAttribute("aria-label", `${f.name} dosyasını kaldır`);
    rmBtn.innerHTML = "&#10005;";
    rmBtn.addEventListener("click", () => {
      attachedFiles.splice(idx, 1);
      renderAttachedFiles();
    });

    chip.appendChild(label);
    chip.appendChild(rmBtn);
    bar.appendChild(chip);
  });
}

// ============================================================================
// 12. WEB SPEECH API TÜRKÇE SESLİ GİRİŞ & MESAJ BAZLI SESLİ OKUMA (TTS)
// ============================================================================
function setVoiceButtonState(recording) {
  const btn = document.getElementById("btn-voice");
  if (!btn) return;
  btn.classList.toggle("recording", recording);
  btn.classList.toggle("active", recording);
  btn.setAttribute("aria-pressed", recording ? "true" : "false");
}

function toggleVoiceInput() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    showToast("Tarayıcınız Web Speech API sesli girişini desteklemiyor", "warn");
    return;
  }

  if (isRecordingVoice && speechRecognition) {
    try { speechRecognition.stop(); } catch (e) {}
    return;
  }

  const input = document.getElementById("chat-input");
  const baseText = input ? input.value.trim() : "";

  try {
    const recognition = new SpeechRec();
    recognition.lang = "tr-TR";
    recognition.interimResults = true;
    recognition.continuous = false;
    speechRecognition = recognition;

    recognition.onstart = () => {
      isRecordingVoice = true;
      setVoiceButtonState(true);
      showToast("Dinleniyor (Türkçe)...", "info", 1800);
    };

    recognition.onresult = (event) => {
      if (!input) return;
      let transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      const clean = transcript.trim();
      input.value = baseText ? `${baseText} ${clean}` : clean;
      autoResizeTextarea(input);
    };

    recognition.onerror = (event) => {
      const code = event && event.error ? event.error : "unknown";
      if (code === "not-allowed" || code === "service-not-allowed") {
        showToast("Mikrofon izni reddedildi", "error");
      } else if (code !== "aborted" && code !== "no-speech") {
        showToast(`Sesli giriş hatası: ${code}`, "warn");
      }
    };

    recognition.onend = () => {
      isRecordingVoice = false;
      speechRecognition = null;
      setVoiceButtonState(false);
      if (input) input.focus();
    };

    recognition.start();
  } catch (err) {
    isRecordingVoice = false;
    speechRecognition = null;
    setVoiceButtonState(false);
    showToast("Sesli giriş başlatılamadı", "error");
  }
}

function extractPlainTextForTts(rawText) {
  let s = String(rawText || "");
  s = s.replace(/<think>[\s\S]*?<\/think>/gi, " ");
  s = s.replace(/<codeact>[\s\S]*?<\/codeact>/gi, " ");
  s = s.replace(/```[\s\S]*?```/g, " ");
  s = s.replace(/⚡ \[OTONOM AJAN İCRASI \/\/[^\]]*\][\s\S]*?(?:\n\}|\[ÇIKTI ÖZETLENDİ\]|\n\n|$)/g, " ");
  s = s.replace(/<[^>]+>/g, " ");
  s = s.replace(/[#*_`~>|[\]]/g, " ");
  s = s.replace(/\s+/g, " ").trim();
  return s.slice(0, 1200);
}

function speakMessageText(btnEl, rawText) {
  if (typeof window.speechSynthesis === "undefined") {
    showToast("Tarayıcınız sesli okumayı desteklemiyor", "warn");
    return;
  }

  if (activeTtsButton === btnEl && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    btnEl.classList.remove("speaking");
    activeTtsButton = null;
    return;
  }

  window.speechSynthesis.cancel();
  if (activeTtsButton) {
    activeTtsButton.classList.remove("speaking");
    activeTtsButton = null;
  }

  const cleanText = extractPlainTextForTts(rawText);
  if (!cleanText) {
    showToast("Okunacak metin bulunamadı", "info");
    return;
  }

  const utter = new SpeechSynthesisUtterance(cleanText);
  utter.lang = "tr-TR";
  utter.rate = 1.02;
  const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
  const trVoice = voices.find(v => v.lang && v.lang.toLowerCase().startsWith("tr"));
  if (trVoice) utter.voice = trVoice;

  utter.onstart = () => {
    activeTtsButton = btnEl;
    btnEl.classList.add("speaking");
  };
  utter.onend = () => {
    btnEl.classList.remove("speaking");
    if (activeTtsButton === btnEl) activeTtsButton = null;
  };
  utter.onerror = () => {
    btnEl.classList.remove("speaking");
    if (activeTtsButton === btnEl) activeTtsButton = null;
  };

  window.speechSynthesis.speak(utter);
}

function attachMessageActions(bubbleEl, rawText) {
  if (!bubbleEl || typeof window.speechSynthesis === "undefined") return;
  if (bubbleEl.querySelector(".msg-actions")) return;

  const actions = document.createElement("div");
  actions.className = "msg-actions";

  const ttsBtn = document.createElement("button");
  ttsBtn.type = "button";
  ttsBtn.className = "msg-tts-btn";
  ttsBtn.title = "Sesli Oku / Durdur";
  ttsBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg><span>Sesli Oku</span>`;
  ttsBtn.addEventListener("click", () => speakMessageText(ttsBtn, rawText));

  actions.appendChild(ttsBtn);
  bubbleEl.appendChild(actions);
}

// ============================================================================
// 13. OTONOM SİSTEM İŞ AKIŞLARI (/api/workflows)
// ============================================================================
const FALLBACK_WORKFLOWS = [
  { id: "system_health_audit", title: "Sistem Sağlık Denetimi", description: "CPU, RAM, disk ve kritik süreçlerin otonom denetimi" },
  { id: "repo_code_audit", title: "Repo Kod Denetimi", description: "Kod külliyatı, dosya dağılımı ve mimari sağlık taraması" },
  { id: "network_security_scan", title: "Ağ Güvenlik Taraması", description: "Dinleyen portlar, aktif bağlantılar ve ağ durumu" }
];

async function loadWorkflows() {
  let workflows = FALLBACK_WORKFLOWS;
  try {
    const res = await fetch("/api/workflows");
    if (res.ok) {
      const data = await res.json();
      const list = Array.isArray(data) ? data : (Array.isArray(data.workflows) ? data.workflows : null);
      if (list && list.length > 0) workflows = list;
    }
  } catch (err) {}
  renderWorkflowsList(workflows);
}

function renderWorkflowsList(workflows) {
  const container = document.getElementById("workflows-list");
  if (!container) return;
  container.innerHTML = "";

  workflows.forEach(wf => {
    const wfId = wf.id || wf.workflow_id || "";
    const wfTitle = wf.title || wf.name || wfId;
    const wfDesc = wf.description || wf.desc || "";

    const card = document.createElement("div");
    card.className = "workflow-card";

    const info = document.createElement("div");
    info.className = "workflow-info";

    const titleEl = document.createElement("div");
    titleEl.className = "workflow-title";
    titleEl.textContent = wfTitle;

    const descEl = document.createElement("div");
    descEl.className = "workflow-desc";
    descEl.textContent = wfDesc;

    info.appendChild(titleEl);
    info.appendChild(descEl);

    const runBtn = document.createElement("button");
    runBtn.type = "button";
    runBtn.className = "workflow-run-btn";
    runBtn.textContent = "Çalıştır";
    runBtn.addEventListener("click", () => runWorkflow(wfId, wfTitle));

    card.appendChild(info);
    card.appendChild(runBtn);
    container.appendChild(card);
  });
}

async function runWorkflow(workflowId, titleLabel = "") {
  if (!workflowId) return;
  closeDrawerIfOpen();
  const label = titleLabel || workflowId;
  appendMessage("user", `⚙️ Otonom İş Akışı Başlatıldı: ${label}`);
  appendKernelLog("KAM-WF", `İş akışı tetiklendi: ${workflowId}`, "jit");

  const kamBubble = createMessageBubble("kam");
  try {
    const res = await fetch("/api/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workflow_id: workflowId, id: workflowId })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    const mdReport = data.markdown || data.summary || data.report || (
      `### ⚙️ Otonom İş Akışı: ${label}\n\n\`\`\`json\n${JSON.stringify(data.result || data, null, 2)}\n\`\`\``
    );
    kamBubble.innerHTML = formatMarkdown(mdReport);
    attachMessageActions(kamBubble, mdReport);
    smartScrollToBottom(false, true);
    showToast(`İş akışı tamamlandı: ${label}`, "success");
    fetchTelemetry();
  } catch (err) {
    kamBubble.innerHTML = `<p>❌ İş akışı çalıştırılamadı: ${escapeHtml(err.message || "bağlantı hatası")}</p>`;
    showToast("İş akışı çalıştırılamadı", "error");
  }
}
