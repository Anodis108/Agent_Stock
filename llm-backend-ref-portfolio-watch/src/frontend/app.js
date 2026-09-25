/* Portfolio Watch frontend — Phase 10: Claude-like Chat UI + Backend API */
(function () {
  const STATUSES = ["pending", "running", "done", "error"];
  const USER_ID = "default";

  function backendBase() {
    if (typeof window.PW_getBackendBaseUrl === "function") {
      return window.PW_getBackendBaseUrl();
    }
    if (window.PW_CONFIG && window.PW_CONFIG.BACKEND_BASE_URL !== undefined) {
      return String(window.PW_CONFIG.BACKEND_BASE_URL || "").replace(/\/+$/, "");
    }
    return "";
  }

  function backendBaseLabel() {
    var b = backendBase();
    return b ? b : "(same-origin)";
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

  function showChatErrorBanner(msg) {
    var banner = document.getElementById("chat-error-banner");
    var textEl = document.getElementById("chat-error-text");
    if (!banner) return;
    if (textEl) textEl.textContent = msg;
    banner.style.display = "flex";
  }

  function hideChatErrorBanner() {
    var banner = document.getElementById("chat-error-banner");
    if (banner) banner.style.display = "none";
  }

  /** Chuẩn hoá steps[] theo contract Backend: {id,name,status,detail?,input?,output?,duration_s?,duration_ms?} */
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
      if (item.duration_s != null) {
        step.duration_s = Number(item.duration_s);
      }
      if (item.duration_ms != null) {
        step.duration_ms = Number(item.duration_ms);
      } else if (step.duration_s != null) {
        step.duration_ms = Math.round(step.duration_s * 1000);
      }
      if (item.detail != null && item.detail !== "") {
        step.detail = String(item.detail);
      }
      if (item.input !== undefined && item.input !== null) {
        step.input = item.input;
      }
      if (item.output !== undefined && item.output !== null) {
        step.output = item.output;
      }
      out.push(step);
    }
    return out;
  }

  /* Phase 11: Live Graph & Hover I/O Inspector State & Helpers */
  var lastTimelineSteps = [];
  var lastLiveGraphSteps = [];
  var currentAnimTimer = null;
  var pinnedInspectorStepId = null;

  function getNodeIcon(name) {
    var lower = String(name || "").toLowerCase();
    if (lower.indexOf("rewrite") >= 0) return "🔄";
    if (lower.indexOf("supervisor") >= 0) return "🧭";
    if (lower.indexOf("price") >= 0) return "📈";
    if (lower.indexOf("news") >= 0) return "📰";
    if (lower.indexOf("classifier") >= 0) return "🏷️";
    if (lower.indexOf("eval") >= 0) return "⚖️";
    if (lower.indexOf("synthesis") >= 0) return "🔔";
    if (lower.indexOf("gate") >= 0) return "🛡️";
    if (lower.indexOf("compose") >= 0) return "✍️";
    if (lower.indexOf("chat") >= 0 || lower.indexOf("scan") >= 0 || lower.indexOf("request") >= 0) return "⚡";
    return "⚙️";
  }

  function setGraphStatus(text, statusClass) {
    var tag = document.getElementById("graph-status-tag");
    if (!tag) return;
    tag.textContent = text || "Sẵn sàng";
    tag.className = "graph-status-tag status-" + (statusClass || "idle");
  }

  function formatIO(val) {
    if (val === undefined || val === null) {
      return "(không có dữ liệu)";
    }
    if (typeof val === "object") {
      try {
        return JSON.stringify(val, null, 2);
      } catch (_e) {
        return String(val);
      }
    }
    return String(val);
  }

  function showNodeInspector(step, isPinned) {
    var inspector = document.getElementById("graph-node-inspector");
    if (!inspector || !step) return;
    // Chỉ cập nhật pin khi click (true/false tường minh). Hover/focus không gỡ pin.
    if (isPinned === true) {
      pinnedInspectorStepId = step.id;
    } else if (isPinned === false) {
      pinnedInspectorStepId = null;
    }

    var nameEl = document.getElementById("inspector-node-name");
    var badgeEl = document.getElementById("inspector-node-badge");
    var detailEl = document.getElementById("inspector-node-detail");
    var inPre = document.getElementById("inspector-input-content");
    var outPre = document.getElementById("inspector-output-content");

    if (nameEl) nameEl.textContent = step.name || "?";
    if (badgeEl) {
      badgeEl.textContent = step.status || "done";
      badgeEl.className = "status-badge status-" + (step.status || "done");
    }
    if (detailEl) {
      var durInfo = step.duration_s != null ? " · ⏱ " + (step.duration_s >= 1 ? step.duration_s.toFixed(2) + "s" : Math.round(step.duration_s * 1000) + "ms") : "";
      detailEl.textContent = (step.detail ? "Chi tiết: " + step.detail : "") + durInfo;
    }
    if (inPre) inPre.textContent = formatIO(step.input);
    if (outPre) outPre.textContent = formatIO(step.output);

    inspector.style.display = "block";

    // Highlight corresponding node card
    var allCards = document.querySelectorAll(".graph-node-card");
    allCards.forEach(function (c) {
      if (c.dataset.stepId === String(step.id)) {
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });
  }

  function hideNodeInspector(force) {
    if (!force && pinnedInspectorStepId) return;
    var inspector = document.getElementById("graph-node-inspector");
    if (inspector) inspector.style.display = "none";
    pinnedInspectorStepId = null;
    var allCards = document.querySelectorAll(".graph-node-card");
    allCards.forEach(function (c) {
      c.classList.remove("active");
    });
  }

  function showGraphStart(kind) {
    if (currentAnimTimer) {
      clearTimeout(currentAnimTimer);
      currentAnimTimer = null;
    }
    setGraphStatus("Đang chạy…", "running");
    var flow = document.getElementById("graph-nodes-flow");
    if (!flow) return;
    flow.innerHTML = "";

    var card = document.createElement("div");
    card.className = "graph-node-card status-running";
    card.tabIndex = 0;
    card.dataset.stepId = "start";
    card.innerHTML =
      '<span class="node-icon">⚡</span>' +
      '<span class="node-label">' + (kind || "request") + '</span>' +
      '<span class="node-status-dot"></span>';

    flow.appendChild(card);
  }

  function renderLiveGraphNodes(steps) {
    var flow = document.getElementById("graph-nodes-flow");
    if (!flow) return;
    flow.innerHTML = "";

    if (!steps || !steps.length) {
      flow.innerHTML =
        '<div class="graph-empty-state"><span class="empty-icon">📊</span><p class="muted tiny"><em>Chờ câu hỏi hoặc lượt quét để kích hoạt đồ thị</em></p></div>';
      return;
    }

    steps.forEach(function (step, idx) {
      if (idx > 0) {
        var arrow = document.createElement("span");
        arrow.className = "graph-connector" + (step.status === "done" ? " passed" : "");
        arrow.textContent = "→";
        flow.appendChild(arrow);
      }

      var card = document.createElement("div");
      var status = STATUSES.indexOf(step.status) >= 0 ? step.status : "pending";
      card.className = "graph-node-card status-" + status;
      if (pinnedInspectorStepId && String(step.id) === String(pinnedInspectorStepId)) {
        card.classList.add("active");
      }
      card.tabIndex = 0;
      card.dataset.stepId = String(step.id);
      card.dataset.stepIndex = String(idx);

      var icon = getNodeIcon(step.name);
      var durationHtml = "";
      if (step.duration_s != null && step.duration_s > 0) {
        var durStr = step.duration_s >= 1 ? step.duration_s.toFixed(2) + "s" : Math.round(step.duration_s * 1000) + "ms";
        durationHtml = '<span class="node-duration-badge" title="Thời gian: ' + step.duration_s + 's">⏱ ' + durStr + '</span>';
      }

      card.innerHTML =
        '<span class="node-icon">' + icon + '</span>' +
        '<span class="node-label">' + (step.name || "?") + '</span>' +
        durationHtml +
        '<span class="node-status-dot"></span>';

      card.addEventListener("mouseenter", function () {
        showNodeInspector(step);
      });
      card.addEventListener("focus", function () {
        showNodeInspector(step);
      });
      card.addEventListener("click", function () {
        if (String(pinnedInspectorStepId) === String(step.id)) {
          hideNodeInspector(true);
        } else {
          showNodeInspector(step, true);
        }
      });
      flow.appendChild(card);
    });
  }

  function animateLiveGraph(finalSteps) {
    return new Promise(function (resolve) {
      if (currentAnimTimer) {
        clearTimeout(currentAnimTimer);
        currentAnimTimer = null;
      }
      var list = normalizeSteps(finalSteps);
      lastLiveGraphSteps = list.slice();
      if (!list.length) {
        renderLiveGraphNodes([]);
        setGraphStatus("Sẵn sàng", "idle");
        resolve();
        return;
      }

      setGraphStatus("Đang thực thi…", "running");

      // Initial state: all pending except first running
      var animState = list.map(function (s, idx) {
        return {
          id: s.id,
          name: s.name,
          status: idx === 0 ? "running" : "pending",
          duration_s: s.duration_s,
          duration_ms: s.duration_ms,
          detail: s.detail,
          input: s.input,
          output: s.output,
        };
      });
      renderLiveGraphNodes(animState);

      var currentIdx = 0;
      var stepDuration = 200; // ms per step highlight

      function nextStep() {
        if (currentIdx < list.length) {
          // Transition currentIdx to final status (done or error)
          animState[currentIdx].status = list[currentIdx].status || "done";

          currentIdx++;
          if (currentIdx < list.length) {
            // Next node becomes running
            animState[currentIdx].status = "running";
            renderLiveGraphNodes(animState);
            currentAnimTimer = setTimeout(nextStep, stepDuration);
          } else {
            // All completed
            renderLiveGraphNodes(animState);
            var hasErr = animState.some(function (s) { return s.status === "error"; });
            var totalDur = list.reduce(function (sum, s) { return sum + (s.duration_s || 0); }, 0);
            var durLabel = totalDur > 0 ? " (" + (totalDur >= 1 ? totalDur.toFixed(2) + "s" : Math.round(totalDur * 1000) + "ms") + ")" : "";
            setGraphStatus((hasErr ? "Có lỗi" : "Hoàn tất") + durLabel, hasErr ? "error" : "done");
            // Show inspector for last step if user hasn't pinned one
            if (animState.length > 0 && !pinnedInspectorStepId) {
              showNodeInspector(animState[animState.length - 1], false);
            }
            resolve();
          }
        } else {
          resolve();
        }
      }

      currentAnimTimer = setTimeout(nextStep, stepDuration);
    });
  }

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
      li.style.cursor = "pointer";
      li.title = "Xem I/O bước này";

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

      if (s.duration_s != null && s.duration_s > 0) {
        var durStr = s.duration_s >= 1 ? s.duration_s.toFixed(2) + "s" : Math.round(s.duration_s * 1000) + "ms";
        var durBadge = document.createElement("span");
        durBadge.className = "timeline-duration-badge";
        durBadge.textContent = "⏱ " + durStr;
        durBadge.title = "Thời gian thực thi: " + s.duration_s + "s";
        li.appendChild(durBadge);
      }

      li.addEventListener("mouseenter", function () {
        showNodeInspector(s, false);
      });
      li.addEventListener("click", function () {
        showNodeInspector(s, true);
      });

      ol.appendChild(li);
    });
  }

  /** Đánh error lên bước running/pending (lỗi giữa chừng); giữ bước done trước. */
  function markTimelineMidError(kind, detail) {
    if (currentAnimTimer) {
      clearTimeout(currentAnimTimer);
      currentAnimTimer = null;
    }
    setGraphStatus("Lỗi", "error");
    var msg = detail || "lỗi giữa chừng";
    var next = lastTimelineSteps.map(function (s) {
      return {
        id: s.id,
        name: s.name,
        status: s.status,
        detail: s.detail,
        input: s.input,
        output: s.output,
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
        input: null,
        output: { error: msg },
      });
    }
    renderTimeline(next);
    renderLiveGraphNodes(next);
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
    showGraphStart(kind);
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
    animateLiveGraph(finalSteps);
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

  function removeThinking() {
    var box = document.getElementById("chat-messages");
    if (!box) return;
    var th = box.querySelectorAll(".chat-thinking");
    th.forEach(function (el) {
      el.remove();
    });
  }

  function appendThinking(text) {
    var box = document.getElementById("chat-messages");
    if (!box) return;
    removeThinking();
    var ph = box.querySelector(".placeholder");
    if (ph) ph.remove();

    var div = document.createElement("div");
    div.className = "chat-msg chat-thinking";

    var header = document.createElement("div");
    header.className = "msg-header";
    header.textContent = "⏳ Đang xử lý…";

    var body = document.createElement("div");
    body.className = "msg-body";
    body.textContent = text || "Portfolio Watch đang suy nghĩ…";

    div.appendChild(header);
    div.appendChild(body);
    box.appendChild(div);
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
        "<td><strong>" +
        (it.symbol || "") +
        "</strong></td><td>" +
        (it.threshold_pct != null ? it.threshold_pct + "%" : "") +
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
    var badge = document.getElementById("approvals-badge");
    var count = (items && items.length) || 0;
    if (badge) {
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = "inline-block";
      } else {
        badge.style.display = "none";
      }
    }
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
        doApprove(it.id).catch(function () {
          /* lỗi đã hiện trong doApprove (banner + boot) */
        });
      });
      var no = document.createElement("button");
      no.type = "button";
      no.className = "btn-small btn-muted";
      no.textContent = "Từ chối";
      no.addEventListener("click", function () {
        var reason = window.prompt("Lý do từ chối:", "tin nhiễu");
        if (reason == null || !String(reason).trim()) return;
        doReject(it.id, String(reason).trim()).catch(function () {
          /* lỗi đã hiện trong doReject (banner + boot) */
        });
      });
      row.appendChild(ok);
      row.appendChild(no);
      li.appendChild(row);
      ul.appendChild(li);
    });
  }

  async function safeLoadWatchlist() {
    hideWatchlistError();
    try {
      var data = await api("GET", "/watchlist?user_id=" + encodeURIComponent(USER_ID));
      renderWatchlist((data && data.items) || []);
    } catch (err) {
      var tbody = document.getElementById("watchlist-body");
      if (!tbody || tbody.children.length === 0) renderWatchlist([]);
      showWatchlistError("Lỗi tải Watchlist: " + formatApiError(err));
      throw err;
    }
  }

  async function safeLoadApprovals() {
    hideApprovalsError();
    try {
      var data = await api("GET", "/approvals?user_id=" + encodeURIComponent(USER_ID));
      renderApprovals((data && data.items) || []);
    } catch (err) {
      var ul = document.getElementById("approvals-list");
      if (!ul || ul.children.length === 0) renderApprovals([]);
      showApprovalsError("Lỗi tải Approvals: " + formatApiError(err));
      throw err;
    }
  }
  
  // Backwards compatibility aliases if any other code calls them by old names
  var loadWatchlist = safeLoadWatchlist;
  var loadApprovals = safeLoadApprovals;

  /* ==================== SESSIONS MANAGEMENT ==================== */
  var currentSessionId = null;
  var sessionList = [];

  function formatSessionTime(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      var now = new Date();
      var diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);
      if (diffSec < 60) return "Vừa xong";
      if (diffSec < 3600) return Math.floor(diffSec / 60) + " phút trước";
      if (diffSec < 86400) return Math.floor(diffSec / 3600) + " giờ trước";
      return d.toLocaleDateString("vi-VN", { month: "numeric", day: "numeric" });
    } catch (_e) {
      return "";
    }
  }

  function updateActiveSessionHeader(title) {
    var titleEl = document.getElementById("active-session-title");
    if (titleEl) {
      titleEl.textContent = title || "Cuộc trò chuyện mới";
    }
  }

  function renderSessionList() {
    var ul = document.getElementById("session-list");
    var badge = document.getElementById("session-count-badge");
    if (badge) {
      badge.textContent = sessionList.length;
    }
    if (!ul) return;
    ul.innerHTML = "";

    if (!sessionList.length) {
      ul.innerHTML = '<li class="session-placeholder"><em>Chưa có phiên chat nào</em></li>';
      return;
    }

    sessionList.forEach(function (s) {
      var li = document.createElement("li");
      li.className = "session-item" + (s.id === currentSessionId ? " active" : "");
      li.dataset.sessionId = s.id;
      li.tabIndex = 0;

      var contentDiv = document.createElement("div");
      contentDiv.className = "session-item-content";

      var titleSpan = document.createElement("span");
      titleSpan.className = "session-item-title";
      titleSpan.textContent = s.title || "Cuộc trò chuyện mới";
      titleSpan.title = s.title || "Cuộc trò chuyện mới";

      var timeSpan = document.createElement("span");
      timeSpan.className = "session-item-time";
      timeSpan.textContent = formatSessionTime(s.updated_at || s.created_at);

      contentDiv.appendChild(titleSpan);
      contentDiv.appendChild(timeSpan);

      var delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "session-del-btn";
      delBtn.title = "Xóa cuộc trò chuyện";
      delBtn.innerHTML = "✕";
      delBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        deleteSession(s.id);
      });

      li.appendChild(contentDiv);
      li.appendChild(delBtn);

      li.addEventListener("click", function () {
        if (currentSessionId !== s.id) {
          selectSession(s.id);
        }
      });

      ul.appendChild(li);
    });
  }

  async function loadSessions(autoSelectFirst) {
    try {
      var data = await api("GET", "/api/sessions");
      sessionList = (data && data.items) || [];
      renderSessionList();

      if (autoSelectFirst) {
        if (sessionList.length > 0) {
          if (!currentSessionId || !sessionList.some(function (s) { return s.id === currentSessionId; })) {
            await selectSession(sessionList[0].id);
          }
        } else {
          await createSession();
        }
      }
    } catch (err) {
      console.error("Lỗi tải danh sách sessions:", err);
    }
  }

  async function createSession(title) {
    try {
      var data = await api("POST", "/api/sessions", {
        title: title || "Cuộc trò chuyện mới",
      });
      currentSessionId = data.id;
      updateActiveSessionHeader(data.title || "Cuộc trò chuyện mới");
      await loadSessions(false);

      var box = document.getElementById("chat-messages");
      if (box) {
        box.innerHTML = '<p class="placeholder"><em>(Cuộc trò chuyện mới — hãy đặt câu hỏi về mã cổ phiếu bên dưới)</em></p>';
      }
      hideChatErrorBanner();
      var input = document.getElementById("chat-input");
      if (input) input.focus();
      return data;
    } catch (err) {
      showChatErrorBanner("Không thể tạo phiên chat: " + formatApiError(err));
      throw err;
    }
  }

  async function selectSession(sessionId) {
    currentSessionId = sessionId;
    renderSessionList();
    hideChatErrorBanner();

    var box = document.getElementById("chat-messages");
    if (box) {
      box.innerHTML = '<p class="placeholder"><em>Đang tải tin nhắn…</em></p>';
    }

    try {
      var detail = await api("GET", "/api/sessions/" + encodeURIComponent(sessionId));
      var session = detail && detail.session;
      updateActiveSessionHeader(session ? session.title : "Cuộc trò chuyện");

      if (!box) return;
      box.innerHTML = "";

      var msgs = (detail && detail.messages) || [];
      if (!msgs.length) {
        box.innerHTML = '<p class="placeholder"><em>(Chưa có hội thoại — hãy đặt câu hỏi về mã cổ phiếu bên dưới)</em></p>';
        return;
      }

      msgs.forEach(function (m) {
        appendChat(m.role, m.content, null, m.chart_path, m.id, sessionId);
      });
    } catch (err) {
      if (box) {
        box.innerHTML = '<p class="placeholder"><em>Lỗi khi tải lịch sử chat: ' + formatApiError(err) + '</em></p>';
      }
      showChatErrorBanner("Không tải được lịch sử chat: " + formatApiError(err));
    }
  }

  async function deleteSession(sessionId) {
    if (!window.confirm("Bạn có chắc muốn xóa cuộc trò chuyện này?")) {
      return;
    }
    try {
      await api("DELETE", "/api/sessions/" + encodeURIComponent(sessionId));
      if (currentSessionId === sessionId) {
        currentSessionId = null;
      }
      await loadSessions(true);
    } catch (err) {
      showChatErrorBanner("Xóa phiên chat thất bại: " + formatApiError(err));
    }
  }

  function formatMarketStatus(status) {
    var map = {
      normal: "Bình thường",
      abnormal: "Bất thường",
      pending: "Chờ duyệt",
      unknown: "Chưa quét",
    };
    return map[status] || status || "—";
  }

  function showMarketError(msg) {
    var el = document.getElementById("market-error");
    if (!el) return;
    el.textContent = msg;
    el.style.display = "block";
  }

  function hideMarketError() {
    var el = document.getElementById("market-error");
    if (el) el.style.display = "none";
  }

  function showWatchlistError(msg) {
    var el = document.getElementById("watchlist-error");
    if (!el) return;
    el.textContent = msg;
    el.style.display = "block";
  }

  function hideWatchlistError() {
    var el = document.getElementById("watchlist-error");
    if (el) el.style.display = "none";
  }

  function showApprovalsError(msg) {
    var el = document.getElementById("approvals-error");
    if (!el) return;
    el.textContent = msg;
    el.style.display = "block";
  }

  function hideApprovalsError() {
    var el = document.getElementById("approvals-error");
    if (el) el.style.display = "none";
  }

  function showScanError(msg) {
    var el = document.getElementById("scan-error");
    if (!el) return;
    el.textContent = msg;
    el.style.display = "block";
  }

  function hideScanError() {
    var el = document.getElementById("scan-error");
    if (el) el.style.display = "none";
  }

  function formatMarketTime(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleString("vi-VN");
    } catch (_e) {
      return iso;
    }
  }

  function renderMarket(items) {
    var tbody = document.getElementById("market-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!items || !items.length) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="placeholder"><em>(Chưa có mã trong watchlist)</em></td></tr>';
      return;
    }
    items.forEach(function (it) {
      var tr = document.createElement("tr");
      var price =
        it.price != null && !isNaN(Number(it.price))
          ? Number(it.price).toLocaleString("vi-VN")
          : "—";
      var pct =
        it.change_pct != null && !isNaN(Number(it.change_pct))
          ? Number(it.change_pct).toFixed(2) + "%"
          : "—";
      var statusClass = "market-status market-status-" + (it.status || "unknown");
      tr.innerHTML =
        "<td><strong>" +
        (it.symbol || "") +
        "</strong></td><td>" +
        price +
        "</td><td>" +
        pct +
        '</td><td><span class="' +
        statusClass +
        '">' +
        formatMarketStatus(it.status) +
        "</span></td><td>" +
        formatMarketTime(it.updated_at) +
        "</td>";
      tbody.appendChild(tr);
    });
  }

  async function safeLoadMarket() {
    hideMarketError();
    try {
      var data = await api(
        "GET",
        "/market?user_id=" + encodeURIComponent(USER_ID)
      );
      renderMarket((data && data.items) || []);
    } catch (err) {
      var tbody = document.getElementById("market-body");
      if (!tbody || tbody.children.length === 0) renderMarket([]);
      showMarketError(
        "Không tải được Market status: " + formatApiError(err)
      );
      throw err;
    }
  }

  var loadMarket = safeLoadMarket;

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

  function initMermaid() {
    if (!window.mermaid || window.PW_mermaidReady) return;
    try {
      mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
      window.PW_mermaidReady = true;
    } catch (err) {
      console.error("Mermaid initialize error", err);
    }
  }

  function renderMermaidInElement(el, code) {
    if (!el || !code) return;
    initMermaid();
    el.classList.add("mermaid");
    el.textContent = code;
    if (window.mermaid) {
      try {
        if (mermaid.run) {
          mermaid.run({ nodes: [el] }).catch(function (err) {
            console.error("Mermaid run error", err);
          });
        } else if (mermaid.init) {
          mermaid.init(undefined, el);
        }
      } catch (err) {
        console.error("Mermaid render error", err);
      }
    }
  }

  function openChartModal(src, caption) {
    var modal = document.getElementById("chart-modal");
    var modalImg = document.getElementById("chart-modal-img");
    var modalCaption = document.getElementById("chart-modal-caption");
    if (!modal || !modalImg) return;
    modalImg.src = src;
    if (modalCaption) {
      modalCaption.textContent = caption ? caption.slice(0, 140) : "Biểu đồ tài chính";
    }
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  function closeChartModal() {
    var modal = document.getElementById("chart-modal");
    if (!modal) return;
    modal.style.display = "none";
    document.body.style.overflow = "";
    var modalImg = document.getElementById("chart-modal-img");
    if (modalImg) modalImg.src = "";
  }

  function initChartModal() {
    var modalClose = document.getElementById("chart-modal-close");
    if (modalClose) {
      modalClose.addEventListener("click", closeChartModal);
    }
    var modalBackdrop = document.getElementById("chart-modal-backdrop");
    if (modalBackdrop) {
      modalBackdrop.addEventListener("click", closeChartModal);
    }
    window.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeChartModal();
      }
    });
  }

  function appendChat(role, text, diagram, chartPath, messageId, sessionId) {
    var box = document.getElementById("chat-messages");
    if (!box) return;
    removeThinking();
    var ph = box.querySelector(".placeholder");
    if (ph) ph.remove();

    var div = document.createElement("div");
    div.className = "chat-msg chat-" + role;

    var header = document.createElement("div");
    header.className = "msg-header";

    if (role === "user") {
      header.textContent = "👤 Bạn";
    } else if (role === "error") {
      header.textContent = "⚠️ Lỗi hệ thống / Mạng";
    } else {
      header.textContent = "🤖 Portfolio Watch";
    }

    var body = document.createElement("div");
    body.className = "msg-body";
    
    var cleanText = text || "";
    var diagramCode = diagram && diagram.mermaid ? diagram.mermaid : null;
    
    var mermaidMatch = cleanText.match(/```mermaid\n([\s\S]*?)```/);
    if (mermaidMatch) {
      if (!diagramCode) {
        diagramCode = mermaidMatch[1];
      }
      cleanText = cleanText.replace(/```mermaid\n[\s\S]*?```/, "").trim();
    }
    
    if (cleanText) {
      var textNode = document.createElement("div");
      textNode.className = "msg-text";
      textNode.textContent = cleanText;
      body.appendChild(textNode);
    }

    if (diagramCode && role === "assistant") {
      var diagramPanel = document.createElement("div");
      diagramPanel.className = "diagram-panel mermaid-diagram";
      body.appendChild(diagramPanel);
      renderMermaidInElement(diagramPanel, diagramCode);
    }

    // Chart image rendering (Phase 4)
    if (chartPath && role === "assistant") {
      var chartContainer = document.createElement("div");
      chartContainer.className = "chat-chart-container";
      
      var img = document.createElement("img");
      img.className = "chat-chart-img";
      img.src = chartPath;
      img.alt = "Biểu đồ tài chính";
      img.loading = "lazy";
      img.title = "Click để phóng to";
      
      var hint = document.createElement("div");
      hint.className = "chat-chart-hint";
      hint.innerHTML = "<span>🔍</span> Nhấn vào ảnh để phóng to";

      chartContainer.addEventListener("click", function () {
        openChartModal(chartPath, cleanText || "Biểu đồ tài chính");
      });

      chartContainer.appendChild(img);
      chartContainer.appendChild(hint);
      body.appendChild(chartContainer);
    }

    // HITL Answer Evaluation & Feedback Toolbar (Phase 6)
    if (role === "assistant") {
      var feedbackComp = createHitlFeedbackComponent(messageId, sessionId || currentSessionId);
      body.appendChild(feedbackComp);
    }

    div.appendChild(header);
    div.appendChild(body);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  async function doChat(question) {
    var sendBtn = document.getElementById("chat-send");
    if (sendBtn) sendBtn.disabled = true;
    hideChatErrorBanner();
    appendChat("user", question);
    appendThinking("Portfolio Watch đang suy nghĩ và kiểm tra dữ liệu…");
    showTimelineStart("chat");
    setBoot("Đang kết nối hệ thống phân tích…");

    var chatPayload = {
      question: question,
      user_id: USER_ID,
    };
    if (currentSessionId) {
      chatPayload.session_id = currentSessionId;
    }

    var realtimeSteps = [];
    var streamedText = "";
    var streamingMsgDiv = null;
    var streamingTextEl = null;

    function getOrCreateStreamingMessage() {
      if (streamingMsgDiv) return streamingTextEl;
      removeThinking();
      var box = document.getElementById("chat-messages");
      if (!box) return null;
      var ph = box.querySelector(".placeholder");
      if (ph) ph.remove();

      streamingMsgDiv = document.createElement("div");
      streamingMsgDiv.className = "chat-msg chat-assistant chat-streaming";

      var header = document.createElement("div");
      header.className = "msg-header";
      header.textContent = "🤖 Portfolio Watch";

      var body = document.createElement("div");
      body.className = "msg-body";

      streamingTextEl = document.createElement("div");
      streamingTextEl.className = "msg-text";
      streamingTextEl.textContent = "";

      body.appendChild(streamingTextEl);
      streamingMsgDiv.appendChild(header);
      streamingMsgDiv.appendChild(body);
      box.appendChild(streamingMsgDiv);
      box.scrollTop = box.scrollHeight;
      return streamingTextEl;
    }

    function handleEvent(eventName, data) {
      if (eventName === "node_start") {
        var nodeName = data.node || "agent";
        var existing = realtimeSteps.find(function (s) { return s.name === nodeName || s.id === nodeName; });
        if (!existing) {
          existing = {
            id: nodeName,
            name: nodeName,
            status: "running",
            detail: "Đang xử lý…",
            input: data.input || null,
            output: null,
          };
          realtimeSteps.push(existing);
        } else {
          existing.status = "running";
          existing.detail = "Đang xử lý…";
        }
        renderLiveGraphNodes(realtimeSteps);
        renderTimeline(realtimeSteps);
        setGraphStatus("Đang chạy (" + nodeName + ")…", "running");
        setBoot("Agent đang chạy: " + nodeName);
      } else if (eventName === "node_finish") {
        var nodeName = data.node || "agent";
        var existing = realtimeSteps.find(function (s) { return s.name === nodeName || s.id === nodeName; });
        if (existing) {
          existing.status = "done";
          if (data.duration_s != null) existing.duration_s = Number(data.duration_s);
          if (data.duration_ms != null) existing.duration_ms = Number(data.duration_ms);
          var durStr = existing.duration_s != null ? (existing.duration_s >= 1 ? existing.duration_s.toFixed(2) + "s" : existing.duration_ms + "ms") : "";
          existing.detail = "Hoàn tất" + (durStr ? " (⏱ " + durStr + ")" : "");
        }
        renderLiveGraphNodes(realtimeSteps);
        renderTimeline(realtimeSteps);
      } else if (eventName === "token") {
        var delta = data.delta || "";
        streamedText += delta;
        var textEl = getOrCreateStreamingMessage();
        if (textEl) {
          textEl.textContent = streamedText;
          var box = document.getElementById("chat-messages");
          if (box) box.scrollTop = box.scrollHeight;
        }
      } else if (eventName === "complete") {
        if (streamingMsgDiv) {
          streamingMsgDiv.remove();
          streamingMsgDiv = null;
          streamingTextEl = null;
        } else {
          removeThinking();
        }

        var finalAnswer = data.answer || streamedText || "(không có câu trả lời cuối từ Backend)";
        var diagram = data.diagram || null;
        var chartPath = data.chart_path || null;
        var messageId = data.message_id || null;
        var sid = data.session_id || currentSessionId;

        appendChat("assistant", finalAnswer, diagram, chartPath, messageId, sid);

        if (data.session_id) {
          currentSessionId = data.session_id;
        }
        loadSessions(false).catch(function () {});

        if (data.steps && data.steps.length) {
          realtimeSteps = normalizeSteps(data.steps);
        } else {
          realtimeSteps.forEach(function (s) { s.status = "done"; });
        }
        renderTimeline(realtimeSteps);
        renderLiveGraphNodes(realtimeSteps);

        var durLabel = data.total_duration_s != null ? " (" + Number(data.total_duration_s).toFixed(2) + "s)" : "";
        setGraphStatus("Hoàn tất" + durLabel, "done");
        setBoot("Đã nhận câu trả lời cuối" + (data.total_duration_s ? " · ⏱ " + Number(data.total_duration_s).toFixed(2) + "s" : ""));

        if (realtimeSteps.length > 0 && !pinnedInspectorStepId) {
          showNodeInspector(realtimeSteps[realtimeSteps.length - 1], false);
        }
      } else if (eventName === "error") {
        removeThinking();
        if (streamingMsgDiv) {
          streamingMsgDiv.remove();
          streamingMsgDiv = null;
        }
        var errMsg = data.error || "Lỗi không xác định từ Backend";
        markTimelineMidError("chat", errMsg);
        appendChat("error", "Lỗi: " + errMsg);
        showChatErrorBanner("Không thể hoàn tất câu hỏi: " + errMsg);
      }
    }

    try {
      var resp = await fetch(apiUrl("/chat/stream"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify(chatPayload),
      });

      if (!resp.ok || !resp.body) {
        // Fallback sang POST /chat thông thường nếu stream gặp sự cố
        console.warn("SSE stream không khả dụng, fallback sang REST POST /chat");
        var fallbackData = await api("POST", "/chat", chatPayload);
        removeThinking();
        var answer = extractFinalAnswer(fallbackData);
        var diagram = fallbackData.diagram || (fallbackData.result && fallbackData.result.diagram);
        var chartPath = fallbackData.chart_path || (fallbackData.result && fallbackData.result.chart_path);
        var messageId = fallbackData.message_id || (fallbackData.result && fallbackData.result.message_id);
        var sid = fallbackData.session_id || currentSessionId;
        appendChat("assistant", answer || "(không có câu trả lời cuối từ Backend)", diagram, chartPath, messageId, sid);
        if (fallbackData && fallbackData.session_id) currentSessionId = fallbackData.session_id;
        loadSessions(false).catch(function () {});
        await applyTimelineFromBackend(fallbackData);
        setBoot("Đã nhận câu trả lời cuối");
        return;
      }

      var reader = resp.body.getReader();
      var decoder = new TextDecoder("utf-8");
      var buffer = "";

      while (true) {
        var chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });

        var parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (var i = 0; i < parts.length; i++) {
          var block = parts[i].trim();
          if (!block) continue;
          var lines = block.split("\n");
          var currentEvt = "message";
          var dataLines = [];
          for (var j = 0; j < lines.length; j++) {
            var line = lines[j].trim();
            if (line.indexOf("event:") === 0) {
              currentEvt = line.substring(6).trim();
            } else if (line.indexOf("data:") === 0) {
              dataLines.push(line.substring(5).trim());
            }
          }
          if (dataLines.length > 0) {
            var rawData = dataLines.join("\n");
            var parsed = null;
            try {
              parsed = JSON.parse(rawData);
            } catch (_e) {
              parsed = { text: rawData };
            }
            handleEvent(currentEvt, parsed);
          }
        }
      }

      if (buffer.trim()) {
        var lines = buffer.trim().split("\n");
        var currentEvt = "message";
        var dataLines = [];
        for (var j = 0; j < lines.length; j++) {
          var line = lines[j].trim();
          if (line.indexOf("event:") === 0) {
            currentEvt = line.substring(6).trim();
          } else if (line.indexOf("data:") === 0) {
            dataLines.push(line.substring(5).trim());
          }
        }
        if (dataLines.length > 0) {
          try {
            handleEvent(currentEvt, JSON.parse(dataLines.join("\n")));
          } catch (_e) {}
        }
      }
    } catch (err) {
      removeThinking();
      if (streamingMsgDiv) {
        streamingMsgDiv.remove();
        streamingMsgDiv = null;
      }
      var msg = showOpError("chat", err);
      appendChat("error", "Lỗi: " + msg);
      showChatErrorBanner("Không thể hoàn tất câu hỏi: " + msg);
      throw err;
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  async function doScan(symbol, thresholdPct) {
    hideScanError();
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
      await loadMarket().catch(function () {});
      setBoot(
        "Quét " + symbol + " xong · run_id=" + ((data && data.run_id) || "")
      );
    } catch (err) {
      showOpError("scan", err);
      showScanError("Quét lỗi: " + formatApiError(err));
      throw err;
    }
  }

  async function doAddWatch(symbol, thresholdPct) {
    hideWatchlistError();
    try {
      await api("POST", "/watchlist", {
        symbol: symbol,
        threshold_pct: thresholdPct,
        user_id: USER_ID,
      });
      await loadWatchlist();
      await loadMarket().catch(function () {});
    } catch (err) {
      showWatchlistError("Thêm mã lỗi: " + formatApiError(err));
      throw err;
    }
  }

  async function doPatchWatch(symbol, thresholdPct) {
    hideWatchlistError();
    try {
      await api("PATCH", "/watchlist/" + encodeURIComponent(symbol), {
        threshold_pct: thresholdPct,
        user_id: USER_ID,
      });
      await loadWatchlist();
      await loadMarket().catch(function () {});
      setBoot("Đã cập nhật ngưỡng " + symbol + " = " + thresholdPct + "%");
    } catch (err) {
      showWatchlistError("Sửa ngưỡng lỗi: " + formatApiError(err));
      throw err;
    }
  }

  async function doDeleteWatch(symbol) {
    hideWatchlistError();
    try {
      await api(
        "DELETE",
        "/watchlist/" +
          encodeURIComponent(symbol) +
          "?user_id=" +
          encodeURIComponent(USER_ID)
      );
      await loadWatchlist();
      await loadMarket().catch(function () {});
    } catch (err) {
      showWatchlistError("Xóa mã lỗi: " + formatApiError(err));
      throw err;
    }
  }

  async function doApprove(id) {
    hideApprovalsError();
    try {
      await api("POST", "/approvals/" + encodeURIComponent(id) + "/approve", {
        user_id: USER_ID,
      });
      await loadApprovals();
      await loadMarket().catch(function () {});
      setBoot("Đã duyệt " + id);
    } catch (err) {
      showApprovalsError("Duyệt lỗi: " + formatApiError(err));
      setBoot("Duyệt lỗi: " + formatApiError(err), true);
      await loadApprovals().catch(function () {});
      throw err;
    }
  }

  async function doReject(id, reason) {
    hideApprovalsError();
    try {
      await api("POST", "/approvals/" + encodeURIComponent(id) + "/reject", {
        reason: reason,
        user_id: USER_ID,
      });
      await loadApprovals();
      await loadMarket().catch(function () {});
      setBoot("Đã từ chối " + id);
    } catch (err) {
      showApprovalsError("Từ chối lỗi: " + formatApiError(err));
      setBoot("Từ chối lỗi: " + formatApiError(err), true);
      await loadApprovals().catch(function () {});
      throw err;
    }
  }

  function initTabs() {
    var tabBtns = document.querySelectorAll(".tab-btn");
    var tabPanes = document.querySelectorAll(".tab-pane");
    tabBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var targetId = btn.getAttribute("data-tab");
        tabBtns.forEach(function (b) {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        tabPanes.forEach(function (p) {
          p.classList.remove("active");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        var targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add("active");
        if (targetId === "market") {
          loadMarket().catch(function () {});
        }
      });
    });
  }

  function initHints() {
    var chips = document.querySelectorAll(".hint-chip");
    var input = document.getElementById("chat-input");
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        if (!input) return;
        input.value = chip.textContent.trim();
        input.focus();
      });
    });
  }

  window.PW_renderTimeline = renderTimeline;
  window.PW_normalizeSteps = normalizeSteps;
  window.PW_applyTimelineFromBackend = applyTimelineFromBackend;
  window.PW_markTimelineMidError = markTimelineMidError;
  window.PW_api = api;
  window.PW_appendChat = appendChat;
  window.PW_showChatErrorBanner = showChatErrorBanner;
  window.PW_hideChatErrorBanner = hideChatErrorBanner;
  window.PW_renderLiveGraph = renderLiveGraphNodes;
  window.PW_animateLiveGraph = animateLiveGraph;
  window.PW_showNodeInspector = showNodeInspector;
  window.PW_hideNodeInspector = hideNodeInspector;
  window.PW_renderMermaidInElement = renderMermaidInElement;
  window.PW_loadSessions = loadSessions;
  window.PW_createSession = createSession;
  window.PW_selectSession = selectSession;
  window.PW_deleteSession = deleteSession;
  window.PW_doChat = doChat;

  var baseLabel = backendBaseLabel();
  var cfgEl = document.getElementById("backend-url-display");
  if (cfgEl) cfgEl.textContent = baseLabel;

  var chatForm = document.getElementById("chat-form");
  var chatInput = document.getElementById("chat-input");
  if (chatInput) {
    chatInput.addEventListener("input", function () {
      hideChatErrorBanner();
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = document.getElementById("chat-input");
      var q = input && input.value ? input.value.trim() : "";
      if (!q) return;
      if (input) input.value = "";
      doChat(q).catch(function () {
        /* lỗi đã hiện trong doChat (banner + timeline + chat thread) */
      });
    });
  }

  var errDismiss = document.getElementById("chat-error-dismiss");
  if (errDismiss) {
    errDismiss.addEventListener("click", hideChatErrorBanner);
  }

  var newSessionBtn = document.getElementById("btn-new-session");
  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", function () {
      createSession().catch(function () {});
    });
  }

  var inspectorCloseBtn = document.getElementById("inspector-close-btn");
  if (inspectorCloseBtn) {
    inspectorCloseBtn.addEventListener("click", function () {
      hideNodeInspector(true);
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

  /* --------------------------------------------------------------------------
     Phase 5: Market Watch (10D) Matrix & Header Navigation
     -------------------------------------------------------------------------- */

  function generateSparklineSvg(prices, width, height) {
    width = width || 100;
    height = height || 28;
    var pad = 4;
    if (!Array.isArray(prices) || prices.length < 2) {
      return '<span class="muted tiny">N/A</span>';
    }

    var valid = prices.filter(function(p) { return typeof p === "number" && !isNaN(p); });
    if (valid.length < 2) {
      return '<span class="muted tiny">N/A</span>';
    }

    var min = Math.min.apply(null, valid);
    var max = Math.max.apply(null, valid);
    var range = max - min;
    var n = valid.length;

    var points = [];
    for (var i = 0; i < n; i++) {
      var x = pad + (i / (n - 1)) * (width - 2 * pad);
      var y = range === 0 ? (height / 2) : (height - pad - ((valid[i] - min) / range) * (height - 2 * pad));
      points.push(x.toFixed(1) + "," + y.toFixed(1));
    }

    var isUp = valid[n - 1] >= valid[0];
    var strokeColor = isUp ? "#059669" : "#dc2626";
    var lastPoint = points[points.length - 1].split(",");

    return (
      '<svg class="sparkline-svg" viewBox="0 0 ' + width + ' ' + height + '" width="' + width + '" height="' + height + '">' +
        '<polyline fill="none" stroke="' + strokeColor + '" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="' + points.join(" ") + '" />' +
        '<circle cx="' + lastPoint[0] + '" cy="' + lastPoint[1] + '" r="2.5" fill="' + strokeColor + '" />' +
      '</svg>'
    );
  }

  function renderMarketMatrix(items) {
    var thead = document.getElementById("market-matrix-thead");
    var tbody = document.getElementById("market-matrix-tbody");
    if (!tbody) return;

    if (!Array.isArray(items) || items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="15" class="matrix-loading-cell"><em>(Không có dữ liệu ma trận)</em></td></tr>';
      return;
    }

    // Dynamic session dates from the first item
    var dates = [];
    if (items[0].sessions && Array.isArray(items[0].sessions)) {
      dates = items[0].sessions.map(function (s) { return s.date; });
    }

    if (thead) {
      var headerHtml = '<tr>' +
        '<th class="th-symbol">Mã</th>' +
        '<th class="th-price">Giá hiện tại</th>' +
        '<th class="th-change">+/- (%)</th>';

      if (dates.length) {
        for (var dIdx = 0; dIdx < dates.length; dIdx++) {
          var d = dates[dIdx];
          var parts = d ? d.split("-") : [];
          var displayDate = parts.length === 3 ? (parts[2] + "/" + parts[1]) : d;
          var isLatest = (dIdx === dates.length - 1);
          var dayOffset = dates.length - 1 - dIdx;
          var offsetLabel = dayOffset === 0 ? "H.nay" : ("T-" + dayOffset);
          headerHtml += '<th class="th-session-col' + (isLatest ? ' th-session-latest' : '') + '" title="Phiên ' + d + '">' +
            '<span class="th-day-label">' + offsetLabel + '</span>' +
            '<span class="th-date-sub">' + displayDate + '</span>' +
          '</th>';
        }
      } else {
        headerHtml += '<th colspan="10" class="th-session-col">10 Phiên gần nhất</th>';
      }

      headerHtml += '<th class="th-volume">Tổng KL (10D)</th>' +
        '<th class="th-sparkline">Xu hướng (10D)</th>' +
        '</tr>';
      thead.innerHTML = headerHtml;
    }

    var rowsHtml = "";
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var sym = item.symbol || "---";
      var curPrice = typeof item.current_price === "number"
        ? item.current_price.toLocaleString("vi-VN", { minimumFractionDigits: 1, maximumFractionDigits: 2 })
        : "---";
      var changePct = typeof item.change_pct === "number" ? item.change_pct : 0;
      var changeSign = changePct > 0 ? "+" : "";
      var changeClass = changePct > 0 ? "cell-up" : changePct < 0 ? "cell-down" : "cell-ref";
      var totalVol = typeof item.total_volume === "number" ? item.total_volume.toLocaleString("vi-VN") : "---";

      rowsHtml += '<tr class="matrix-row">' +
        '<td class="td-symbol"><strong>' + sym + '</strong></td>' +
        '<td class="td-price">' + curPrice + '</td>' +
        '<td class="td-change ' + changeClass + '">' + changeSign + changePct.toFixed(2) + '%</td>';

      if (item.sessions && Array.isArray(item.sessions)) {
        for (var sIdx = 0; sIdx < item.sessions.length; sIdx++) {
          var s = item.sessions[sIdx];
          var sPct = typeof s.change_pct === "number" ? s.change_pct : 0;
          var sClass = sPct > 0 ? "matrix-cell-up" : sPct < 0 ? "matrix-cell-down" : "matrix-cell-ref";
          var sSign = sPct > 0 ? "+" : "";
          var sClose = typeof s.close === "number" ? s.close.toFixed(1) : "---";
          var tooltip = "Mã: " + sym + "\nNgày: " + (s.date || "") +
            "\nĐóng cửa: " + sClose +
            "\nBiến động: " + sSign + sPct.toFixed(2) + "%" +
            (s.volume ? "\nKhối lượng: " + s.volume.toLocaleString("vi-VN") : "");

          rowsHtml += '<td class="td-session ' + sClass + '" title="' + tooltip.replace(/"/g, '&quot;') + '">' +
            '<span class="session-price">' + sClose + '</span>' +
            '<span class="session-change">' + sSign + sPct.toFixed(1) + '%</span>' +
          '</td>';
        }
      } else {
        rowsHtml += '<td colspan="10" class="muted tiny">Chưa có dữ liệu phiên</td>';
      }

      var sparklineSvg = generateSparklineSvg(item.sparkline || []);
      rowsHtml += '<td class="td-volume">' + totalVol + '</td>' +
        '<td class="td-sparkline">' + sparklineSvg + '</td>' +
        '</tr>';
    }

    tbody.innerHTML = rowsHtml;
  }

  async function loadMarketMatrix() {
    var errorEl = document.getElementById("market-matrix-error");
    var errorTextEl = document.getElementById("market-matrix-error-text");
    var updatedEl = document.getElementById("matrix-updated-time");
    var tbody = document.getElementById("market-matrix-tbody");
    var refreshBtn = document.getElementById("btn-refresh-matrix");

    if (errorEl) errorEl.style.display = "none";
    if (refreshBtn) refreshBtn.classList.add("loading");

    try {
      var data = await api("GET", "/market/matrix-10d");
      if (!data || !Array.isArray(data.items)) {
        throw new Error("Dữ liệu ma trận không hợp lệ");
      }
      renderMarketMatrix(data.items);
      if (updatedEl) {
        var timeStr = data.updated_at ? new Date(data.updated_at).toLocaleTimeString("vi-VN") : new Date().toLocaleTimeString("vi-VN");
        updatedEl.textContent = "Cập nhật: " + timeStr + " · " + (data.count || data.items.length) + " mã cổ phiếu";
      }
    } catch (err) {
      console.error("loadMarketMatrix error:", err);
      if (errorEl) {
        errorEl.style.display = "flex";
        if (errorTextEl) errorTextEl.textContent = "Lỗi tải ma trận thị trường: " + formatApiError(err);
      }
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="15" class="matrix-error-cell">Không thể tải dữ liệu ma trận. Vui lòng bấm "Làm mới" để thử lại.</td></tr>';
      }
    } finally {
      if (refreshBtn) refreshBtn.classList.remove("loading");
    }
  }

  function switchView(viewName) {
    var tabChat = document.getElementById("tab-nav-chat");
    var tabMarket = document.getElementById("tab-nav-market");
    var chatView = document.getElementById("chat-view");
    var marketMatrixView = document.getElementById("market-matrix-view");

    if (viewName === "market-matrix") {
      if (tabMarket) tabMarket.classList.add("active");
      if (tabChat) tabChat.classList.remove("active");
      if (chatView) chatView.style.display = "none";
      if (marketMatrixView) marketMatrixView.style.display = "flex";
      loadMarketMatrix().catch(function () {});
    } else {
      if (tabChat) tabChat.classList.add("active");
      if (tabMarket) tabMarket.classList.remove("active");
      if (chatView) chatView.style.display = "";
      if (marketMatrixView) marketMatrixView.style.display = "none";
    }
  }

  function initHeaderNav() {
    var tabChat = document.getElementById("tab-nav-chat");
    var tabMarket = document.getElementById("tab-nav-market");
    var refreshBtn = document.getElementById("btn-refresh-matrix");

    if (tabChat) {
      tabChat.addEventListener("click", function () {
        switchView("chat");
      });
    }
    if (tabMarket) {
      tabMarket.addEventListener("click", function () {
        switchView("market-matrix");
      });
    }
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        loadMarketMatrix().catch(function () {});
      });
    }
  }

  initTabs();
  initHints();
  initChartModal();
  initHeaderNav();
  renderTimeline([]);
  renderLiveGraphNodes([]);
  setGraphStatus("Sẵn sàng", "idle");
  setBoot("API=" + baseLabel + " · đang tải watchlist/market/approvals…");
  loadSessions(true).catch(function () {});
  
  if (typeof Promise.allSettled === 'function') {
    Promise.allSettled([loadWatchlist(), loadMarket(), loadApprovals()])
      .then(function (results) {
        var fails = 0;
        for (var i = 0; i < results.length; i++) {
          if (results[i].status === "rejected") fails++;
        }
        if (fails > 0) {
          setBoot("API=" + baseLabel + " · đã nối Backend (tải lỗi " + fails + "/3)", true);
        } else {
          setBoot("API=" + baseLabel + " · đã nối Backend");
        }
      });
  } else {
    // Fallback for older browsers
    var ps = [
      loadWatchlist().catch(function(e) { return e; }), 
      loadMarket().catch(function(e) { return e; }), 
      loadApprovals().catch(function(e) { return e; })
    ];
    Promise.all(ps).then(function(results) {
      var fails = results.filter(function(r) { return r instanceof Error; }).length;
      if (fails > 0) {
        setBoot("API=" + baseLabel + " · đã nối Backend (tải lỗi " + fails + "/3)", true);
      } else {
        setBoot("API=" + baseLabel + " · đã nối Backend");
      }
    });
  }

  /* --------------------------------------------------------------------------
     Phase 6: HITL Answer Evaluation & Feedback Toolbar
     -------------------------------------------------------------------------- */

  function showToast(message, type) {
    var container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    var toast = document.createElement("div");
    toast.className = "toast-message" + (type ? " toast-" + type : " toast-success");
    toast.innerHTML = (type === "error" ? "⚠️ " : "✅ ") + message;

    container.appendChild(toast);
    setTimeout(function () {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3600);
  }

  async function sendHitlFeedback(payload, container) {
    try {
      // Direct call to /hitl/feedback
      var res = await api("POST", "/hitl/feedback", payload);
      if (container) {
        var statusEl = container.querySelector(".hitl-feedback-status");
        if (statusEl) {
          statusEl.innerHTML = "✅ Cảm ơn bạn đã phản hồi!";
          statusEl.style.display = "inline-flex";
        }
        var formEl = container.querySelector(".hitl-feedback-form");
        if (formEl) formEl.style.display = "none";
        var expandBtn = container.querySelector(".btn-hitl-expand-text");
        if (expandBtn) expandBtn.style.display = "none";
      }
      showToast("Cảm ơn bạn đã phản hồi!", "success");
      return res;
    } catch (err) {
      console.error("sendHitlFeedback error:", err);
      showToast("Gửi đánh giá thất bại: " + formatApiError(err), "error");
      throw err;
    }
  }

  function createHitlFeedbackComponent(messageId, sessionId) {
    var container = document.createElement("div");
    container.className = "hitl-feedback-container";
    if (messageId) container.setAttribute("data-message-id", messageId);
    if (sessionId) container.setAttribute("data-session-id", sessionId);

    var currentVote = null;
    var currentRating = null;

    var toolbar = document.createElement("div");
    toolbar.className = "hitl-feedback-toolbar";

    var label = document.createElement("span");
    label.className = "hitl-feedback-label";
    label.textContent = "Đánh giá câu trả lời:";
    toolbar.appendChild(label);

    // Thumbs Up / Down
    var voteGroup = document.createElement("div");
    voteGroup.className = "hitl-vote-group";

    var btnUp = document.createElement("button");
    btnUp.type = "button";
    btnUp.className = "btn-hitl-vote btn-hitl-up";
    btnUp.title = "Hữu ích (Thumbs Up)";
    btnUp.innerHTML = "<span>👍</span>";

    var btnDown = document.createElement("button");
    btnDown.type = "button";
    btnDown.className = "btn-hitl-vote btn-hitl-down";
    btnDown.title = "Chưa tốt (Thumbs Down)";
    btnDown.innerHTML = "<span>👎</span>";

    voteGroup.appendChild(btnUp);
    voteGroup.appendChild(btnDown);
    toolbar.appendChild(voteGroup);

    // Star Rating (1..5)
    var starGroup = document.createElement("div");
    starGroup.className = "hitl-star-rating";
    starGroup.title = "Đánh giá 1 đến 5 sao";

    var stars = [];
    for (var s = 1; s <= 5; s++) {
      (function (starVal) {
        var starSpan = document.createElement("span");
        starSpan.className = "hitl-star";
        starSpan.setAttribute("data-star", String(starVal));
        starSpan.title = starVal + " sao";
        starSpan.textContent = "★";

        starSpan.addEventListener("mouseenter", function () {
          for (var j = 0; j < stars.length; j++) {
            stars[j].classList.toggle("hovered", j < starVal);
          }
        });

        starSpan.addEventListener("mouseleave", function () {
          for (var j = 0; j < stars.length; j++) {
            stars[j].classList.remove("hovered");
          }
        });

        starSpan.addEventListener("click", function () {
          currentRating = starVal;
          for (var j = 0; j < stars.length; j++) {
            stars[j].classList.toggle("active", j < starVal);
          }
          if (currentVote === null) {
            currentVote = starVal >= 3;
            btnUp.classList.toggle("active", currentVote);
            btnDown.classList.toggle("active", !currentVote);
          }
          var form = container.querySelector(".hitl-feedback-form");
          if (!form || form.style.display === "none") {
            sendHitlFeedback({
              message_id: messageId || "",
              session_id: sessionId || currentSessionId || "",
              is_positive: currentVote !== false,
              rating: currentRating,
            }, container).catch(function () {});
          }
        });

        stars.push(starSpan);
        starGroup.appendChild(starSpan);
      })(s);
    }
    toolbar.appendChild(starGroup);

    // Expand comment button
    var btnExpand = document.createElement("button");
    btnExpand.type = "button";
    btnExpand.className = "btn-hitl-expand-text";
    btnExpand.innerHTML = "<span>💬 Góp ý</span>";
    toolbar.appendChild(btnExpand);

    // Status display
    var statusSpan = document.createElement("span");
    statusSpan.className = "hitl-feedback-status";
    statusSpan.style.display = "none";
    toolbar.appendChild(statusSpan);

    container.appendChild(toolbar);

    // Feedback text form (collapsible)
    var form = document.createElement("div");
    form.className = "hitl-feedback-form";
    form.style.display = "none";

    // Reason selection dropdown (Phase 8)
    var reasonSelect = document.createElement("select");
    reasonSelect.className = "hitl-reason-select";
    var reasonOptions = [
      { val: "", text: "-- Chọn lý do (tùy chọn) --" },
      { val: "Sai số liệu giá", text: "Sai số liệu giá" },
      { val: "Tin tức không đúng", text: "Tin tức không đúng" },
      { val: "Sai biểu đồ", text: "Sai biểu đồ" },
      { val: "Thiếu ý", text: "Thiếu ý" },
      { val: "Khác", text: "Khác" },
    ];
    reasonOptions.forEach(function (opt) {
      var optEl = document.createElement("option");
      optEl.value = opt.val;
      optEl.textContent = opt.text;
      reasonSelect.appendChild(optEl);
    });

    var input = document.createElement("input");
    input.type = "text";
    input.className = "hitl-feedback-input";
    input.placeholder = "Góp ý chi tiết về câu trả lời này…";
    input.maxLength = 500;

    var btnSubmit = document.createElement("button");
    btnSubmit.type = "button";
    btnSubmit.className = "btn-hitl-submit";
    btnSubmit.textContent = "Gửi đánh giá";

    form.appendChild(reasonSelect);
    form.appendChild(input);
    form.appendChild(btnSubmit);
    container.appendChild(form);

    btnExpand.addEventListener("click", function () {
      var isHidden = form.style.display === "none";
      form.style.display = isHidden ? "flex" : "none";
      if (isHidden) input.focus();
    });

    btnUp.addEventListener("click", function () {
      currentVote = true;
      btnUp.classList.add("active");
      btnDown.classList.remove("active");
      if (currentRating === null) {
        currentRating = 5;
        for (var j = 0; j < stars.length; j++) {
          stars[j].classList.toggle("active", j < 5);
        }
      }
      var isFormOpen = form.style.display !== "none";
      if (!isFormOpen) {
        sendHitlFeedback({
          message_id: messageId || "",
          session_id: sessionId || currentSessionId || "",
          is_positive: true,
          rating: currentRating,
        }, container).catch(function () {});
      }
    });

    btnDown.addEventListener("click", function () {
      currentVote = false;
      btnDown.classList.add("active");
      btnUp.classList.remove("active");
      if (currentRating === null) {
        currentRating = 1;
        for (var j = 0; j < stars.length; j++) {
          stars[j].classList.toggle("active", j < 1);
        }
      }
      if (form.style.display === "none") {
        form.style.display = "flex";
        reasonSelect.focus();
      }
    });

    btnSubmit.addEventListener("click", function () {
      var text = input.value.trim();
      var selReason = reasonSelect.value || null;
      btnSubmit.disabled = true;
      sendHitlFeedback({
        message_id: messageId || "",
        session_id: sessionId || currentSessionId || "",
        is_positive: currentVote !== false,
        rating: currentRating || (currentVote === false ? 1 : 5),
        feedback_text: text || null,
        reason: selReason,
      }, container).finally(function () {
        btnSubmit.disabled = false;
      });
    });

    return container;
  }

  window.addEventListener("error", function (e) {
    console.error("Global error:", e.error || e.message);
    setBoot("Lỗi giao diện: " + (e.message || "Không rõ"), true);
  });
  window.addEventListener("unhandledrejection", function (e) {
    console.error("Unhandled rejection:", e.reason);
    setBoot("Lỗi hệ thống: " + (e.reason && e.reason.message ? e.reason.message : e.reason || "Không rõ"), true);
  });

  window.PW_showWatchlistError = showWatchlistError;
  window.PW_showApprovalsError = showApprovalsError;
  window.PW_openChartModal = openChartModal;
  window.PW_closeChartModal = closeChartModal;
  window.PW_switchView = switchView;
  window.PW_loadMarketMatrix = loadMarketMatrix;
  window.PW_renderMarketMatrix = renderMarketMatrix;
  window.PW_generateSparklineSvg = generateSparklineSvg;
  window.PW_sendHitlFeedback = sendHitlFeedback;
  window.PW_showToast = showToast;
  window.PW_createHitlFeedbackComponent = createHitlFeedbackComponent;
})();
