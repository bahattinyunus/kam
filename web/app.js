// KAM Bilişsel Kontrol Merkezi Web İstemcisi
// Siber-Şamanik ve İkonik Arayüz Motoru (v2.5 R1)

let isProcessing = false;

// Basit Markdown Dönüştürücü (Gemini / DeepSeek-R1 / ChatGPT çıktıları için)
function formatMarkdown(text) {
  if (!text) return "";

  // Düşünce Zinciri (<think>...</think>) - DeepSeek-R1
  let thoughtHtml = "";
  let mainText = text;

  if (mainText.includes("<think>")) {
    if (mainText.includes("</think>")) {
      mainText = mainText.replace(/<think>([\s\S]*?)<\/think>/gi, (match, thought) => {
        return `<details class="thought-process" open>
          <summary class="thought-summary">🧠 Düşünce Süreci (DeepSeek-R1 Akıl Yürütme)</summary>
          <div class="thought-content">${thought.trim().replace(/\n/g, '<br>')}</div>
        </details>`;
      });
    } else {
      mainText = mainText.replace(/<think>([\s\S]*)$/gi, (match, thought) => {
        return `<details class="thought-process" open>
          <summary class="thought-summary">🧠 Düşünce Süreci (Düşünüyor...)</summary>
          <div class="thought-content">${thought.trim().replace(/\n/g, '<br>')} <span class="typing-dots"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span></div>
        </details>`;
      });
    }
  }

  let html = mainText;

  // Kod Blokları ```lang\ncode\n```
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre class="code-snippet"><code>${code.trim()}</code></pre>`;
  });

  // Inline Kod `kod`
  html = html.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; color: var(--cyan-glow); font-family: var(--font-mono);">$1</code>');

  // Başlıklar
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Kalın ve İtalik
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Madde İşaretleri (- veya * ile başlayanlar)
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, ''); // ardışık ul'leri birleştir

  // Satır sonları
  html = html.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

  return html;
}

// Telemetri Verisini Çek
async function fetchTelemetry() {
  try {
    const res = await fetch("/api/telemetry");
    if (!res.ok) return;
    const data = await res.json();

    const entropyStr = `%${Math.round(data.entropy * 100)}`;
    const elValEntropy = document.getElementById("val-entropy");
    if (elValEntropy) elValEntropy.innerText = entropyStr;

    const elDrawerEntropy = document.getElementById("drawer-val-entropy");
    if (elDrawerEntropy) elDrawerEntropy.innerText = entropyStr;

    const barEntropy = document.getElementById("bar-entropy");
    if (barEntropy) {
      barEntropy.style.width = `${Math.min(100, Math.round(data.entropy * 100))}%`;
      if (data.entropy >= 0.8) {
        barEntropy.style.background = "var(--crimson-glow)";
      } else if (data.entropy >= 0.4) {
        barEntropy.style.background = "var(--amber-glow)";
      } else {
        barEntropy.style.background = "var(--emerald-glow)";
      }
    }

    const elFreeEnergy = document.getElementById("val-free-energy");
    if (elFreeEnergy) elFreeEnergy.innerText = `${data.free_energy.toFixed(3)} nats`;

    const barFreeEnergy = document.getElementById("bar-free-energy");
    if (barFreeEnergy) barFreeEnergy.style.width = `${Math.min(100, Math.round(data.free_energy * 50))}%`;

    const elNpuTemp = document.getElementById("val-npu-temp");
    if (elNpuTemp) elNpuTemp.innerText = `${data.npu_temp.toFixed(1)}°C`;

    const barNpuTemp = document.getElementById("bar-npu-temp");
    if (barNpuTemp) barNpuTemp.style.width = `${Math.min(100, Math.round(data.npu_temp))}%`;

    const elChannel = document.getElementById("val-active-channel");
    if (elChannel) elChannel.innerText = data.active_telemetry;

    // Aktif Model Etiketleri
    if (data.active_model) {
      const shortModel = data.active_model.split(":")[0];
      const elModelText = document.getElementById("active-model-text");
      if (elModelText) elModelText.innerText = data.active_model;

      const elIslandModel = document.getElementById("island-model-label");
      if (elIslandModel) elIslandModel.innerText = data.active_model;
    }

    // Durum Hapı
    const statusText = document.getElementById("system-status-text");
    const statusPill = document.getElementById("status-pill");
    if (statusText && statusPill) {
      if (data.chaos_detected) {
        statusText.innerText = "KAOS & ENJİYON";
        statusPill.style.color = "var(--crimson-glow)";
        statusPill.style.borderColor = "var(--crimson-glow)";
        statusPill.style.background = "rgba(244, 63, 94, 0.15)";
      } else {
        statusText.innerText = "DİRLİK & DENGE";
        statusPill.style.color = "var(--emerald-glow)";
        statusPill.style.borderColor = "rgba(16, 185, 129, 0.25)";
        statusPill.style.background = "rgba(16, 185, 129, 0.1)";
      }
    }

    // Düğüm durumları
    const tagUart = document.getElementById("tag-uart");
    const tagSdr = document.getElementById("tag-sdr");
    if (tagUart && tagSdr) {
      if (data.active_telemetry.includes("SDR")) {
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
  }
}

// Model Listesini Getir
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

// 2 saniyede bir telemetri güncelle
setInterval(fetchTelemetry, 2000);
fetchTelemetry();
fetchModels();

// Klavye ve Textarea İşleyicileri
function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
}

function autoResizeTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 180) + "px";
}

function sendPrompt(text) {
  const input = document.getElementById("chat-input");
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
  avatar.innerText = sender === "user" ? "👤" : "🐺";

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
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  return bubble;
}

function appendMessage(sender, text, codeSnippet = null) {
  hideWelcomeHero();
  const history = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = `chat-avatar avatar-${sender === "user" ? "user" : "kam"}`;
  avatar.innerText = sender === "user" ? "👤" : "🐺";

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${sender === "user" ? "user" : "kam"}`;
  bubble.innerHTML = sender === "kam" ? formatMarkdown(text) : text.replace(/\n/g, "<br>");

  if (codeSnippet) {
    const codePre = document.createElement("pre");
    codePre.className = "code-snippet";
    codePre.innerText = codeSnippet;
    bubble.appendChild(codePre);
  }

  if (sender === "user") {
    msgDiv.appendChild(bubble);
    msgDiv.appendChild(avatar);
  } else {
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
  }

  history.appendChild(msgDiv);
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

async function submitMessage() {
  const input = document.getElementById("chat-input");
  const sendBtn = document.querySelector(".btn-send");
  const text = input.value.trim();
  if (!text || isProcessing) return;

  appendMessage("user", text);
  input.value = "";
  input.style.height = "auto";
  input.disabled = true;
  if (sendBtn) sendBtn.disabled = true;
  isProcessing = true;

  const kamBubble = createMessageBubble("kam");
  let accumulatedText = "";

  // Güvenlik: Eğer akış 35 saniyede bitmezse kilidi mutlaka aç
  const safetyTimer = setTimeout(() => {
    if (isProcessing) {
      console.warn("Yayın zaman aşımına uğradı, kilit sıfırlanıyor.");
      isProcessing = false;
      input.disabled = false;
      if (sendBtn) sendBtn.disabled = false;
      input.focus();
    }
  }, 35000);

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let streamDone = false;

    while (!streamDone) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop(); // Son bitmemiş satırı tamponda tut

      for (const chunk of chunks) {
        if (chunk.startsWith("data: ")) {
          const jsonStr = chunk.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const data = JSON.parse(jsonStr);
            if (data.done) {
              streamDone = true;
              try { await reader.cancel(); } catch (e) {}
              break;
            }
            if (data.token) {
              accumulatedText += data.token;
              kamBubble.innerHTML = formatMarkdown(accumulatedText);
              window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
            }
          } catch (e) {}
        }
      }
    }

    if (!accumulatedText.trim()) {
      kamBubble.innerHTML = "KAM Zihni aktif. Sistem telemetrisi ve bilişsel nöronlar dengede.";
    }
  } catch (err) {
    console.error("Sohbet hatası:", err);
    if (!accumulatedText) {
      kamBubble.innerHTML = "Bağlantı hatası: KAM çekirdeğine ulaşılamadı.";
    }
  } finally {
    clearTimeout(safetyTimer);
    isProcessing = false;
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
    fetchTelemetry();
  }
}

