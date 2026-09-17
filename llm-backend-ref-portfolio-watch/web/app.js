/* Phase 4–5 — fetch thật + render UI; lỗi hiện rõ, không im lặng. */
const API_BASE = "";
const NETWORK_ERROR_MSG = "Không lấy được dữ liệu, thử lại";

async function apiFetch(path, options = {}) {
  const method = options.method || "GET";
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }
    return { ok: res.ok, status: res.status, text, data };
  } catch (err) {
    console.error("[api]", method, path, err);
    return { ok: false, status: 0, text: String(err), data: null };
  }
}

function scanSymbol(symbol) {
  return apiFetch("/scan", {
    method: "POST",
    body: JSON.stringify({ symbol }),
  });
}

function sendChat(question) {
  return apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

function getApprovals() {
  return apiFetch("/approvals");
}

function approveAlert(id) {
  return apiFetch(`/approvals/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    body: "{}",
  });
}

function rejectAlert(id, reason) {
  return apiFetch(`/approvals/${encodeURIComponent(id)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || "" }),
  });
}

function getWatchlist() {
  return apiFetch("/watchlist");
}

function addWatchlistItem(symbol, threshold_pct) {
  return apiFetch("/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol, threshold_pct }),
  });
}

function updateWatchlistItem(symbol, threshold_pct) {
  return apiFetch(`/watchlist/${encodeURIComponent(symbol)}`, {
    method: "PATCH",
    body: JSON.stringify({ threshold_pct }),
  });
}

