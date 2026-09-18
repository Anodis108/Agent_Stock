/* Portfolio Watch frontend — Phase 4: gọi Backend (bỏ mock). */
(function () {
  const STATUSES = ["pending", "running", "done", "error"];
  const USER_ID = "default";

  function backendBase() {
    if (typeof window.PW_getBackendBaseUrl === "function") {
      return window.PW_getBackendBaseUrl();
    }
    return (
      (window.PW_CONFIG && window.PW_CONFIG.BACKEND_BASE_URL) ||
      "http://127.0.0.1:8000"
    );
  }

  function apiUrl(path) {
    return backendBase() + path;
  }

  function requestTimeoutMs() {
    var n =
      (window.PW_CONFIG && window.PW_CONFIG.REQUEST_TIMEOUT_MS) || 90000;
    n = Number(n);
    return n > 0 ? n : 90000;
  }

  function formatApiError(err) {
    if (!err) return "lỗi không rõ";
    var name = err.name || "";
    var msg = String(err.message || err);
    if (name === "AbortError" || /aborted|timeout/i.test(msg)) {
      return "Hết thời gian chờ Backend/AI — thử lại sau.";
    }
    if (/failed to fetch|networkerror|load failed/i.test(msg)) {
      return "Không nối được Backend (kiểm tra :8000 còn chạy).";
    }
    return msg;
  }

  async function api(method, path, body) {
    var opts = {
      method: method,
      headers: { Accept: "application/json" },
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = null;
    if (ctrl) {
      opts.signal = ctrl.signal;
      timer = setTimeout(function () {
        try {
          ctrl.abort();
        } catch (_e) {}
      }, requestTimeoutMs());
    }
    try {
      var resp = await fetch(apiUrl(path), opts);
      var text = await resp.text();
      var data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch (_e) {
        data = { detail: text };
      }
      if (!resp.ok) {
        var detail =
          (data && (data.detail || data.message)) ||
          resp.statusText ||
          "lỗi " + resp.status;
        if (typeof detail !== "string") {
          detail = JSON.stringify(detail);
        }
        // 502 từ Backend khi AI down/timeout — giữ nguyên message
        throw new Error(detail);
      }
      return data;
    } catch (err) {
      throw new Error(formatApiError(err));
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  function setBoot(msg, isError) {
    var boot = document.getElementById("boot-status");
    if (!boot) return;
    boot.textContent = msg;
    boot.classList.toggle("boot-error", !!isError);
  }

  /** Chuẩn hoá steps[] theo contract Backend: {id,name,status,detail?} */
  function normalizeSteps(raw) {
    if (!raw || !raw.length) return [];
    var out = [];
    for (var i = 0; i < raw.length; i++) {
      var item = raw[i];
      if (!item || typeof item !== "object") continue;
      var status = item.status || "done";
      if (STATUSES.indexOf(status) < 0) status = "pending";
      var step = {
        id: String(item.id != null ? item.id : i + 1),
        name: String(item.name || item.tool || "step_" + (i + 1)),
        status: status,
      };
      if (item.detail != null && item.detail !== "") {
        step.detail = String(item.detail);
      }
      out.push(step);
    }
    return out;
  }

  var lastTimelineSteps = [];

  function renderTimeline(steps) {
    var ol = document.getElementById("timeline-steps");
    if (!ol) return;
    ol.innerHTML = "";
    var list = normalizeSteps(steps);
    lastTimelineSteps = list.slice();
    if (!list.length) {
      ol.innerHTML =
        '<li class="placeholder"><em>(Chưa có bước)</em></li>';
      return;
    }
    list.forEach(function (s) {
      var status = STATUSES.indexOf(s.status) >= 0 ? s.status : "pending";
      var li = document.createElement("li");
      li.className = "timeline-item status-" + status;
      li.dataset.status = status;
      li.dataset.stepId = s.id || "";

      var badge = document.createElement("span");
      badge.className = "status-badge status-" + status;
      badge.textContent = status;

      var name = document.createElement("strong");
      name.className = "step-name";
      name.textContent = s.name || "?";

      var detail = document.createElement("span");
      detail.className = "step-detail";
      detail.textContent = s.detail ? " — " + s.detail : "";

      li.appendChild(badge);
      li.appendChild(document.createTextNode(" "));
      li.appendChild(name);
      li.appendChild(detail);
      ol.appendChild(li);
    });
  }

  /** Đánh error lên bước running/pending (lỗi giữa chừng); giữ bước done trước. */
  function markTimelineMidError(kind, detail) {
    var msg = detail || "lỗi giữa chừng";
    var next = lastTimelineSteps.map(function (s) {
      return {
        id: s.id,
        name: s.name,
        status: s.status,
        detail: s.detail,
      };
    });
    var marked = false;
    for (var i = 0; i < next.length; i++) {
      if (next[i].status === "running" || next[i].status === "pending") {
        next[i].status = "error";
        next[i].detail = msg;
        marked = true;
        break;
      }
    }
    if (!marked) {
      next.push({
        id: String(next.length + 1),
        name: kind || "request",
        status: "error",
        detail: msg,
      });
    }
    renderTimeline(next);
    return next;
  }

  function showOpError(kind, err) {
    var msg = formatApiError(err);
    setBoot(kind + " lỗi: " + msg, true);
    markTimelineMidError(kind, msg);
    return msg;
  }

  /** test-plan: ít nhất start (running) rồi done — trước khi có steps từ Backend. */
  function showTimelineStart(kind) {
    renderTimeline([
      {
        id: "start",
        name: kind || "request",
        status: "running",
        detail: "Backend…",
      },
    ]);
  }

  /**
   * Cập nhật timeline từ Backend: ưu tiên GET /runs/{id}/steps,
   * fallback steps trong response chat/scan. Không gọi AI.
   */
  async function applyTimelineFromBackend(data) {
    var inline = normalizeSteps((data && data.steps) || []);
    var runId = data && data.run_id;
    var finalSteps = inline;
    if (runId) {
      try {
        var got = await api(
          "GET",
          "/runs/" + encodeURIComponent(runId) + "/steps"
        );
        var fromRun = normalizeSteps((got && got.steps) || []);
        if (fromRun.length) {
          finalSteps = fromRun;
        }
      } catch (_e) {
        /* fallback inline */
      }
    }
    renderTimeline(finalSteps);
    var errStep = null;
    for (var i = 0; i < finalSteps.length; i++) {
      if (finalSteps[i].status === "error") {
        errStep = finalSteps[i];
        break;
      }
    }
    if (errStep) {
      setBoot(
        "Bước lỗi: " +
          (errStep.name || "?") +
          (errStep.detail ? " — " + errStep.detail : ""),
        true
      );
    }
    return finalSteps;
  }

  function appendChat(role, text) {
    var box = document.getElementById("chat-messages");
    if (!box) return;
    var ph = box.querySelector(".placeholder");
    if (ph) ph.remove();
    var p = document.createElement("p");
    p.className = "chat-msg chat-" + role;
    var label = document.createElement("strong");
    label.textContent = role === "user" ? "Bạn: " : "Bot: ";
    p.appendChild(label);
    p.appendChild(document.createTextNode(text || ""));
    box.appendChild(p);
    box.scrollTop = box.scrollHeight;
  }

  function renderWatchlist(items) {
    var tbody = document.getElementById("watchlist-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!items || !items.length) {
      tbody.innerHTML =
        '<tr><td colspan="3" class="placeholder"><em>(Chưa có mã)</em></td></tr>';
      return;
    }
    items.forEach(function (it) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        (it.symbol || "") +
        "</td><td>" +
        (it.threshold_pct != null ? it.threshold_pct : "") +
        '</td><td class="actions"></td>';
      var actions = tr.querySelector(".actions");
      var scanBtn = document.createElement("button");
      scanBtn.type = "button";
      scanBtn.className = "btn-small";
      scanBtn.textContent = "Quét";
      scanBtn.addEventListener("click", function () {
        doScan(it.symbol, it.threshold_pct);
      });
      var delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn-small btn-muted";
      delBtn.textContent = "Xóa";
      delBtn.addEventListener("click", function () {
        doDeleteWatch(it.symbol);
      });
      var editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "btn-small btn-muted";
      editBtn.textContent = "Sửa";
      editBtn.addEventListener("click", function () {
        var cur = it.threshold_pct != null ? String(it.threshold_pct) : "3";
        var next = window.prompt("Ngưỡng % mới cho " + it.symbol + ":", cur);
        if (next == null || !String(next).trim()) return;
        var n = Number(next);
        if (!(n > 0)) {
          setBoot("Ngưỡng phải > 0", true);
          return;
        }
        doPatchWatch(it.symbol, n).catch(function (err) {
          setBoot("Sửa ngưỡng lỗi: " + (err.message || err), true);
        });
      });
      actions.appendChild(scanBtn);
      actions.appendChild(editBtn);
      actions.appendChild(delBtn);
      tbody.appendChild(tr);
    });
  }

  function renderApprovals(items) {
    var ul = document.getElementById("approvals-list");
    if (!ul) return;
    ul.innerHTML = "";
    if (!items || !items.length) {
      ul.innerHTML =
        '<li class="placeholder"><em>(Không có cảnh báo chờ duyệt)</em></li>';
      return;
    }
    items.forEach(function (it) {
      var li = document.createElement("li");
      li.className = "approval-item";
      var text = document.createElement("span");
      text.textContent =
        (it.symbol || "?") +
        " · " +
        (it.gate || "") +
        " · id=" +
        (it.id || "");
      li.appendChild(text);
      var row = document.createElement("span");
      row.className = "approval-actions";
      var ok = document.createElement("button");
      ok.type = "button";
      ok.className = "btn-small";
      ok.textContent = "Duyệt";
      ok.addEventListener("click", function () {
        doApprove(it.id).catch(function (err) {
          setBoot("Duyệt lỗi: " + (err.message || err), true);
          loadApprovals().catch(function () {});
        });
      });
      var no = document.createElement("button");
      no.type = "button";
      no.className = "btn-small btn-muted";
      no.textContent = "Từ chối";
      no.addEventListener("click", function () {
        var reason = window.prompt("Lý do từ chối:", "tin nhiễu");
        if (reason == null || !String(reason).trim()) return;
        doReject(it.id, String(reason).trim()).catch(function (err) {
          setBoot("Từ chối lỗi: " + (err.message || err), true);
          loadApprovals().catch(function () {});
        });
      });
      row.appendChild(ok);
      row.appendChild(no);
      li.appendChild(row);
      ul.appendChild(li);
    });
  }

  async function loadWatchlist() {
    var data = await api("GET", "/watchlist?user_id=" + encodeURIComponent(USER_ID));
    renderWatchlist((data && data.items) || []);
  }

  async function loadApprovals() {
    var data = await api(
      "GET",
      "/approvals?user_id=" + encodeURIComponent(USER_ID)
    );
    renderApprovals((data && data.items) || []);
  }

  function extractFinalAnswer(data) {
    if (!data) return "";
    if (typeof data.answer === "string" && data.answer.trim()) {
      return data.answer;
    }
    if (data.result && typeof data.result.answer === "string") {
      return data.result.answer;
    }
    return "";
  }

  async function doChat(question) {
    var sendBtn = document.getElementById("chat-send");
    if (sendBtn) sendBtn.disabled = true;
    appendChat("user", question);
    showTimelineStart("chat");
    setBoot("Đang chờ câu trả lời cuối từ Backend…");
    try {
      var data = await api("POST", "/chat", {
        question: question,
        user_id: USER_ID,
      });
      var answer = extractFinalAnswer(data);
      appendChat(
        "assistant",
        answer || "(không có câu trả lời cuối từ Backend)"
      );
      await applyTimelineFromBackend(data);
      setBoot(
        "Đã nhận câu trả lời cuối" +
          (data && data.run_id ? " · run_id=" + data.run_id : "")
      );
    } catch (err) {
      var msg = showOpError("chat", err);
      appendChat("assistant", "Lỗi: " + msg);
      throw err;
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  async function doScan(symbol, thresholdPct) {
    setBoot("Đang quét " + symbol + "…");
    showTimelineStart("scan");
    var body = { symbol: symbol, user_id: USER_ID };
    if (thresholdPct != null && thresholdPct !== "") {
      body.threshold_pct = Number(thresholdPct);
    }
    try {
      var data = await api("POST", "/scan", body);
      await applyTimelineFromBackend(data);
      await loadApprovals();
      setBoot(
        "Quét " + symbol + " xong · run_id=" + ((data && data.run_id) || "")
      );
    } catch (err) {
      showOpError("scan", err);
      throw err;
    }
  }

  async function doAddWatch(symbol, thresholdPct) {
    await api("POST", "/watchlist", {
      symbol: symbol,
      threshold_pct: thresholdPct,
      user_id: USER_ID,
    });
    await loadWatchlist();
  }

  async function doPatchWatch(symbol, thresholdPct) {
    await api("PATCH", "/watchlist/" + encodeURIComponent(symbol), {
      threshold_pct: thresholdPct,
      user_id: USER_ID,
    });
    await loadWatchlist();
    setBoot("Đã cập nhật ngưỡng " + symbol + " = " + thresholdPct + "%");
  }

  async function doDeleteWatch(symbol) {
    await api(
      "DELETE",
      "/watchlist/" +
        encodeURIComponent(symbol) +
        "?user_id=" +
        encodeURIComponent(USER_ID)
    );
    await loadWatchlist();
  }

  async function doApprove(id) {
    await api("POST", "/approvals/" + encodeURIComponent(id) + "/approve", {
      user_id: USER_ID,
    });
    await loadApprovals();
    setBoot("Đã duyệt " + id);
  }

  async function doReject(id, reason) {
    await api("POST", "/approvals/" + encodeURIComponent(id) + "/reject", {
      reason: reason,
      user_id: USER_ID,
    });
    await loadApprovals();
    setBoot("Đã từ chối " + id);
  }

  window.PW_renderTimeline = renderTimeline;
  window.PW_normalizeSteps = normalizeSteps;
  window.PW_applyTimelineFromBackend = applyTimelineFromBackend;
  window.PW_markTimelineMidError = markTimelineMidError;
  window.PW_api = api;

  var base = backendBase();
  var cfgEl = document.getElementById("backend-url-display");
  if (cfgEl) cfgEl.textContent = base;

  var chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = document.getElementById("chat-input");
      var q = input && input.value ? input.value.trim() : "";
      if (!q) return;
      if (input) input.value = "";
      doChat(q).catch(function () {
        /* lỗi đã hiện trong doChat (boot + timeline + chat) */
      });
    });
  }

  var wlForm = document.getElementById("watchlist-form");
  if (wlForm) {
    wlForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var symEl = document.getElementById("watchlist-symbol");
      var thrEl = document.getElementById("watchlist-threshold");
      var sym = symEl && symEl.value ? symEl.value.trim().toUpperCase() : "";
      var thr = thrEl && thrEl.value ? Number(thrEl.value) : undefined;
      if (!sym) return;
      doAddWatch(sym, thr)
        .then(function () {
          if (symEl) symEl.value = "";
          setBoot("Đã thêm " + sym);
        })
        .catch(function (err) {
          setBoot("Watchlist lỗi: " + (err.message || err), true);
        });
    });
  }

  var scanForm = document.getElementById("scan-form");
  if (scanForm) {
    scanForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var symEl = document.getElementById("scan-symbol");
      var sym = symEl && symEl.value ? symEl.value.trim().toUpperCase() : "";
      if (!sym) return;
      doScan(sym).catch(function () {
        /* lỗi đã hiện trong doScan */
      });
    });
  }

  renderTimeline([]);
  setBoot("BACKEND_BASE_URL=" + base + " · đang tải watchlist/approvals…");
  Promise.all([loadWatchlist(), loadApprovals()])
    .then(function () {
      setBoot("BACKEND_BASE_URL=" + base + " · đã nối Backend");
    })
    .catch(function (err) {
      setBoot(
        "Không nối được Backend (" + base + "): " + (err.message || err),
        true
      );
    });
})();
