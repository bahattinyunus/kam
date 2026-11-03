// KAM Bilişsel Kontrol Merkezi Web İstemcisi

let isProcessing = false;

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

// 2 saniyede bir telemetri güncelle
setInterval(fetchTelemetry, 2000);
fetchTelemetry();

function handleKeyPress(e) {
  if (e.key === "Enter") {
    submitMessage();
  }
}

function sendPrompt(text) {
  document.getElementById("chat-input").value = text;
  submitMessage();
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
  bubble.innerHTML = text.replace(/\n/g, "<br>");

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

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();

    appendMessage("kam", data.reply, data.code || null);
    fetchTelemetry();
  } catch (err) {
    appendMessage("kam", "Bağlantı hatası: KAM çekirdeğine ulaşılamadı.");
  } finally {
    isProcessing = false;
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