function deleteWatchlistItem(symbol) {
  return apiFetch(`/watchlist/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function showAppError(message) {
  const el = document.getElementById("app-error");
  if (!el) return;
  const msg = (message || "").trim() || NETWORK_ERROR_MSG;
  el.textContent = msg;
  el.hidden = false;
  el.classList.add("is-visible");
}

function clearAppError() {
  const el = document.getElementById("app-error");
  if (!el) return;
  el.textContent = "";
  el.hidden = true;
  el.classList.remove("is-visible");
}

/** FastAPI detail: string | {msg}[] | object — mạng lỗi → câu thân thiện. */
function formatError(res, fallback) {
  if (!res || res.status === 0) {
    return NETWORK_ERROR_MSG;
  }
  const d = res.data && res.data.detail;
  if (typeof d === "string" && d) return d;
  if (Array.isArray(d)) {
    return d
      .map((x) => (x && (x.msg || x.message)) || JSON.stringify(x))
      .join("; ");
  }
  if (d && typeof d === "object") return JSON.stringify(d);
  if (res.text && res.text.length < 300 && res.text.trim()) return res.text;
  return fallback || NETWORK_ERROR_MSG;
}

function appendChat(role, text) {
  const box = document.getElementById("chat-messages");
  if (!box) return;
  const ph = box.querySelector("em");
  if (ph && /Chưa có hội thoại/i.test(ph.textContent || "")) {
    box.innerHTML = "";
  }
  const p = document.createElement("p");
  p.innerHTML = `<strong>${role === "user" ? "Bạn" : "Agent"}:</strong> ${escapeHtml(text)}`;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

function renderWatchlist(items) {
  const tbody = document.getElementById("watchlist-body");
  if (!tbody) return;
  if (!items || items.length === 0) {
    tbody.innerHTML = "<tr><td colspan=\"2\"><em>(Watchlist trống)</em></td></tr>";
    return;
  }
  tbody.innerHTML = items
    .map(
      (i) =>
        `<tr><td>${escapeHtml(i.symbol)}</td><td>${escapeHtml(String(i.threshold_pct))}</td></tr>`
    )
    .join("");
}

function renderApprovals(items) {
  const list = document.getElementById("approvals-list");
  if (!list) return;
  if (!items || items.length === 0) {
    list.innerHTML = "<li><em>(Không có cảnh báo chờ duyệt)</em></li>";
    return;
  }
  list.innerHTML = items
    .map((item) => {
      const id = item.approval_id || item.alert_id || item.proposal_id || "";
      const sym = item.symbol || (item.alert && item.alert.symbol) || "?";
      const gate = item.gate || "";
      const title =
        (item.alert && item.alert.title) ||
        (gate === "gate2"
          ? `Đề xuất ngưỡng ${item.proposed_threshold_pct ?? ""}`
          : "Cảnh báo");
      return (
        `<li data-approval-id="${escapeHtml(id)}">` +
        `<strong>${escapeHtml(sym)}</strong> — ${escapeHtml(title)}` +
        ` <span>(${escapeHtml(gate)})</span> ` +
        `<button type="button" data-approve-id="${escapeHtml(id)}">Approve</button>` +
        `<button type="button" data-reject-id="${escapeHtml(id)}">Reject</button>` +
        `</li>`
      );
    })
    .join("");
  wireApprovalButtons(list);
}

function showScanResult(data, errorText, isError) {
  const el = document.getElementById("scan-result");
  if (!el) return;
  el.style.display = "block";
  if (errorText) {
    el.textContent = errorText;
    if (isError) el.classList.add("is-error");
    else el.classList.remove("is-error");
    return;
  }
  el.classList.remove("is-error");
  // product-spec: thấy giá, tin, phân loại, (nếu bất thường) đánh giá + cảnh báo + gate
  const lines = [
    `Mã: ${data.symbol}`,
    `Phân loại: ${data.route}${data.reason ? ` — ${data.reason}` : ""}`,
    `Ngưỡng: ${data.threshold_pct}%`,
    `Giá: close=${data.price && data.price.latest_close}, prev=${data.price && data.price.prev_close}, Δ=${data.price && data.price.change_pct}%`,
  ];
  if (data.price && data.price.error) {
    lines.push(`Giá lỗi: ${data.price.error}`);
  }
  lines.push(`Tin: ${data.news_count}${data.news_error ? ` (lỗi: ${data.news_error})` : ""}`);
  if (data.news && data.news.length) {
    data.news.slice(0, 5).forEach((n, i) => {
      lines.push(`  ${i + 1}. ${n.title || "(không tiêu đề)"}`);
    });
  }
  if (data.severity) {
    const s = data.severity;
    lines.push(
      `Đánh giá: level=${s.level}, confidence=${s.confidence}` +
        (s.reasoning ? ` — ${s.reasoning}` : "")
    );
    if (s.evidence && s.evidence.length) {
      lines.push(`Evidence: ${s.evidence.join("; ")}`);
    }
    if (s.proposed_threshold_pct != null) {
      lines.push(`Đề xuất ngưỡng (Gate 2): ${s.proposed_threshold_pct}%`);
    }
  }
  lines.push(`Gate1: ${data.gate1_action ?? "—"}`);
  lines.push(`Gate2 pending: ${data.gate2_pending}`);
  if (data.alert) {
    lines.push(`Alert: ${data.alert.status} — ${data.alert.title || ""}`);
  }
  if (data.pending_events && data.pending_events.length) {
    lines.push(`Pending events: ${data.pending_events.length}`);
  }
  if (data.error) lines.push(`Lỗi: ${data.error}`);
  el.textContent = lines.join("\n");
}

async function refreshWatchlist() {
  const res = await getWatchlist();
  if (!res.ok) {
    const msg = formatError(res, NETWORK_ERROR_MSG);
    showAppError(msg);
    const tbody = document.getElementById("watchlist-body");
    if (tbody) {
      tbody.innerHTML =
        `<tr><td colspan="2"><em>${escapeHtml(msg)}</em></td></tr>`;
    }
    return;
  }
  renderWatchlist((res.data && res.data.items) || []);
}

async function refreshApprovals() {
  const res = await getApprovals();
  if (!res.ok) {
    const msg = formatError(res, NETWORK_ERROR_MSG);
    showAppError(msg);
    const list = document.getElementById("approvals-list");
    if (list) {
      list.innerHTML = `<li><em>${escapeHtml(msg)}</em></li>`;
    }
    return;
  }
  renderApprovals((res.data && res.data.items) || []);
}

function wireApprovalButtons(root) {
  root.querySelectorAll("[data-approve-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-approve-id");
      btn.disabled = true;
      const res = await approveAlert(id);
      if (!res.ok) {
        showAppError(formatError(res, "Approve thất bại"));
        btn.disabled = false;
        return;
      }
      clearAppError();
      await refreshApprovals();
      await refreshWatchlist();
    });
  });
  root.querySelectorAll("[data-reject-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-reject-id");
      const reason = window.prompt("Lý do reject:", "tin nhiễu");
      if (reason === null) return;
      const why = reason.trim();
      if (!why) {
        showAppError("lý do reject rỗng");
        return;
      }
      btn.disabled = true;
      const res = await rejectAlert(id, why);
      if (!res.ok) {
        showAppError(formatError(res, "Reject thất bại"));
        btn.disabled = false;
        return;
      }
      clearAppError();
      await refreshApprovals();
    });
  });
}

function wireUi() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  if (form && input) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const question = input.value.trim();
      if (!question) {
        showAppError("câu hỏi rỗng");
        return;
      }
      appendChat("user", question);
      input.value = "";
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      const res = await sendChat(question);
      if (btn) btn.disabled = false;
      if (!res.ok) {
        const msg = formatError(res, NETWORK_ERROR_MSG);
        showAppError(msg);
        appendChat("assistant", msg);
        return;
      }
      clearAppError();
      const answer = (res.data && res.data.answer) || "(không có câu trả lời)";
      appendChat("assistant", answer);
    });
  }

  const scanForm = document.getElementById("scan-form");
  const scanInput = document.getElementById("scan-symbol");
  if (scanForm && scanInput) {
    scanForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const symbol = scanInput.value.trim().toUpperCase();
      if (!symbol) {
        showAppError("symbol rỗng");
        return;
      }
      const btn = scanForm.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
      clearAppError();
      showScanResult(null, `Đang quét ${symbol}…`, false);
      const res = await scanSymbol(symbol);
      if (btn) btn.disabled = false;
      if (!res.ok) {
        const msg = formatError(res, NETWORK_ERROR_MSG);
        showAppError(msg);
        showScanResult(null, msg, true);
        return;
      }
      clearAppError();
      showScanResult(res.data);
      // Soft-fail nguồn: vẫn hiện trong scan-result + banner nếu có lỗi giá/tin
      const soft = [];
      if (res.data && res.data.price && res.data.price.error) {
        soft.push(res.data.price.error);
      }
      if (res.data && res.data.news_error) soft.push(res.data.news_error);
      if (soft.length) {
        showAppError(soft.join(" — ") || NETWORK_ERROR_MSG);
      }
      await refreshApprovals();
    });
  }

  refreshWatchlist();
  refreshApprovals();
}

document.addEventListener("DOMContentLoaded", wireUi);
