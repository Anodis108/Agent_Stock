# Product Spec — Portfolio Watch

## App Name
**Portfolio Watch — Multi-Agent Stock Assistant (Production LLMOps Edition)**

---

## App Goal

Xây dựng ứng dụng web MVP giúp theo dõi và phân tích cổ phiếu Việt Nam qua **Multi-Agent Swarm**, đồng thời áp dụng quy trình **Production LLMOps** (Module III — *LLM-Engineer-Handbook/module-3-production-llmops.md*).

**Một câu:** Người dùng chat hỏi về cổ phiếu VN và nhận câu trả lời streaming; kỹ sư vận hành hệ thống an toàn, đo được chất lượng, và cải tiến qua prompt/eval — không qua train model.

> **Chú thích (Handbook M3):** Vòng lặp chính là `prompt/dataset version → evaluate → deploy → monitor → feedback`. Artifact quan trọng: **prompt + config + eval set**.

**Hai mục tiêu song song:**

| | End user | LLMOps (M3) |
| :--- | :--- | :--- |
| **Làm gì** | Tra cứu giá, tin, biểu đồ; hỏi nối tiếp theo ngữ cảnh | Version prompt, eval gate, cost/cache, CI/CD, observability |
| **Thành công khi** | Chat nhanh, đúng dữ liệu VN, an toàn | Biết version đang chạy; PR xấu bị chặn; rollback được |

---

## Target Users

### 1. Nhà đầu tư cá nhân
- Tra cứu giá, biến động 10 phiên, tin tức, biểu đồ cổ phiếu VN.
- Chat streaming; hỏi tiếp không cần nhắc lại mã (*"FPT tăng hay giảm?"* → *"Tại sao lại giảm?"*).
- Xem bảng Market Watch 10D; gửi phản hồi 👍/👎 dưới mỗi câu trả lời.

### 2. Kỹ sư AI / LLMOps
- Vận hành swarm agents, prompt registry, eval pipeline, deploy demo.
- Theo dõi Live Swarm Inspector, cost, trace sampling.
- Rollback nhanh: **image tag**, **prompt alias**, hoặc **model config**.

> **Chú thích:** Sửa code → unit test; sửa prompt/model → eval gate trước khi merge.

---

## Core User Flow

### Luồng người dùng (End User)

1. Mở app — `http://localhost:3000` (Docker) hoặc `http://localhost:8000` (local).
2. **Turn 1** — Nhập câu hỏi (vd. *"FPT hôm nay tăng hay giảm?"*).
   - Guardrail kiểm tra an toàn → supervisor điều phối price/news/chart → composer stream câu trả lời từng token (SSE).
   - Live Inspector hiển thị node đang chạy và thời gian xử lý.
3. **Turn 2** — Hỏi nối tiếp (vd. *"Tại sao lại giảm?"*).
   - Hệ thống đọc session, kế thừa mã cổ phiếu, trả lời theo ngữ cảnh.
4. **Yêu cầu biểu đồ** — *"Vẽ biểu đồ FPT 10 phiên"* → ảnh hiện trong chat.
5. **Market Watch** — Tab ma trận 10 mã × 10 phiên; số liệu khớp với chat.
6. **Phản hồi HITL** — 👍/👎; feedback lưu để cải thiện golden dataset sau.

### Luồng từ chối (Edge Cases)

- Câu ngoài phạm vi (AAPL, thời tiết, tư vấn mua bán) → guardrail từ chối lịch sự.
- Prompt injection → guardrail chặn ngay, không gọi worker agents.

### Luồng vận hành (LLMOps — M3)

```
Sửa prompt/code → PR → lint + pytest → eval subset (gate) → merge
→ deploy (Docker/ngrok) → monitor + HITL → thêm case vào golden set
```

---

## Features In Scope

### A. Tính năng sản phẩm (đã có / duy trì)

| # | Tính năng | Mô tả ngắn |
| :---: | :--- | :--- |
| 1 | Chat SSE streaming | Câu trả lời chạy từng token; Inspector realtime |
| 2 | Multi-Agent Swarm | guardrail → rewrite → supervisor → price/news/chart → composer |
| 3 | Guardrails | Chặn injection & out-of-scope (fail-closed) |
| 4 | Session memory | Hỏi nối tiếp Turn 1 → Turn 2 |
| 5 | Chart agent | Biểu đồ giá lưu `resources/data/charts/` |
| 6 | Market Watch 10D | Ma trận giá; đồng bộ với chat |
| 7 | HITL feedback | Telemetry JSON tại `resources/data/hitl_feedback.json` |
| 8 | Docker 2-container | Frontend :3000 + Backend :8000 |

