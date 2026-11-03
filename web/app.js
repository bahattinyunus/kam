// KAM Bilişsel Kontrol Merkezi Web İstemcisi

let isProcessing = false;

// Basit Markdown Dönüştürücü (Gemini / ChatGPT çıktıları için)
function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Kod Blokları ```lang\ncode\n```
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre class="code-snippet"><code>${code.trim()}</code></pre>`;
  });

  // Inline Kod `kod`
  html = html.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 5px; border-radius: 4px; color: var(--cyan-glow);">$1</code>');

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

async function fetchTelemetry() {
  try {
    const res = await fetch("/api/telemetry");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("val-entropy").innerText = `%${Math.round(data.entropy * 100)}`;
    const barEntropy = document.getElementById("bar-entropy");
    barEntropy.style.width = `${Math.min(100, Math.round(data.entropy * 100))}%`;
    if (data.entropy >= 0.8) {
      barEntropy.style.background = "var(--crimson-glow)";
    } else if (data.entropy >= 0.4) {
      barEntropy.style.background = "var(--amber-glow)";
    } else {
      barEntropy.style.background = "var(--emerald-glow)";
    }

    document.getElementById("val-free-energy").innerText = `${data.free_energy.toFixed(3)} nats`;
    document.getElementById("bar-free-energy").style.width = `${Math.min(100, Math.round(data.free_energy * 50))}%`;

    document.getElementById("val-npu-temp").innerText = `${data.npu_temp.toFixed(1)}°C`;
    document.getElementById("val-active-channel").innerText = data.active_telemetry;

    // Aktif Model Bilgisi
    if (data.active_model) {
      const backendLabel = data.backend === "gemini" ? "Gemini Bulut" : (data.backend === "ollama" ? "Ollama Yerel" : "Dahili");
      document.getElementById("active-model-text").innerText = `${data.active_model} (${backendLabel})`;
    }

    // Durum Hapı
    const statusText = document.getElementById("system-status-text");
    if (data.chaos_detected) {
      statusText.innerText = "KRİTİK KAOS TESPİT EDİLDİ";
      statusText.parentElement.style.color = "var(--crimson-glow)";
      statusText.parentElement.style.borderColor = "var(--crimson-glow)";
    } else {
      statusText.innerText = "BİLİŞSEL DENGE AKTİF";
      statusText.parentElement.style.color = "var(--emerald-glow)";
      statusText.parentElement.style.borderColor = "rgba(16, 185, 129, 0.4)";
    }

    // Düğüm durumları
    const tagUart = document.getElementById("tag-uart");
    const tagSdr = document.getElementById("tag-sdr");
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
    if (data.models && data.models.length > 0) {
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
      const backendLabel = data.active_backend === "gemini" ? "Gemini Bulut" : (data.active_backend === "ollama" ? "Ollama Yerel" : "Dahili");
      document.getElementById("active-model-text").innerText = `${data.current_model} (${backendLabel})`;
    }
  } catch (err) {
    console.warn("Modeller çekilemedi:", err);
  }
}

// 2 saniyede bir telemetri güncelle
setInterval(fetchTelemetry, 2000);
fetchTelemetry();
fetchModels();

function handleKeyPress(e) {
  if (e.key === "Enter") {
    submitMessage();
  }
}

function sendPrompt(text) {
  document.getElementById("chat-input").value = text;
  submitMessage();
}

function showTypingIndicator() {
  const history = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-message kam typing-temp";
  msgDiv.id = "typing-indicator-msg";

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar avatar-kam";
  avatar.innerText = "🐺";

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble bubble-kam";
  bubble.innerHTML = `KAM düşünüyor <span class="typing-dots"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>`;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  history.appendChild(msgDiv);
  history.scrollTop = history.scrollHeight;
}

function hideTypingIndicator() {
  const el = document.getElementById("typing-indicator-msg");
  if (el) el.remove();
}

function createMessageBubble(sender) {
  const history = document.getElementById("chat-history");
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${sender}`;

  const avatar = document.createElement("div");
  avatar.className = `chat-avatar avatar-${sender === "user" ? "user" : "kam"}`;
  avatar.innerText = sender === "user" ? "👤" : "🐺";

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble bubble-${sender === "user" ? "user" : "kam"}`;
  bubble.innerHTML = `<span class="typing-dots"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>`;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  history.appendChild(msgDiv);
  history.scrollTop = history.scrollHeight;
  return bubble;
}

function appendMessage(sender, text, codeSnippet = null) {
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

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  history.appendChild(msgDiv);
  history.scrollTop = history.scrollHeight;
}

async function submitMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text || isProcessing) return;

  appendMessage("user", text);
  input.value = "";
  isProcessing = true;

  const kamBubble = createMessageBubble("kam");
  let accumulatedText = "";

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

    while (true) {
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
            if (data.done) break;
            if (data.token) {
              accumulatedText += data.token;
              kamBubble.innerHTML = formatMarkdown(accumulatedText);
              const history = document.getElementById("chat-history");
              history.scrollTop = history.scrollHeight;
            }
          } catch (e) {}
        }
      }
    }

    if (!accumulatedText.trim()) {
      kamBubble.innerHTML = "KAM Zihni aktif. Sistem telemetrisi ve bilişsel nöronlar dengede.";
    }
  } catch (err) {
    if (!accumulatedText) {
      kamBubble.innerHTML = "Bağlantı hatası: KAM çekirdeğine ulaşılamadı.";
    }
  } finally {
    isProcessing = false;
    fetchTelemetry();
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

    appendMessage("kam", `⚠️ <strong>[KRİZ TETİKLENDİ]</strong> ${data.message}`, data.code || null);
    fetchTelemetry();
  } catch (err) {
    alert("Kriz tetiklenirken hata oluştu!");
  }
}

async function resetSystem() {
  try {
    await fetch("/api/reset", { method: "POST" });
    appendMessage("kam", "🛡️ <strong>[SİSTEM SIFIRLANDI]</strong> Aktif çıkarım dengelendi, entropi %3 seviyesine çekildi.");
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
