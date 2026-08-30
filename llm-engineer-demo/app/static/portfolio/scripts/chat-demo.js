// AI Demo — gọi backend FastAPI (vn-stock-swarm/llm-engineer-demo) qua endpoint POST /chat.
(() => {
    const STORAGE_KEY = 'demoBackendUrl';

    const urlInput = document.getElementById('backend-url');
    const statusEl = document.getElementById('backend-status');
    const messagesEl = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');

    if (!form || !urlInput) return;

    // Trang này được chính backend serve (app/static/portfolio) → mặc định gọi
    // same-origin, không cần chỉnh URL khi demo. Vẫn cho override qua input/localStorage
    // để dùng lại được cả khi mở trang này tách rời (file:// hoặc host khác).
    urlInput.value = window.location.origin;
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) urlInput.value = saved;
    } catch (e) {
        // localStorage có thể bị chặn (private mode) — bỏ qua, dùng giá trị mặc định.
    }

    function getBaseUrl() {
        return urlInput.value.trim().replace(/\/+$/, '');
    }

    function addMessage(text, kind) {
        const el = document.createElement('div');
        el.className = `chat-message chat-message-${kind}`;
        el.textContent = text;
        messagesEl.appendChild(el);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return el;
    }

    async function checkHealth() {
        const baseUrl = getBaseUrl();
        if (!baseUrl) return;
        statusEl.textContent = '● Đang kiểm tra...';
        statusEl.className = 'backend-status';
        try {
            const res = await fetch(`${baseUrl}/health`, { method: 'GET' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            statusEl.textContent = `● Online (${data.model || data.app || 'ok'})`;
            statusEl.className = 'backend-status online';
        } catch (err) {
            statusEl.textContent = '● Offline / không kết nối được';
            statusEl.className = 'backend-status offline';
        }
    }

    urlInput.addEventListener('change', () => {
        try {
            localStorage.setItem(STORAGE_KEY, urlInput.value.trim());
        } catch (e) {
            // ignore
        }
        checkHealth();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = input.value.trim();
        if (!question) return;

        const baseUrl = getBaseUrl();
        if (!baseUrl) {
            addMessage('Vui lòng nhập Backend URL trước.', 'error');
            return;
        }

        addMessage(question, 'user');
        input.value = '';
        sendBtn.disabled = true;
        const thinkingEl = addMessage('Đang suy nghĩ...', 'bot');

        try {
            const res = await fetch(`${baseUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
            });

            if (!res.ok) {
                const errBody = await res.json().catch(() => ({}));
                throw new Error(errBody.reason || errBody.detail || `HTTP ${res.status}`);
            }

            const data = await res.json();
            thinkingEl.textContent = data.answer || '(không có câu trả lời)';
        } catch (err) {
            thinkingEl.remove();
            addMessage(
                `Lỗi khi gọi backend: ${err.message}. Kiểm tra backend đã chạy (uvicorn app.main:app --reload) và CORS đã bật.`,
                'error'
            );
        } finally {
            sendBtn.disabled = false;
        }
    });

    checkHealth();
})();
