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

  /** Chuẩn hoá steps[] theo contract Backend: {id,name,status,detail?,input?,output?} */
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
      detailEl.textContent = step.detail ? "Chi tiết: " + step.detail : "";
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
      card.innerHTML =
        '<span class="node-icon">' + icon + '</span>' +
        '<span class="node-label">' + (step.name || "?") + '</span>' +
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
          detail: s.detail,
          input: s.input,
          output: s.output,
        };
      });
      renderLiveGraphNodes(animState);

      var currentIdx = 0;
      var stepDuration = 220; // ms per step highlight

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
            setGraphStatus(hasErr ? "Có lỗi" : "Hoàn tất", hasErr ? "error" : "done");
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

  function appendChat(role, text, diagram) {
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
    setBoot("Đang chờ câu trả lời cuối từ Backend…");
    try {
      var data = await api("POST", "/chat", {
        question: question,
        user_id: USER_ID,
      });
      var answer = extractFinalAnswer(data);
      var diagram = data.diagram || (data.result && data.result.diagram);
      appendChat(
        "assistant",
        answer || "(không có câu trả lời cuối từ Backend)",
        diagram
      );
      await applyTimelineFromBackend(data);
      setBoot(
        "Đã nhận câu trả lời cuối" +
          (data && data.run_id ? " · run_id=" + data.run_id : "")
      );
    } catch (err) {
      removeThinking();
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

  initTabs();
  initHints();
  renderTimeline([]);
  renderLiveGraphNodes([]);
  setGraphStatus("Sẵn sàng", "idle");
  setBoot("API=" + baseLabel + " · đang tải watchlist/market/approvals…");
  
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
})();