async function clearChat() {
  try {
    await fetch("/api/clear_chat", { method: "POST" });
  } catch (e) {}

  const history = document.getElementById("chat-history");
  history.innerHTML = "";
  const hero = document.getElementById("welcome-hero");
  if (hero) hero.style.display = "flex";
}

// Slide-Over HUD Drawer Aç/Kapat
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
    const res = await fetch("/api/crisis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crisis_type: type })
    });
    const data = await res.json();

    appendMessage("kam", `⚡ <strong>[KAOS TETİKLENDİ // AYİN BAŞLADI]</strong> ${data.message}`, data.code || null);
    fetchTelemetry();
  } catch (err) {
    alert("Kriz tetiklenirken hata oluştu!");
  }
}

async function resetSystem() {
  try {
    await fetch("/api/reset", { method: "POST" });
    appendMessage("kam", "🛡️ <strong>[DİRLİK VE DENGE YENİDEN KURULDU]</strong> Gök çökmedi, yer yarılmadı. Bilişsel denge sağlandı, varyasyonel serbest enerji %3 seviyesine çekildi.");
    fetchTelemetry();
  } catch (err) {
    alert("Sıfırlama başarısız.");
  }
}

// Modal Kontrolleri
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
    model: modelSelect.value,
    gemini_key: geminiInput.value.trim()
  };

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "ok") {
      closeSettingsModal();
      fetchTelemetry();
      appendMessage("kam", `⚙️ <strong>[YAPILANDIRMA GÜNCELLENDİ]</strong> Aktif Model: <code>${data.current_model}</code> (${data.active_backend.toUpperCase()})`);
    }
  } catch (err) {
    alert("Ayarlar kaydedilirken hata oluştu!");
  }
}

// Global Kısayollar (Esc ile çekmeceyi/modali kapat)
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const drawer = document.getElementById("hud-drawer");
    if (drawer && drawer.classList.contains("active")) {
      toggleTelemetryDrawer();
    }
    const modal = document.getElementById("settings-modal");
    if (modal && modal.style.display !== "none") {
      closeSettingsModal();
    }
  }
});