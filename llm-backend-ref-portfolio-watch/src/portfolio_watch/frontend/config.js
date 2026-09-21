/**
 * Frontend config — chỉ nói chuyện với Backend (không gọi AI trực tiếp).
 *
 * Đổi URL mặc định tại đây, hoặc override tạm:
 *   http://127.0.0.1:5173/?backend=http://127.0.0.1:8000
 */
window.PW_CONFIG = {
  BACKEND_BASE_URL: "http://127.0.0.1:8000",
  /** Timeout gọi Backend (ms) — tránh treo khi AI/Backend chậm hoặc down. */
  REQUEST_TIMEOUT_MS: 90000,
};

/**
 * @returns {string} base URL Backend (không dấu / cuối)
 */
window.PW_getBackendBaseUrl = function PW_getBackendBaseUrl() {
  var fromQuery = null;
  try {
    var q = new URLSearchParams(window.location.search || "");
    fromQuery = q.get("backend") || q.get("BACKEND_BASE_URL");
  } catch (_e) {
    fromQuery = null;
  }
  var raw =
    (fromQuery && String(fromQuery).trim()) ||
    (window.PW_CONFIG && window.PW_CONFIG.BACKEND_BASE_URL) ||
    "http://127.0.0.1:8000";
  return String(raw).replace(/\/+$/, "");
};
