const CATEGORY_TAGS = {
  normal: { label: "Chuyến đi", class: "tag-normal" },
  edge: { label: "Ngân sách", class: "tag-edge" },
  clarification: { label: "Làm rõ", class: "tag-clarification" },
  guardrail: { label: "An toàn", class: "tag-guardrail" },
};

const $ = (sel) => document.querySelector(sel);
const messagesEl = $("#messages");
const queryEl = $("#query");
const formEl = $("#chat-form");
const toolDetailsEl = $("#tool-details");
const statusPill = $("#status-pill");
const sendBtn = $("#send-btn");
const spinner = $("#spinner");
const todayEl = $("#today");

function setLoading(on) {
  sendBtn.disabled = on;
  spinner.classList.toggle("hidden", !on);
}

function appendMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `bubble bubble-${role}`;
  const meta = document.createElement("div");
  meta.className = "bubble-meta";
  meta.textContent = role === "user" ? "Bạn" : "TravelBuddy";
  const body = document.createElement("div");
  body.textContent = text;
  wrap.append(meta, body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function resetPipeline() {
  document.querySelectorAll(".pipe-step").forEach((el) => {
    el.classList.remove("active", "done");
  });
}

function highlightPipeline(toolCalls) {
  resetPipeline();
  const order = ["search_flights", "calculate_budget", "search_hotels"];
  toolCalls.forEach((call, i) => {
    const step = document.querySelector(`.pipe-step[data-tool="${call.name}"]`);
    if (step) {
      step.classList.add("done");
      if (i === toolCalls.length - 1) step.classList.add("active");
    }
  });
  if (!toolCalls.length) return;
  order.forEach((name) => {
    const step = document.querySelector(`.pipe-step[data-tool="${name}"]`);
    const used = toolCalls.some((c) => c.name === name);
    if (step && used && !step.classList.contains("active")) {
      step.classList.add("done");
    }
  });
}

function renderToolDetails(toolCalls) {
  if (!toolCalls.length) {
    toolDetailsEl.innerHTML =
      '<p class="muted">Không gọi tool — làm rõ thông tin, từ chối guardrail, hoặc ngoài phạm vi dữ liệu.</p>';
    return;
  }
  toolDetailsEl.innerHTML = "";
  toolCalls.forEach((call, index) => {
    const card = document.createElement("details");
    card.className = "tool-card";
    card.open = index === 0;
    let outputPretty = call.output;
    try {
      outputPretty = JSON.stringify(JSON.parse(call.output), null, 2);
    } catch {
      /* keep raw */
    }
    card.innerHTML = `
      <summary>${index + 1}. ${call.name}</summary>
      <div class="body">
        <strong>Tham số</strong>
        <pre>${escapeHtml(JSON.stringify(call.args, null, 2))}</pre>
        <strong>Kết quả</strong>
        <pre>${escapeHtml(outputPretty)}</pre>
      </div>
    `;
    toolDetailsEl.appendChild(card);
  });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function loadExamples() {
  const res = await fetch("/api/examples");
  const examples = await res.json();
  const list = $("#example-list");
  list.innerHTML = "";
  examples.forEach((ex) => {
    const tag = CATEGORY_TAGS[ex.category] || { label: ex.category, class: "tag-normal" };
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "example-btn";
    btn.innerHTML = `<span class="tag ${tag.class}">${tag.label}</span><br>${escapeHtml(ex.label)}`;
    btn.addEventListener("click", () => {
      queryEl.value = ex.query;
      queryEl.focus();
    });
    list.appendChild(btn);
  });
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const ok = data.credentials?.openai || data.credentials?.google;
    statusPill.textContent = ok ? `Sẵn sàng · ${data.default_provider}` : "Thiếu API key";
    statusPill.className = ok ? "pill pill-ok" : "pill pill-muted";
  } catch {
    statusPill.textContent = "Không kết nối server";
    statusPill.className = "pill pill-muted";
  }
}

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = queryEl.value.trim();
  if (!query) return;

  appendMessage("user", query);
  queryEl.value = "";
  setLoading(true);
  resetPipeline();
  toolDetailsEl.innerHTML = '<p class="muted">Đang xử lý…</p>';

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({
        query,
        today: todayEl.value || "2026-05-31",
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Lỗi không xác định");
    }
    appendMessage("bot", data.final_answer);
    highlightPipeline(data.tool_calls);
    renderToolDetails(data.tool_calls);
  } catch (err) {
    const banner = document.createElement("div");
    banner.className = "error-banner";
    banner.textContent = err.message || String(err);
    messagesEl.appendChild(banner);
    toolDetailsEl.innerHTML = '<p class="muted">Có lỗi khi gọi agent.</p>';
  } finally {
    setLoading(false);
  }
});

$("#clear-btn").addEventListener("click", () => {
  messagesEl.innerHTML = "";
  resetPipeline();
  toolDetailsEl.innerHTML = '<p class="muted">Gửi câu hỏi để xem chi tiết từng bước.</p>';
});

loadExamples();
checkHealth();
