# Agents trong hệ thống

Mô tả từng agent: vai trò, có dùng LLM hay không, input/output, tool. Tham
chiếu chi tiết luồng dữ liệu: `../portfolio-watch-agent-explained.md`.
Nguồn code kỹ thuật tương ứng để tận dụng lại ở `../../llm-engineer-demo`
được ghi chú ở mỗi mục.

## Sơ đồ quan hệ (tóm tắt)

```
3 lối vào: Cron / API quét ngay / Chat API
        │
        ├── nhánh giám sát: Orchestrator → PriceAgent + NewsAgent (song song)
        │       → EventClassifier → (bình thường: dừng) hoặc (bất thường: EvalAgent)
        │       → EvalAgent → SynthesisAgent → Guardrail → Confidence Gate
        │       → gửi thẳng HOẶC HITL Gate 1 → gửi
        │
        └── nhánh hỏi-đáp: RewriteQuestion → Supervisor → (PriceAgent/NewsAgent)
                → [EvalAgent nếu cần] → AnswerComposer → Guardrail → trả lời
```

Watchlist/threshold thay đổi luôn đi qua HITL Gate 2 (không có đường tắt).

## Orchestrator (giám sát)

- **Loại:** hàm điều phối thuần (không LLM) — đọc watchlist, lặp song song
  theo từng mã, gọi PriceAgent + NewsAgent.
- **Input:** danh sách mã trong watchlist của user (hoặc 1 mã, khi gọi qua
  API "Quét ngay").
- **Output:** kết quả giá + tin theo từng mã, chuyển tiếp cho EventClassifier.
- **Tham khảo:** hierarchical.py (`llm-engineer-demo/app/agent_m2/multi_agent`)
  cho cách một node trung tâm gọi song song nhiều worker.

## PriceAgent

- **Loại:** hàm thuần, KHÔNG cần LLM.
- **Input:** symbol.
- **Tool:** `fetch_latest_close(symbol)`.
- **Output:** giá đóng cửa mới nhất + % thay đổi so với phiên trước.
- **Ghi chú:** deterministic — không cần prompt, không cần eval chất lượng LLM.

## NewsAgent

- **Loại:** ReAct, có LLM (vòng lặp LLM ⇄ tool).
- **Input:** symbol + khung thời gian.
- **Tool:** `fetch_cafef_news(symbol)`.
- **Luồng:** LLM chọn từ khóa tìm → gọi tool → LLM tự đánh giá đã đủ tin chưa
  → lặp lại nếu cần → khi đủ, lọc ra tin thực sự liên quan đến mã đó.
- **Output:** danh sách tin đã lọc, liên quan tới symbol.
- **Tham khảo:** vòng lặp ReAct trong `app/agent/nodes.py` (agent_node +
  should_continue) của llm-backend-ref hiện tại — tái dùng cơ chế bind_tools +
  tool loop, không tái dùng domain logic.

## Event Classifier

- **Loại:** LLM, quyết định nhị phân (RoutingDecision).
- **Input:** kết quả PriceAgent + NewsAgent.
- **Output:** `bình thường` (kết thúc, chỉ log, không tốn thêm LLM call) hoặc
  `bất thường` (đi tiếp EvalAgent).
- **Ghi chú:** đây là bước lọc rẻ tiền để tránh gọi EvalAgent/SynthesisAgent
  (tốn kém hơn) cho mọi mã ở mọi lần quét.

## EvalAgent

- **Loại:** ReAct, có LLM. Dùng chung cho cả nhánh giám sát và nhánh hỏi-đáp
  (khi câu hỏi cần giải thích/so sánh).
- **Input:** dữ liệu sự kiện (giá + tin) cần đánh giá.
- **Tool:** `read_price_history(symbol)` — đọc lịch sử giá khi cần thêm căn cứ.
- **Output:** `Severity { level, confidence, reasoning, evidence }`. Có thể
  kèm đề xuất đổi ngưỡng/thêm mã liên quan vào watchlist (đi qua HITL Gate 2).
