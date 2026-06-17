const API_BASE = window.location.origin;
const STORAGE_KEY = "day12_agent_config";

const els = {
  apiKey: document.getElementById("apiKey"),
  userId: document.getElementById("userId"),
  saveConfig: document.getElementById("saveConfig"),
  testKey: document.getElementById("testKey"),
  messages: document.getElementById("messages"),
  welcome: document.getElementById("welcome"),
  typing: document.getElementById("typing"),
  input: document.getElementById("questionInput"),
  send: document.getElementById("sendBtn"),
  chips: document.querySelectorAll(".chip"),
  pillHealth: document.getElementById("pillHealth"),
  pillRedis: document.getElementById("pillRedis"),
  pillModel: document.getElementById("pillModel"),
  toast: document.getElementById("toast"),
};

function loadConfig() {
  try {
    const cfg = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    if (cfg.apiKey) els.apiKey.value = cfg.apiKey;
    if (cfg.userId) els.userId.value = cfg.userId;
    else els.userId.value = "demo-user";
  } catch {
    els.userId.value = "demo-user";
  }
}

function saveConfig() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      apiKey: els.apiKey.value.trim(),
      userId: els.userId.value.trim() || "demo-user",
    }),
  );
  showToast("Settings saved locally", false);
  refreshStatus();
}

function getConfig() {
  return {
    apiKey: els.apiKey.value.trim(),
    userId: els.userId.value.trim() || "demo-user",
  };
}

function showToast(msg, isError = true) {
  els.toast.textContent = msg;
  els.toast.style.borderColor = isError ? "var(--danger)" : "var(--accent-dim)";
  els.toast.style.color = isError ? "var(--danger)" : "var(--accent)";
  els.toast.classList.add("show");
  setTimeout(() => els.toast.classList.remove("show"), 4000);
}

function setPill(el, text, state) {
  el.textContent = text;
  el.className = "pill " + (state || "");
}

async function refreshStatus() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    setPill(els.pillHealth, `Health: ${data.status}`, data.status === "ok" ? "ok" : "warn");
    const redis = data.checks?.redis;
    const redisSet = data.checks?.redis_url_set;
    const redisLabel =
      redis === true ? "Redis: connected" :
      redis === false && redisSet ? "Redis: bad REDIS_URL" :
      redis === false ? "Redis: offline" :
      "Redis: not configured";
    setPill(els.pillRedis, redisLabel, redis === true ? "ok" : redisSet ? "err" : "warn");
    const useMock = data.checks?.use_mock_llm;
    const openaiOk = data.checks?.openai_configured;
    let llmLabel = data.checks?.llm || "mock";
    if (useMock) llmLabel = "mock — set USE_MOCK_LLM=false on Render";
    else if (openaiOk) llmLabel = "openai ready";
    else llmLabel = "mock (no valid OPENAI_API_KEY)";
    setPill(els.pillModel, `LLM: ${llmLabel}`, useMock || !openaiOk ? "warn" : "ok");
  } catch {
    setPill(els.pillHealth, "Health: unreachable", "err");
  }
}

function appendMessage(role, text, meta = "") {
  els.welcome.style.display = "none";
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  wrap.innerHTML = `
    <span class="role">${role === "user" ? "You" : "Agent"}</span>
    <div class="bubble">${escapeHtml(text)}</div>
    ${meta ? `<span class="meta">${escapeHtml(meta)}</span>` : ""}
  `;
  els.messages.appendChild(wrap);
  els.messages.scrollTop = els.messages.scrollHeight;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function setLoading(on) {
  els.send.disabled = on;
  els.input.disabled = on;
  els.typing.classList.toggle("show", on);
  if (on) els.messages.scrollTop = els.messages.scrollHeight;
}

async function sendMessage(question) {
  const q = (question || els.input.value).trim();
  if (!q) return;

  const { apiKey, userId } = getConfig();
  if (!apiKey) {
    showToast("Enter your AGENT_API_KEY in settings above");
    els.apiKey.focus();
    return;
  }

  els.input.value = "";
  appendMessage("user", q);
  setLoading(true);

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({ user_id: userId, question: q }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const detail = typeof data.detail === "object"
        ? JSON.stringify(data.detail)
        : (data.detail || res.statusText);
      if (res.status === 401) {
        throw new Error("401: Invalid API key — copy AGENT_API_KEY from Render Environment (not OPENAI_API_KEY)");
      }
      if (res.status === 502) {
        throw new Error("502: Server/LLM error — set USE_MOCK_LLM=true on Render, or fix OPENAI_API_KEY");
      }
      if (res.status === 429) {
        throw new Error("429: Rate limit exceeded — wait 1 minute");
      }
      throw new Error(`${res.status}: ${detail}`);
    }

    const meta = `turn ${data.turn} · ${data.model} · ${data.storage} · ${data.served_by}`;
    appendMessage("assistant", data.answer, meta);
  } catch (err) {
    appendMessage("assistant", `Error: ${err.message}`, "check API key and try again");
    showToast(err.message);
  } finally {
    setLoading(false);
    els.input.focus();
  }
}

async function testApiKey() {
  const { apiKey } = getConfig();
  if (!apiKey) {
    showToast("Enter API key first");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/verify`, {
      headers: { "X-API-Key": apiKey },
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast("API key is valid", false);
    } else {
      showToast(data.detail || `Key rejected (${res.status})`);
    }
  } catch (err) {
    showToast(err.message);
  }
}

els.saveConfig.addEventListener("click", saveConfig);
els.testKey.addEventListener("click", testApiKey);
els.send.addEventListener("click", () => sendMessage());
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
els.chips.forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.dataset.q));
});

loadConfig();
refreshStatus();
setInterval(refreshStatus, 30000);