### B. Tính năng LLMOps (M3 — cần hoàn thiện)

| # | Tính năng | Handbook | MVP |
| :---: | :--- | :---: | :--- |
| 1 | Prompt registry git-based | M3-B1 | Version + `production.txt` + lint |
| 2 | Eval pipeline + gate | M3-B2 | 40 cases golden v5; subset 20 cho PR; gate theo slice |
| 3 | Cost tracking + cache 2 tầng | M3-B3 | Exact cache + semantic đơn giản; key có `prompt_version` |
| 4 | SSE/Docker hardening | M3-B4 | Disconnect stop, retry 429, benchmark latency |
| 5 | Deploy demo | M3-B5 | ngrok public URL + smoke test (GCP tùy chọn) |
| 6 | CI/CD eval gate | M3-B6 | GitHub Actions: lint → pytest → eval subset |
| 7 | Observability | M3-B7 | Trace sampling, cost log, 1 incident playbook |
| 8 | Capstone feedback loop | M3-B8 | HITL → draft golden case; pipeline diagram |

> **Chú thích trạng thái:** Chat/Docker/guardrail/eval cơ bản **đã có**. Cache, CI/CD, eval gate, cost dashboard **chưa có** — triển khai theo `implementation-plan.md`.

---

## Features Out of Scope

Giữ MVP đơn giản — **không** làm trong chu kỳ này:

1. **Đặt lệnh giao dịch thực** — không tích hợp broker.
2. **Streaming giá tick-by-tick** — chỉ dữ liệu nến ngày 1D.
3. **OAuth2 / RBAC / thanh toán** — single-user demo.
4. **Self-host vLLM/TGI production** — dùng API provider; vLLM chỉ mở rộng.
5. **Fine-tuning LoRA** — nhánh tách biệt, không thuộc đường chính M3.
6. **Visual Graph Builder** — chỉnh workflow qua code/spec.
7. **Redis / infra cache nặng** — MVP dùng in-memory hoặc SQLite.

---

## Acceptance Criteria

Tiêu chí nghiệm thu MVP — pass khi **tất cả** mục dưới đạt:

### Sản phẩm (End User)

1. Chat SSE hoạt động; Inspector hiển thị node và latency.
2. Turn 2 kế thừa đúng mã cổ phiếu từ Turn 1.
3. Injection và out-of-scope bị chặn 100% (không trả giá bịa).
4. Chart sinh ảnh hợp lệ; Market Watch 10D khớp số liệu chat.
5. HITL lưu feedback vào `resources/data/hitl_feedback.json`.
6. `docker compose up --build` chạy ổn định; UI tại `:3000`, API tại `:8000`.

### LLMOps (Module III)

7. **Prompt:** Không hardcode prompt trong agents; ≥ 2 prompt có ≥ 2 version + changelog; đổi production chỉ sửa `production.txt`.
8. **Eval:** Golden v5 (40 cases) overall ≥ 85%; slices `injection` và `out_of_scope` = 100%; report có `by_slice` và liệt kê case fail.
9. **Gate:** `eval.gate` exit 1 khi slice injection tụt (đã chứng minh bằng test cố ý).
10. **Cost/Cache:** Có baseline cost; cache key chứa `prompt_version`; có báo cáo trước/sau.
11. **Deploy:** Public demo URL (ngrok) + smoke pass; không commit API key.
12. **CI:** Workflow chạy lint + pytest + eval subset trên PR đổi prompt/agent.
13. **Observability:** Trace sampling + cost ghi kèm `prompt_version`; ≥ 1 playbook incident đã diễn tập.
14. **Capstone:** Pipeline diagram khớp thực tế; ≥ 1 HITL case chuyển thành golden draft; rollback 1 trục đã thử.

### Kiểm thử tổng hợp

```bash
pytest tests/ -v
python -m backend.eval.run_detailed
python -m backend.eval.gate --run <report.json>   # sau Phase 2
docker compose up --build -d
```

Dẫn chứng eval: `specs/eval/eval_results_golden_v5.md`, `specs/eval/v5_baseline.json`.
