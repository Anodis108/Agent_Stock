# Báo cáo kiểm thử — `tests/QUESTIONS.agent_pr.md`

**Ngày chạy:** 2026-09-03
**Môi trường:** `http://localhost:8000` — gọi thật qua `POST /pr/ask`, `/pr/price`, `/pr/approve`, `/pr/ask/evaluate`, không mock, script `tests/run_agent_pr_questions.py`.
**Số câu chạy:** 5 lời gọi (mục 1–5, 9–18; SKIP mục 6–8 — chưa build).
**Tổng thời gian API:** 40.2s (~0.7 phút).
**Log chi tiết:** `tests/.run/log.jsonl`

---

## 1. Tóm tắt nhanh

| Chỉ số | Kết quả |
|---|---|
| Tổng số lời gọi | 5 |
| HTTP 200 | 0 |
| HTTP 400 (guardrail chặn) | 0 |
| HTTP 422 (validate / thiếu thread_id / input rỗng) | 0 |
| SKIP (chưa build / quan sát tay) | 0 |
| Exception mạng/timeout | 0 |
| HTTP khác (KHÔNG mong muốn — cần soát) | 5 |
| Ask 200 có dòng `Token:` trong trace | 0/0 |

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Viết 2-4 câu đánh giá tổng quan ở đây (so với lần chạy trước nếu có).

## 2. Bug và vấn đề tìm thấy (xếp theo mức độ nghiêm trọng)

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Dùng ký hiệu 🟠 Đáng kể / 🟡 Trung bình / 🟢 Nhỏ. Mỗi bug: **Câu tái hiện**, **Hiện tượng**, **So với spec**, **Đề xuất sửa** — xem `copy_REPORT.agent_pr_questions.md` mục 2 làm mẫu định dạng.

## 3. Bug đã xác nhận FIX so với lần chạy trước

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Đối chiếu với `copy_REPORT.agent_pr_questions.md` mục 3 — bug nào từng ghi nhận, giờ còn không.

## 4. Mục không test được — tính năng chưa build

- **Mục 6:** DocumentAgent / PDF BCTC — chưa có trong app/agent_pr
- **Mục 7:** Swarm dị chủng Scout/Render/Api/Stealth — chưa build
- **Mục 8:** ContentRouter + Sink Router 2 tầng độc lập — chưa build
- **15.4 / 15.5:** LangFuse — đối chiếu UI khi `MONITORING_ENABLED=true`, không assert trong script.

## 5. Long-term memory

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Xác nhận Qdrant thật (không fallback in-memory) — đối chiếu câu 11.alice1–4, 11.bob, 11.nouser* trong phụ lục mục 11.

## 6. Những gì hoạt động đúng (xác nhận bằng dữ liệu thật)

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Bảng | Hạng mục | Bằng chứng | — liệt kê tối thiểu: cache trong phiên, HITL đúng luồng, guardrail chặn injection đúng/không chặn nhầm, subset worker theo câu hỏi, HTTP 422 đúng spec.

## 7. Thay đổi hạ tầng thực hiện trong lần chạy này

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Ghi các thay đổi docker-compose/.env/config nếu có thực hiện trong lần chạy này (nếu không có thì ghi "Không có").

## 8. Danh sách đầy đủ theo mục (tóm tắt kết quả)

| Mục | Tiêu đề | Số câu chạy | HTTP 200 | 400/422 | SKIP/EXC |
|---|---|---|---|---|---|
| 1 | Supervisor — parse ticker / routing | 5 | 0 | 0 | 0 |

## 9. Khuyến nghị ưu tiên sửa

> **TODO (Claude điền sau khi đọc `tests/.run/log.jsonl` thật):** phần này cần đọc hiểu + diễn giải kết quả, script không tự sinh chính xác được. Chạy xong thì nhờ Claude đọc log và viết lại phần này.
> Danh sách đánh số, [Ưu tiên cao/trung bình/thấp], bám theo bug ở mục 2.

## 10. Ghi chú phương pháp

- Dữ liệu test dùng key OpenAI thật, không mock — chi phí LLM thật đã phát sinh.
- Cache trong phiên / DB đã có dữ liệu từ câu trước cùng lần chạy là hành vi cache đúng thiết kế, không phải bug.
- Script bám `QUESTIONS.agent_pr.md` mục 1–5, 9–18 + bộ demo §16 + probe §18 (db_write code-enforced / idempotency / memory / Token trace) từ `STUDY_PLAN.agent_pr.html`.
- Log chi tiết từng câu (request/response đầy đủ, JSONL): `tests/.run/log.jsonl` (scratch, không commit — có thể chạy lại `python tests/run_agent_pr_questions.py` để tái tạo).

---

## 11. Phụ lục — câu trả lời đầy đủ từng câu hỏi

Toàn bộ câu trả lời thật của agent (không rút gọn), lấy trực tiếp từ log JSONL. Trace gấp gọn trong `<details>`.

### Mục 1 — Supervisor — parse ticker / routing

**1.1**

**Câu hỏi:** 'Tại sao giá HPG giảm hôm nay?'
`thread_id=run-1.1-18b75c` — HTTP 503 (8.95s)

> Không lấy được dữ liệu: database disk image is malformed

*Expect:* Price+News+DB→Eval→final_answer

---

**1.2**

**Câu hỏi:** 'Tại sao HPG giảm?'
`thread_id=run-1.2-b2b8d0` — HTTP 503 (7.73s)

> Không lấy được dữ liệu: database disk image is malformed

---

**1.3**

**Câu hỏi:** 'HPG hôm nay thế nào?'
`thread_id=run-1.3-4f3783` — HTTP 503 (8.8s)

> Không lấy được dữ liệu: database disk image is malformed

---

**1.4**

**Câu hỏi:** 'Hòa Phát hôm nay giảm vì sao?'
`thread_id=run-1.4-d989e5` — HTTP 503 (7.85s)

> Không lấy được dữ liệu: database disk image is malformed

*Expect:* Tên công ty → HPG

---

**1.5**

**Câu hỏi:** 'Vinamilk đang ra sao?'
`thread_id=run-1.5-97ed02` — HTTP 503 (6.91s)

> Không lấy được dữ liệu: database disk image is malformed

*Expect:* → VNM

---