- **Tham khảo:** `llm-engineer-demo/app/agent/nodes.py` (CRAG, đánh giá độ liên
  quan) cho pattern "LLM tự quyết định có cần gọi thêm tool hay không".

## SynthesisAgent

- **Loại:** LLM, chỉ dùng ở nhánh giám sát.
- **Input:** `Severity` từ EvalAgent.
- **Tool:** `read_user_memory(user_id)` — đọc sở thích người dùng.
- **Luồng:** chọn model theo độ phức tạp sự kiện (model routing) → soạn nội
  dung cảnh báo → qua Guardrail Output → nếu vi phạm, quay lại soạn lại.
- **Output:** `FinalAlert` draft (đã qua guardrail).
- **Tham khảo:** `llm-engineer-demo/app/optimization/routed/routing.py` (model
  routing theo độ phức tạp) và `app/guardrails/checks.py`.

## Guardrail Output

- **Loại:** kiểm tra không dùng LLM (rule-based) + tùy chọn LLM injection
  check, tái dùng ý tưởng từ `llm-engineer-demo/app/guardrails`.
- **Kiểm tra:** không đưa lời khuyên mua/bán chắc chắn; nội dung khớp với
  evidence thật (không bịa số liệu).
- **Áp dụng:** cả nhánh giám sát (sau SynthesisAgent) và nhánh hỏi-đáp (sau
  AnswerComposer).

## Confidence Gate + HITL Gate 1

- **Loại:** logic điều kiện thuần, không LLM.
- **Điều kiện:** độ tin cậy cao VÀ khớp đúng ngưỡng user đã đặt → gửi tự động
  (email/push), không cần duyệt — giữ giá trị cảnh báo real-time.
- **Ngược lại:** vào HITL Gate 1, chờ người dùng duyệt. Approve → gửi.
  Reject → ghi lý do vào Memory (học lại ngưỡng cho lần sau).

## HITL Gate 2 (đổi cấu hình watchlist)

- **Loại:** luôn cần duyệt, không có đường tắt (khác Gate 1) — vì đây là
  thay đổi cấu hình lâu dài, không phải một cảnh báo đơn lẻ.
- **Input:** đề xuất đổi ngưỡng/thêm mã liên quan từ EvalAgent.
- **Output:** approve → ghi đè Watchlist Store; reject → ghi lý do, giữ nguyên.

## Supervisor / RewriteQuestion (nhánh hỏi-đáp)

- **Loại:** LLM.
- **RewriteQuestion:** chuẩn hoá câu hỏi tự do, dùng lịch sử hội thoại (Memory).
- **Supervisor RoutingDecision:** quyết định câu hỏi cần agent nào (tái sử
  dụng PriceAgent/NewsAgent, gọi song song đúng những agent cần thiết).
- **Tham khảo:** `hierarchical.py` (Supervisor pattern) trong
  `llm-engineer-demo/app/agent_m2/multi_agent`.

## AnswerComposer (nhánh hỏi-đáp)

- **Loại:** LLM, có model routing + (tùy chọn) prompt A/B.
- **Input:** kết quả gộp từ các worker (+ output EvalAgent nếu câu hỏi cần
  giải thích/so sánh), Memory (hội thoại cũ).
- **Output:** câu trả lời, qua Guardrail Output rồi trả thẳng cho user — nhánh
  này KHÔNG qua HITL vì chỉ cung cấp thông tin, không có tác dụng phụ ra
  ngoài (không gửi email/thay đổi cấu hình).
- **Sau khi trả lời:** lưu hội thoại vào Memory cho lượt hỏi sau.

## Kho dữ liệu dùng chung

- **Watchlist Store:** mã + ngưỡng cảnh báo theo user.
- **Price History DB:** lịch sử giá, đọc bởi EvalAgent.
- **Memory Store:** preferences, lịch sử cảnh báo, hội thoại — đọc/ghi bởi
  SynthesisAgent, AnswerComposer, và cả 2 HITL Gate khi reject.
