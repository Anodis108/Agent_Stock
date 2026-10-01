/**
 * Frontend config — gọi cùng origin khi app gộp (Phase 2).
 *
 * Mặc định "" = same-origin (uvicorn backend.main phục vụ UI + API).
 * Override tạm: ?backend=http://127.0.0.1:8000
 * Tách FE :5173 (V2): set BACKEND_BASE_URL = "http://127.0.0.1:8000"
 */
window.PW_CONFIG = {
  BACKEND_BASE_URL: "",
  /** Timeout gọi Backend (ms) — tránh treo khi AI/Backend chậm hoặc down. */
  REQUEST_TIMEOUT_MS: 90000,
};

/**
 * @returns {string} base URL Backend (không dấu / cuối); "" = same origin
 */
window.PW_getBackendBaseUrl = function PW_getBackendBaseUrl() {
  var fromQuery = null;
  try {
    var q = new URLSearchParams(window.location.search || "");
    fromQuery = q.get("backend") || q.get("BACKEND_BASE_URL");
  } catch (_e) {
    fromQuery = null;
  }
  if (fromQuery != null && String(fromQuery).trim() !== "") {
    return String(fromQuery).trim().replace(/\/+$/, "");
  }
  var cfg =
    window.PW_CONFIG && window.PW_CONFIG.BACKEND_BASE_URL !== undefined
      ? window.PW_CONFIG.BACKEND_BASE_URL
      : "";
  return String(cfg == null ? "" : cfg).replace(/\/+$/, "");
};
