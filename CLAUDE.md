# Coding Rules

- **Superpowers:** Mọi task sửa/viết code trong repo này → tuân `.cursor/rules/superpowers-coding.mdc` và plugin skill `using-superpowers` (announce skill trước khi implement).
- Viết code đơn giản, ngắn gọn, dễ đọc.
- Không tách hàm nhỏ lẻ khi không cần thiết — giữ logic liền mạch trong một hàm nếu nó không quá dài hoặc phức tạp.
- Tránh trừu tượng hóa (abstraction) không cần thiết khi task không yêu cầu.
- Không bao giờ dùng `.get(...)` trên dict / state / context — code luôn đảm bảo key tồn tại, truy cập thẳng `x["key"]` (key có thể chưa được node nào ghi thì khởi tạo mặc định ở điểm vào, vd. `None`).
  Ngoại lệ — dữ liệu ngoài code kiểm soát vẫn dùng `.get`: biến môi trường, header HTTP, JSON từ LLM / dataset eval / YAML prompt, payload Qdrant / Redis, dữ liệu vnstock, contextvar có thể rỗng, và chuỗi key thay thế kiểu `h.get("symbol") or h.get("ticker")`.
- Không bao giờ tự tạo / fix cứng định danh (`user_id`, `request_id`, `thread_id`, `session_id`, …): không mặc định `"default"`, không `x or "default"`, không tự sinh UUID giữa đường. Định danh phải lấy đúng giá trị được truyền vào; thiếu / rỗng → báo lỗi request (HTTP 400/422, hoặc raise ở tầng trong). Tham số định danh luôn bắt buộc (không có giá trị mặc định).
  Ngoại lệ: `request_id` chỉ được sinh 1 lần ở điểm vào hệ thống rồi truyền xuyên suốt — web backend (CorrelationIdMiddleware, khi frontend chưa gửi), job quét định kỳ, eval; AI backend không tự sinh; khoá chính khi tạo bản ghi mới (message / session / holding …), tên file ảnh, tool_call id, correlation id của middleware được tự sinh.

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
