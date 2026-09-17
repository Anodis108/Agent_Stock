# Change Log

Nhật ký thay đổi theo thời gian cho project Portfolio Watch & Chat Agent.
Ghi theo ngày, mới nhất ở trên.

## 2026-09-17 — Review quyết định Docker / đóng Phase 7 vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục cuối ↔ demo packaging / 1 URL):**
- Image base `python:3.12-slim`; tag `portfolio-watch:demo`.
- Port container **8000**; host `${APP_HOST_PORT:-8000}`.
- Volume `portfolio-watch-sqlite` → `/app/data` (`SQLITE_PATH=…/portfolio_watch.db`).
- `env_file: .env`; demo URL cùng origin `http://localhost:8000/`.
- Ngày đóng Phase 7: **2026-09-17**; bảng phase 1–7 đủ ngày; checklist `[x]`.

**Fails:** không có thiếu sót so với checklist mục này (sau khi sửa assert
test không còn yêu cầu placeholder `*(chưa)*` toàn file).

**Missing:** không còn mục unchecked trong `implementation-plan.md`.

## 2026-09-17 — Phase 7 hoàn thành: quyết định Docker + ngày đóng phase

**Ngày hoàn thành Phase 7:** **2026-09-17**

### Quyết định Docker (demo packaging)

| Mục | Quyết định | Lý do ngắn |
|-----|------------|------------|
| Image base | `python:3.12-slim` | Khớp runtime local ≥3.10; slim đủ cho FastAPI + deps |
| Image tag | `portfolio-watch:demo` (compose `build: .`) | Một service app; không multi-stage |
| Container port | **8000** (`EXPOSE` + uvicorn `--port 8000`) | Cùng cổng local / product demo |
| Host port | `${APP_HOST_PORT:-8000}:8000` (biến `APP_HOST_PORT`) | Đổi cổng host qua `.env`, không đổi image |
| Volume name | `portfolio-watch-sqlite` (compose key `pw_sqlite`) | Named volume — SQLite sống qua `restart` / `down` |
| Volume path | host volume → `/app/data` | `SQLITE_PATH=/app/data/portfolio_watch.db` |
| Env / secrets | `env_file: .env`; không bake key vào image | Compose override `API_HOST` / `SQLITE_PATH` trong container |
| Demo URL | `http://localhost:8000/` (API + `web/` cùng origin) | Một URL; `API_BASE=""` |

Bảng phase (mục “Ngày hoàn thành từng phase”) cập nhật Phase 7 = **2026-09-17**.
Checklist Phase 7 trong `implementation-plan.md` toàn `[x]`.

**Liên kết AC:** `scripts/verify_clean_docker.py` → `CLEAN_DOCKER_SMOKE_OK`
(3 luồng qua cùng API UI dùng).

## 2026-09-17 — Review Docker 3-luồng máy sạch vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 xác nhận máy sạch ↔ AC 3 luồng / demo 1 URL):**
- `docker compose up --build` → health + UI (`chat`/`watchlist`/`approvals`).
- Quét: `POST /scan` FPT (giá thật, route bình thường).
- Chat: `POST /chat` không HITL, có `answer`.
- HITL: approve → `sent`; reject + `reject_reason` ghi lại.
- Script `scripts/verify_clean_docker.py` → `CLEAN_DOCKER_SMOKE_OK` (đã chạy thật).

**Fails (liên quan feature, đã sửa):**
- Seed HITL dùng ID cố định `docker-a1` trên volume còn resolution cũ →
  `list_pending` rỗng → đổi seed sang UUID mỗi lần chạy.
- `subprocess` capture compose log Windows cp1252 → `encoding=utf-8`,
  `errors=replace`.

**Missing (đúng kỳ vọng — mục Phase 7 cuối):**
- Ghi quyết định Docker (port/volume/base) + ngày đóng Phase 7.

## 2026-09-17 — Phase 7: xác nhận Docker Compose chạy 3 luồng

- `scripts/verify_clean_docker.py`: compose up --build, UI + scan/chat/HITL.
- README § Demo Docker mục 4; `tests/test_clean_docker_smoke.py`.
- Chạy thật trên máy này → `CLEAN_DOCKER_SMOKE_OK`.

## 2026-09-17 — Review README Demo bằng Docker vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục README Docker ↔ demo 1 URL / 3 luồng):**
- Yêu cầu Docker + Compose; `cp`/Copy-Item `.env.example` → `.env`.
- `docker compose up --build`; mở http://localhost:8000/ (UI+API).
- `logs -f`, `down`, `down -v` (reset volume `portfolio-watch-sqlite`).

**Fails:** không có thiếu sót so với checklist mục này.

**Missing (đúng kỳ vọng — Phase 7 tiếp):**
- Xác nhận máy sạch `compose up` + 3 luồng UI.
- Ghi quyết định Docker (port/volume/base) + ngày đóng Phase 7.

## 2026-09-17 — Phase 7: mục README "Demo bằng Docker"

- Thêm section hướng dẫn: yêu cầu, `.env`, `up --build`, URL, dừng/log/reset.
- `tests/test_readme_docker_demo.py`.

## 2026-09-17 — Review single-URL API+web in container vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 — 1 URL demo ↔ product-spec Frontend cùng origin):**
- `GET /` UI (chat/watchlist/approvals) + `GET /health` + API JSON cùng host.
- `app.js` `API_BASE=""`; Dockerfile `COPY web` + uvicorn `main:app`.
- `resolve_web_dir()`: editable `/app/web`, fallback `Path("/app/web")`, cwd.

**Fails (liên quan feature này, đã sửa):**
- `WEB_DIR` chỉ `parents[2]/web` dễ lệch layout container → thêm
  `resolve_web_dir()` đa ứng viên.
- Thêm `tests/test_docker_single_url.py` (layout editable + same-origin).

**Missing (đúng kỳ vọng):**
- Live `docker compose up` trên máy này (Docker daemon off lúc review).
- README "Demo bằng Docker" (mục Phase 7 tiếp).

## 2026-09-17 — Phase 7: FastAPI phục vụ API + web/ một URL (container)

- `main.resolve_web_dir()` để mount static ổn định trong Docker.
- Xác nhận cùng origin: `/` + `/health` + `/app.js` (`API_BASE=""`).

## 2026-09-17 — Review Docker env_file vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 env từ .env, không bake secret vào image):**
- `docker-compose.yml`: `env_file: .env`; port `${APP_HOST_PORT:-8000}:8000`.
- Compose `environment` ghi đè `API_HOST=0.0.0.0`,
  `SQLITE_PATH=/app/data/portfolio_watch.db` (thắng giá trị local).
- `.env.example`: `APP_HOST_PORT`, ghi chú DB trong volume; Dockerfile /
  `.dockerignore` không chứa secret.

**Fails (liên quan feature này, đã sửa):**
- Test compose còn assert cứng `8000:8000` sau khi đổi sang
  `APP_HOST_PORT` → cập nhật `tests/test_docker_compose.py`.
- Cảnh báo: `env_file` inject *mọi* key trong `.env` → ghi chú trên
  `.env.example` (dùng bản copy sạch từ example, không merge .env project khác).

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- README "Demo bằng Docker"; xác nhận 3 luồng; ghi quyết định Phase 7.

## 2026-09-17 — Phase 7: env_file .env + cập nhật .env.example (Docker)

- `docker-compose.yml`: `env_file: .env`, `APP_HOST_PORT`, override host/DB.
- `.env.example`: mục Docker (`APP_HOST_PORT`, path DB volume, cảnh báo inject).
- `tests/test_docker_env_file.py`.

## 2026-09-17 — Review docker-compose vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục compose ↔ demo stack):**
- Service `app` build từ `Dockerfile`; map `8000:8000`; volume
  `portfolio-watch-sqlite` → `/app/data`; `SQLITE_PATH=/app/data/portfolio_watch.db`.
- `docker compose config` parse OK; không hard-code secret trong YAML.
- Cùng origin API+UI khi container chạy (Dockerfile đã mount `web/`).

**Fails (liên quan feature này):** không có lỗi blocking sau `compose config`.

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- `env_file: .env` + cập nhật `.env.example` (mục kế tiếp).
- README Docker; xác nhận 3 luồng trên máy sạch; ghi quyết định Phase 7.

## 2026-09-17 — Phase 7: docker-compose.yml (app + port + SQLite volume)

- Thêm `docker-compose.yml`: service `app`, `8000:8000`, volume named
  `pw_sqlite` mount `/app/data`.
- `tests/test_docker_compose.py` — assert port / volume / không bake key.

## 2026-09-17 — Review Dockerfile vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 7 mục Dockerfile ↔ demo API+UI cùng origin):**
- Image `python:3.12-slim`; `pip install -e .`; copy `src/` + `web/`;
  `EXPOSE 8000`; `uvicorn ... --host 0.0.0.0 --port 8000` (không reload).
- Không hard-code secret; `.dockerignore` loại `.env` / `.venv`.
- `ENV API_HOST=0.0.0.0`, `SQLITE_PATH=/app/data/portfolio_watch.db`.

**Fails (liên quan feature này, đã sửa):**
- `pip install .` (non-editable) → `__file__` vào site-packages →
  `WEB_DIR` lệch, UI static không mount → đổi `pip install -e .` để
  `WEB_DIR=/app/web`.

**Missing (đúng kỳ vọng — checklist Phase 7 tiếp):**
- `docker-compose.yml`, env_file, README Docker, xác nhận máy sạch.
- Docker daemon không chạy trên máy này lúc review — chưa `docker build` thật.

## 2026-09-17 — Phase 7: Dockerfile (API + web demo)

- Thêm `Dockerfile` + `.dockerignore`.
- `tests/test_dockerfile.py` — assert deps / web / expose 8000 / uvicorn /
  không bake secret.

## 2026-09-17 — Review phase completion dates vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 mục “ghi ngày hoàn thành từng phase”):**
- Bảng Phase 1–6 có ngày đóng phase; Phase 7 ghi *(chưa)*.
- Liên kết AC: `test_product_spec_ac.py` (Phase 5) + `verify_clean_local.py`
  (Phase 6 / 3 luồng).
- Checklist Phase 6 trong `implementation-plan.md` toàn `[x]`.

**Fails (liên quan feature này, đã sửa):**
- Cần assert Phase 6 không còn `- [ ]` → bổ sung
  `tests/test_change_log_phase_dates.py`.

**Missing (đúng kỳ vọng):**
- Phase 7 Docker (chưa bắt đầu) — sẽ cập nhật ngày khi đóng phase.

## 2026-09-17 — Ngày hoàn thành từng phase (Phase 6 checklist)

Tóm tắt ngày **đóng phase** (mục checklist cuối của phase trong
`implementation-plan.md` đã `[x]`). Chi tiết từng task vẫn ở các mục nhật ký
bên dưới.

| Phase | Tên | Ngày hoàn thành | Ghi chú ngắn |
|-------|-----|-----------------|--------------|
| 1 | Project setup | **2026-09-16** | FastAPI skeleton, settings, `/health`, `.env.example` |
| 2 | Core UI | **2026-09-16** | `web/` 3 khu vực + CSS + stub `app.js`; xác nhận mở UI |
| 3 | Core backend / data logic | **2026-09-17** | Ports, agents, scan/HITL/chat app layer, cron, full unit+IT |
| 4 | Connect UI to data | **2026-09-17** | `/scan` `/chat` `/approvals` `/watchlist`, CORS, static, wire UI |
| 5 | Validation and error states | **2026-09-17** | 4xx, soft-fail nguồn, cron isolation, guardrail, HITL idempotent, UI lỗi, rà AC |
| 6 | Local run instructions | **2026-09-17** | README local, clean-venv verify, bảng ngày phase (mục này) |
| 7 | Docker demo setup | **2026-09-17** | Dockerfile + compose, env_file, 1 URL, README Docker, `verify_clean_docker.py` |

**Liên kết AC:** Phase 5 đã xác nhận 6 bullet `product-spec.md` qua
`tests/test_product_spec_ac.py`; Phase 6 xác nhận 3 luồng chính theo README
(`scripts/verify_clean_local.py`); Phase 7 xác nhận Docker demo
(`scripts/verify_clean_docker.py`).

## 2026-09-17 — Review clean-venv verify vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 xác nhận máy sạch ↔ AC 3 luồng):**
- Venv mới + `pip install -e .` → health, UI 3 khu vực, watchlist, scan,
  chat (`hitl_used=false`), approve/reject → `CLEAN_VENV_SMOKE_OK`.
- Script `scripts/verify_clean_local.py` + mục README §8.

**Fails (liên quan feature này, đã sửa):**
- `load_dotenv(..., override=True)` khiến `.env` project ghi đè `SQLITE_PATH`
  môi trường → seed HITL lệch DB / xác nhận fail → đổi `override=False`.
- Test settings dùng `importlib.reload` có thể làm bẩn process → chuyển
  subprocess + assert source `override=False`.

**Missing (đúng kỳ vọng):**
- Mục Phase 6 cuối: ghi ngày hoàn thành từng phase vào change-log.
- Gắn cron lifespan; Docker (Phase 7).

## 2026-09-17 — Phase 6: xác nhận virtualenv mới chạy 3 luồng

- Chạy thật `scripts/verify_clean_local.py` trên venv tạm: scan / chat / HITL
  OK không sửa source.
- `load_dotenv(override=False)` để biến môi trường thắng `.env`.
- README §8 + `tests/test_clean_venv_smoke.py`.

## 2026-09-17 — Review README local run vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 6 hướng dẫn local ↔ AC chạy 3 luồng):**
- `pip install -e .`, `.env.example` → `.env`, `OPENAI_API_KEYS` / `SQLITE_PATH`.
- SQLite tự tạo schema (`connect` / one-liner); backend
  `python -m src.portfolio_watch.main` / uvicorn cổng **8000**.
- UI cùng origin `http://127.0.0.1:8000/`; seed watchlist; `/scan` `/chat`
  `/approvals`; cron thủ công `scan_watchlist`.

**Fails (liên quan feature này, đã sửa):**
- Thiếu lệnh copy `.env` trên PowerShell → thêm `Copy-Item`.
- Chưa nêu rõ heuristic vs mạng/`vnstock` → bổ sung ghi chú bảng env.
- Test README thiếu assert `uvicorn` / `/health` / sqlite init → siết
  `tests/test_readme_local_instructions.py`.

**Missing (đúng kỳ vọng — checklist Phase 6 tiếp):**
- Xác nhận máy sạch theo README end-to-end (mục kế tiếp).
- Gắn APScheduler vào `main` lifespan; Docker (Phase 7).

## 2026-09-17 — Phase 6: hướng dẫn chạy local (README)

- Viết lại mục **Chạy local (Phase 6)** trong `README.md`: cài deps, `.env`,
  SQLite auto-init, chạy `main`/uvicorn `:8000`, mở UI cùng origin, seed
  watchlist, cron thủ công `scan_watchlist`, kiểm 3 luồng.
- `tests/test_readme_local_instructions.py` — assert README đủ checklist.

## 2026-09-17 — Review product-spec AC rà lại vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (6 AC product-spec.md qua HTTP):**
- AC1 scan: giá/tin/phân loại; bất thường → severity + alert + gate1.
- AC2 đặt ngưỡng thấp (`POST /watchlist`) → vượt ngưỡng → sent/pending.
- AC3 approve/reject → sent / rejected + lý do Memory.
- AC4 đề xuất ngưỡng → Gate 2 pending, không tự áp dụng watchlist.
- AC5 chat → giá thật trong answer, `hitl_used=false`, không pending.
- AC6 guardrail chặn “nên mua/bán”; output chat/scan sạch.

**Fails (liên quan feature này, đã sửa):**
- AC1 chỉ cover bất thường; route assert sai enum EN → thêm nhánh bình
  thường + dùng giá trị `bình thường`/`bất thường`.
- AC2 seed FakeWatchlistStore thay vì “đặt” qua API → chuyển
  `POST /watchlist` rồi `POST /scan` (không ghi đè threshold).
- AC5 chưa assert cứng `hitl_used` + `price.latest_close` → siết assert.

**Missing (đúng kỳ vọng / ngoài AC bullets):**
- Cron wire vào `main` lifespan, README local, Docker (Phase 6).
- LLM composer thật / nguồn thị trường thật trong CI.

## 2026-09-17 — Phase 5: Rà lại acceptance criteria product-spec

- `tests/test_product_spec_ac.py` — 6 test map 6 bullet AC trong
  `product-spec.md` (scan pipeline, watchlist ngưỡng, approve/reject,
  Gate 2, chat không HITL, guardrail mua/bán).
- Đánh dấu hoàn thành mục Phase 5 cuối; không đổi production code.

## 2026-09-17 — Review Frontend error states vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 5 Frontend lỗi cơ bản + product-spec Frontend đơn giản):**
- Banner `#app-error` + câu “Không lấy được dữ liệu, thử lại” khi mạng/API lỗi.
- Scan/chat/approvals/watchlist lỗi hiện rõ trên UI (không chỉ console).
- Soft-fail giá/tin trên scan vẫn đẩy lên banner.

**Fails (liên quan feature này, đã sửa):**
- “Đang quét…” bị style như lỗi (`is-error`) → tách `isError` flag.
- Submit scan/chat rỗng im lặng → `showAppError("symbol/câu hỏi rỗng")`.

**Missing (đúng kỳ vọng):**
- Timeout/retry button riêng; form CRUD watchlist trên UI (ngoài mục này).
- Rà toàn bộ AC product-spec (checklist Phase 5 tiếp).

## 2026-09-17 — Phase 5: Frontend hiển thị lỗi API cơ bản

- `web/index.html`: banner `#app-error` (role=alert).
- `web/app.js`: `NETWORK_ERROR_MSG`, `showAppError`/`clearAppError`,
  `formatError` (status 0 → câu thân thiện); scan/chat/HITL/watchlist lỗi
  hiện banner + panel; bỏ `alert()`.
- `web/style.css`: `.app-error` / `#scan-result.is-error`.
- `tests/test_ui_error_states.py` — xác nhận banner + wiring lỗi.

## 2026-09-17 — Review HITL missing / already-done vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Phase 5 + AC approve/reject trạng thái đúng):**
- Id thiếu / đã xử lý → HTTP 404; không gửi Notifier lần 2; không ghi reject
  thêm; không thêm event; Gate 2 không đổi watchlist; cross approve↔reject.

**Fails (liên quan feature này, đã sửa):**
- Resolution chỉ có `alert_id`/`proposal_id` (thiếu `approval_id`) không bị
  coi đã xử lý → có thể approve lại → siết `_is_resolution` +
  `list_pending_approvals`.
- Reject id đã xử lý/thiếu kèm lý do rỗng trả 400 “lý do rỗng” thay vì 404
  đúng case → bỏ normalize reason trước app layer (ưu tiên missing/done).
- Thêm test Gate2 reject 2 lần + resolution alias + empty-reason → 404.

**Missing (đúng kỳ vọng):**
- Happy-path Gate 1/2 approve/reject (đã cover Phase 3–4 / test-plan #3).
- UI hiện lỗi API khi approve/reject fail (mục Frontend Phase 5 tiếp).

## 2026-09-17 — Phase 5: HITL missing / already-done → lỗi rõ, không đổi state

- `tests/test_hitl_missing_already_done.py` — xác nhận Phase 5:
  id thiếu / đã xử lý → HTTP 404; không gửi Notifier lần 2; không ghi reject
  thêm; không thêm alert event; Gate 2 không đổi watchlist; cross
  approve↔reject giữ trạng thái đã chốt.
- Không đổi production code — `review_approval` + router đã trả lỗi đúng.

## 2026-09-17 — Review Guardrail confirmation vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (AC guardrail + test-plan Synthesis/Answer):**
- “nên mua”/“nên bán” → `check_output` chặn; Synthesis rewrite `draft_attempts > 1`.
- Số lệch evidence → chặn; Synthesis/AnswerComposer rewrite hoặc fallback sạch.
- Hai nhánh dùng chung `domain.guardrails.output_checks`.

**Fails (liên quan feature này, đã sửa):**
- `build_evidence` gắn cả Eval `reasoning` → whitelist số bịa (vd. 12.5%) trong
  câu trả lời hỏi-đáp → bỏ `reasoning:` khỏi evidence blob; thêm test xác nhận.
- Confirmation thiếu case Synthesis rewrite “nên bán” và assert `calls > 1`
  trên nhánh Answer fallback bán → siết test.

**Missing (đúng kỳ vọng):**
- Model routing Severity (đã cover Phase 3 / ngoài mục “chặn vi phạm”).
- Composer LLM thật (vẫn inject/heuristic).

## 2026-09-17 — Phase 5: xác nhận Guardrail (test-plan)

- `tests/test_guardrail_confirmation.py` — case cụ thể test-plan:
  chặn “nên mua”/“nên bán”; số liệu lệch evidence; Synthesis/AnswerComposer
  rewrite (`draft_attempts > 1`); module `output_checks` dùng chung hai nhánh.
- Không đổi production code — hành vi Phase 3 đã đủ; bổ sung xác nhận.

## 2026-09-17 — Review cron isolation vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (test-plan #7 — cron/watchlist độc lập):**
- 1 mã crash / price timeout / news timeout không chặn mã khác.
- Đường APScheduler job thủ công (`build_scan_watchlist_job`) cùng isolation.

**Fails (liên quan feature này, đã sửa):**
- Chỉ cover lỗi mã giữa; cron path chưa assert thứ tự gọi + price/news
  trên mã OK → thêm BAD đầu/cuối; siết assert luồng giám sát độc lập
  (change_pct / tin theo mã).

**Missing (đúng kỳ vọng):**
- Quét song song (agents.md gợi ý) — test-plan chỉ yêu cầu độc lập lỗi.
- Wire scheduler vào `main.py` lifespan (Phase 6 hướng dẫn).

## 2026-09-17 — Phase 5: xác nhận cron isolation (tích hợp)

- `tests/test_cron_isolation_integration.py` — test-plan #7 ở mức tích hợp:
  agent crash mã giữa, Price/News timeout 1 mã, đường APScheduler job;
  FPT+VNM vẫn quét khi BAD lỗi.

## 2026-09-17 — Review Price/News source errors vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi nguồn lỗi/timeout không crash scan):**
- PriceAgent/NewsAgent bắt exception → error rõ; `scan_symbol` / `POST /scan`
  200, không alert khi thiếu dữ liệu.
- CafeF HTTP lỗi raise (không nuốt `[]`); multi-symbol đã có ở cron tests.

**Fails (liên quan feature này, đã sửa):**
- `quote.error="timeout"` không có cụm “không lấy được dữ liệu” → PriceAgent
  chuẩn hoá message.
- CafeF wrap RuntimeError → NewsAgent double-prefix “không lấy được tin” →
  re-raise gốc + NewsAgent tránh double-wrap.
- Thiếu case chỉ news timeout + assert không trả `None`.

**Missing (đúng kỳ vọng — checklist khác):**
- Cron isolation xác nhận lại (mục Phase 5 tiếp); UI hiện lỗi nguồn (Phase 5
  frontend).

## 2026-09-17 — Phase 5: PriceSource/NewsSource lỗi không crash scan

- `CafefNewsSource`: timeout/HTTP lỗi → raise (không nuốt `[]`) để
  NewsAgent gắn `không lấy được tin`.
- `tests/test_source_errors.py` — agent + `scan_symbol` + `POST /scan`
  khi price/news timeout: 200, `price.error` / `news_error` rõ, không alert.

## 2026-09-17 — Review API validate input vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 5 validate input → 4xx):**
- Symbol rỗng/whitespace/không hợp lệ → 400; ngưỡng âm → 400.
- Câu hỏi rỗng → 400; mã không có trên watchlist → 404.
- Reject lý do rỗng → 400; input hợp lệ vẫn 200 (scan/chat).

**Fails (liên quan feature này, đã sửa):**
- `""` bị pydantic `min_length` → 422 tiếng Anh mập mờ → bỏ min_length,
  thống nhất 400 tiếng Việt qua `validation.py`.
- Thiếu case PATCH ngưỡng âm, symbol quá dài/`FP-T`, thiếu field → 422.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Mã thị trường không tồn tại / PriceSource timeout → agent trả lỗi rõ
  (không crash) — mục Phase 5 kế tiếp, không map 4xx ở đây.

## 2026-09-17 — Phase 5: API validate input → 4xx

- Thêm `api/helpers/validation.py`: symbol / câu hỏi / ngưỡng / approval_id /
  lý do reject — 400 rõ ràng.
- Wire vào scan, chat, watchlist, approvals; ngưỡng âm → 400 (không còn
  chỉ dựa pydantic 422).
- `tests/test_api_validation.py` — rỗng, không hợp lệ, âm, 404 mã không
  có trên watchlist.

## 2026-09-17 — Review xác nhận UI vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi xác nhận Phase 4 UI / cùng API web gọi):**
- UI 3 khu vực + `app.js` wiring.
- #1 quét bình thường → không alert; chat #5 → answer, không HITL.
- #3 pending → approve (sent) / reject (lý do, không gửi); list `/approvals`
  cập nhật.

**Fails (liên quan feature này, đã sửa):**
- Thiếu xác nhận quét bất thường đủ field AC (severity/tin/alert/gate).
- Thiếu #2 auto-send (Gate 1 không còn pending trên UI).
- Pending item chưa assert field `renderApprovals` cần (`approval_id`,
  symbol).

**Missing (đúng kỳ vọng — Phase 5+ / ngoài checklist này):**
- #4 Gate 2 / #6 chat giải thích / #7 cron (đã cover ở test API/application
  khác).
- Form CRUD ngưỡng trên UI; validate lỗi UI (Phase 5).

## 2026-09-17 — Phase 4: Xác nhận luồng UI (scan / chat / HITL)

- Thêm `tests/test_ui_manual_confirmation.py` — e2e cùng endpoint
  `web/app.js` gọi: UI load, quét → kết quả, chat → answer, pending →
  approve/reject cập nhật list.
- Phase 4 checklist hoàn tất (5/5 passed).

## 2026-09-17 — Review wire web/app.js vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi UI nối 4 API + 3 khu vực):**
- Chat → `POST /chat`, hiện câu trả lời; watchlist/approvals load + refresh.
- Quét ngay → `POST /scan`; approve/reject → API + refresh list.
- `API_BASE=""` cùng origin; không còn stub log-only Phase 2.

**Fails (liên quan feature này, đã sửa):**
- Scan UI thiếu “toàn bộ luồng” AC (tin/severity/reason/gate2 proposal) →
  mở rộng `showScanResult`.
- `detail` 422 dạng mảng hiện xấu; reject lý do rỗng vẫn gửi →
  `formatError` + chặn reason rỗng; disable nút khi đang request.
- Test chưa chặn regression stub → `test_ui_wiring_renders_scan_chat_approvals`.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Xác nhận thủ công trên browser (quét / chat / approve-reject e2e UI).
- Form thêm/sửa ngưỡng watchlist trên UI (CRUD API đã có; AC “đặt ngưỡng”
  vẫn làm được qua API).

## 2026-09-17 — Phase 4: Wire web/app.js → API + render UI

- `web/app.js`: `API_BASE=""` (cùng origin); parse JSON; render chat /
  watchlist / approvals; approve/reject + quét ngay.
- `web/index.html`: form quét, `#watchlist-body`, bỏ placeholder mẫu.
- Còn mục xác nhận thủ công trên browser (checklist tiếp).

## 2026-09-17 — Review mount static web/ vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi phục vụ UI cùng origin với API):**
- `GET /` (và `/index.html`) trả trang 3 khu vực: chat / watchlist /
  approvals (product-spec Frontend).
- `/app.js`, `/style.css` cùng host; link relative từ HTML resolve được.
- Mount `/` không che API: `/health`, `/watchlist`, `/approvals`, `/docs`,
  OpenAPI `/scan` `/chat` vẫn JSON/HTML đúng.

**Fails (liên quan feature này, đã sửa):**
- Test chưa assert API JSON không bị static shadow, chưa check
  `/index.html` + asset links từ HTML → siết `test_api_static.py`.

**Missing (đúng kỳ vọng — checklist tiếp):**
- `web/app.js` còn `API_BASE` cứng + log-only — nối `fetch` + render UI
  thật (mục Phase 4 tiếp theo).

## 2026-09-17 — Phase 4: Mount static web/ cùng origin

- `main.py`: mount `StaticFiles(web/, html=True)` tại `/` (sau API routes)
  → UI + API cùng base URL khi demo.
- `tests/test_api_static.py` — `/`, `/app.js`, `/style.css`; `/health` +
  `/docs` vẫn hoạt động.

## 2026-09-17 — Review CORS + routers vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi đăng ký router + CORS cho web/):**
- Đủ 4 nhóm API (`/scan`, `/chat`, `/approvals`, `/watchlist`) + method
  khớp stub `web/app.js`.
- `CORSMiddleware` `allow_origins=["*"]` — GET và preflight POST/PATCH/DELETE
  trả `Access-Control-Allow-Origin: *` (Live Server / `Origin: null`).

**Fails (liên quan feature này, đã sửa):**
- Test chỉ cover `/health` + preflight `/chat` → mở rộng assert method
  OpenAPI và CORS trên đúng endpoint web gọi.

**Missing (đúng kỳ vọng — checklist tiếp):**
- Mount static `web/`, nối UI `fetch` + render kết quả thật.

## 2026-09-17 — Phase 4: CORS + đăng ký đủ router

- `main.py`: xác nhận 4 router (`scan`, `chat`, `approvals`, `watchlist`)
  + `CORSMiddleware` `allow_origins=["*"]` (dev, `web/` gọi cross-origin).
- `tests/test_api_cors.py` — OpenAPI có đủ path; CORS header + preflight.

## 2026-09-17 — Review CRUD /watchlist vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi CRUD watchlist API):**
- `GET/POST/PATCH/DELETE /watchlist` thêm/xem/sửa ngưỡng/xóa mã.
- User CRUD **không** tạo HITL pending (khác đề xuất EvalAgent → Gate 2).
- Symbol chuẩn hoá uppercase; rỗng/whitespace → 400; ngưỡng âm → 422;
  mã thiếu → 404.

**Fails (liên quan feature này, đã sửa):**
- Thiếu e2e product-spec “đặt watchlist ngưỡng thấp → quét vượt ngưỡng →
  cảnh báo”: `POST /watchlist` rồi `POST /scan` (không ghi đè threshold).
- Thiếu assert CRUD không tạo pending / PATCH áp dụng ngay (không Gate 2).

**Missing (đúng kỳ vọng — checklist khác):**
- CORS, mount static `web/`, UI gọi watchlist.

## 2026-09-17 — Phase 4: CRUD /watchlist API

- Thêm `api/routers/watchlist.py`: `GET/POST /watchlist`,
  `PATCH/DELETE /watchlist/{symbol}` → `WatchlistStore` (không qua HITL).
- Đăng ký watchlist router trong `main.py` (chưa CORS / static / UI).
- `tests/test_api_watchlist.py` — CRUD, default threshold, symbol rỗng,
  thiếu mã → 404, ngưỡng âm → 422.

## 2026-09-17 — Review POST/GET /approvals vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi HITL approve/reject qua API):**
- `GET /approvals` liệt kê chờ duyệt (Gate 1 + Gate 2) kèm payload.
- Gate 1 approve → status `sent`, Notifier gửi; reject → không gửi, lý do
  ghi Memory.
- Gate 2 approve → cập nhật watchlist; reject → giữ ngưỡng cũ.
- Id thiếu / đã xử lý → 404; lý do reject rỗng → 400.

**Fails (liên quan feature này, đã sửa):**
- test-plan #3 chưa khép HTTP: `POST /scan` → pending →
  `POST /approvals/.../approve|reject` — thêm e2e.
- Thiếu HTTP Gate 2 reject (giữ watchlist) và reject missing/already-done.
- `reason=""` bị 422 pydantic thay vì 400 “lý do rỗng” → bỏ `min_length`,
  validate sau strip.

**Missing (đúng kỳ vọng — router/checklist khác):**
- CRUD `/watchlist`, CORS, static `web/`, UI gọi approvals.

## 2026-09-17 — Phase 4: POST/GET /approvals API

- Thêm `api/routers/approvals.py`: `GET /approvals`,
  `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`
  → `review_approval` (Gate 1 gửi alert / Gate 2 cập nhật watchlist).
- Đăng ký approvals router trong `main.py` (chưa CORS / watchlist / static).
- `tests/test_api_approvals.py` — list, approve/reject Gate 1+2, reason rỗng,
  id thiếu/đã xử lý → 4xx.

## 2026-09-17 — Review POST /chat vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Chat API hỏi-đáp):**
- `POST /chat` chạy Rewrite → Supervisor → workers → AnswerComposer;
  trả lời dựa trên giá/tin, lưu hội thoại.
- #5 hỏi giá → chỉ `price`, không HITL / không pending.
- #6 hỏi "tại sao giảm" → có `news`/`eval`, câu trả lời nhắc tin/lý do.
- Follow-up ("còn mã đó") dùng Memory qua API.

**Fails (liên quan feature này, đã sửa):**
- Response chưa lộ `news_error` (khó thấy lỗi tin) → thêm field.
- Test #5/#6 chưa seed mã trong watchlist; chưa assert
  `list_pending_approvals == []` / title tin cụ thể.
- Thiếu case HTTP follow-up dùng lịch sử hội thoại.

**Missing (đúng kỳ vọng — ngoài phạm vi router chat):**
- Enforce chỉ trả lời mã có trong WatchlistStore (`answer_question`
  chưa nhận watchlist port — ghi nhận từ trước).
- `POST /approvals/...`, CORS / UI gọi `/chat`.

## 2026-09-17 — Phase 4: POST /chat API

- Thêm `api/routers/chat.py`: `POST /chat` → `answer_question`, trả
  rewritten/route/answer/price/news/severity; không tạo HITL.
- Đăng ký chat router trong `main.py` (chưa CORS / approvals / watchlist).
- `tests/test_api_chat.py` — hỏi giá, giải thích giảm, câu rỗng/whitespace.

## 2026-09-17 — Review POST /scan vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi API quét ngay 1 mã):**
- `POST /scan` chạy đủ luồng: giá, tin, route; bất thường → severity/alert/gate.
- #1 bình thường → không alert; #2 confidence cao → `sent`, không pending.

**Fails (liên quan feature này, đã sửa):**
- Thiếu coverage API cho #3 (pending khi confidence thấp) và #4 (`gate2_pending`).
- Response chưa lộ `news_error` (khó thấy đủ kết quả tin) → thêm field.
- Symbol chỉ whitespace → 400; siết assert `pending_events` / severity.

**Missing (đúng kỳ vọng — router khác / Phase 4 tiếp):**
- `POST /approvals/...` (phần còn lại của test-plan #3).
- CORS / UI gọi `/scan`.

## 2026-09-17 — Phase 4: POST /scan API

- Thêm `api/deps.py` (AppDeps + override test) và `api/routers/scan.py`:
  `POST /scan` → `scan_symbol`, trả route/price/news/severity/alert/gates.
- Đăng ký scan router trong `main.py` (chưa CORS / routers khác).
- `tests/test_api_scan.py` — normal, auto-send, symbol rỗng → 422.

## 2026-09-17 — Review backend test suite vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 3 “chạy unit + integration, chưa API/UI”):**
- Full suite `tests/`: **85 passed**.
- Unit theo test-plan (Price/News/Classifier/Eval/Synthesis/Gate/HITL/
  Supervisor/Answer) đã có trong các `test_*.py` riêng.
- Integration #1–#7 map application layer (scan / approve-reject / chat /
  cron thủ công), không HTTP.

**Fails (liên quan feature này, đã sửa):**
- #2 chỉ assert “không Gate 1” → siết thành `list_pending_approvals == []`
  + `status=SENT`.
- #3 thiếu assert pending trống sau approve/reject; pending phải có payload
  alert.
- #4 thiếu assert Gate 2 **không** tự `upsert` watchlist.
- #5/#6 thiếu assert không tạo `alert_events` / pending HITL.

**Missing (đúng kỳ vọng — Phase 4+):**
- `POST /scan`, `POST /chat`, `POST /approvals/...` HTTP e2e.
- Chat “mã trong watchlist” enforce qua WatchlistStore (answer_question
  chưa nhận watchlist port).

## 2026-09-17 — Phase 3: chạy full backend tests (test-plan, chưa API/UI)

- Chạy toàn bộ `tests/`: **85 passed**.
- Thêm `tests/test_backend_integration.py` map test-plan e2e #1–#7 ở
  application layer (scan / approve-reject / chat / cron thủ công) — không
  HTTP/UI (đúng phạm vi “chưa cần API/UI”).

## 2026-09-17 — Review Cron / scan_watchlist vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Cron / watchlist nhiều mã):**
- Đọc watchlist → gọi `scan_symbol` từng mã; 1 mã crash không chặn mã sau.
- APScheduler interval (`create_scan_scheduler`); có thể fire job thủ công.
- Ngưỡng lấy theo từng `WatchlistItem`.

**Fails (liên quan feature này, đã sửa):**
- Thiếu case PriceSource lỗi ở 1 mã (agent trả error) vẫn quét hết danh sách.
- Job scheduler có thể raise làm nhiễu cron → bọc `_safe_job`; thêm
  `build_scan_watchlist_job` (chạy thủ công / APScheduler, không raise).
- `interval_minutes` không hợp lệ → fallback 60; test e2e job + isolation.

**Missing (đúng kỳ vọng):**
- Wire scheduler vào `main.py` lifespan / demo stack (Phase 6 hướng dẫn).
- Quét song song nhiều mã (agents.md gợi ý; test-plan chỉ yêu cầu độc lập).

## 2026-09-17 — Phase 3: Cron / scan_watchlist (APScheduler)

- Thêm `application/scan_watchlist.py`: lặp watchlist → `scan_symbol` từng
  mã; `try/except` theo mã (1 mã lỗi không chặn các mã còn lại).
- Thêm `infra/scheduler/cron.py`: `create_scan_scheduler` /
  `start_scan_scheduler` / `stop_scan_scheduler` (APScheduler interval,
  `SCAN_INTERVAL_MINUTES`).
- `tests/test_scan_watchlist.py` — isolation lỗi, threshold theo item, job
  đăng ký + chạy thủ công.

## 2026-09-17 — Review review_approval vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (HITL Gate 1 / Gate 2):**
- Gate 1 approve → gửi Notifier, status sent; reject → `record_rejection`,
  không gửi.
- Gate 2 approve → cập nhật watchlist (ngưỡng + mã mới); reject → giữ nguyên
  cấu hình cũ.
- Id không tồn tại / đã xử lý → `ok=False` + lỗi rõ (approve và reject).

**Fails (liên quan feature này, đã sửa):**
- Reject lý do rỗng vẫn thành công (trái “lý do reject được ghi lại”) → bắt
  buộc reason không rỗng.
- Gate 1 approve: Notifier không set status vẫn có thể không “đã gửi” → ép
  `AlertStatus.SENT` sau send thành công.
- Snapshot Gate 2 reject mở rộng cho mã liên quan; thêm test reject 2 lần /
  missing / empty reason / SENT ép status.

**Missing (đúng kỳ vọng):**
- HTTP `POST /approvals/{id}/approve|reject` (Phase 4).

## 2026-09-17 — Phase 3: review_approval (HITL Gate 1 + Gate 2)

- Thêm `application/review_approval.py`:
  - `list_pending_approvals` — pending chưa có resolution.
  - Gate 1 approve → `Notifier.send` (status sent); reject →
    `record_rejection`, không gửi.
  - Gate 2 approve → `WatchlistStore.upsert` (ngưỡng + mã liên quan);
    reject → ghi lý do, giữ nguyên watchlist.
  - Approve/reject id không tồn tại hoặc đã xử lý → `ok=False` + error rõ.
- `tests/test_review_approval.py`.

## 2026-09-17 — Review hỏi-đáp vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (Supervisor / Rewrite / AnswerComposer / không HITL):**
- Tra cứu giá → chỉ `price`, không `eval`.
- “Tại sao … giảm” → `price+news+eval`; trả lời có tin/lý do.
- “Còn mã đó” → Rewrite lấy symbol từ Memory.
- Guardrail dùng chung `output_checks`; `hitl_used` / không tạo pending.
- Lưu hội thoại vào Memory sau trả lời.

**Fails (liên quan feature này, đã sửa):**
- “thông tin giá …” bị route `news_lookup` vì substring `tin` → lọc “thông
  tin” trước khi nhận diện tin tức.
- Follow-up không ticker (“Tại sao giảm?”) chưa lấy symbol từ Memory → bổ sung.
- `hitl_used` / `pending_approvals_created` hardcode `False`/`0` → đếm thật từ
  delta `alert_events`.
- Fallback guardrail khi “nên bán” + số giả; assert output cuối luôn pass check.

**Missing (đúng kỳ vọng):**
- `POST /chat` API (Phase 4).

## 2026-09-17 — Phase 3: hỏi-đáp (Supervisor + AnswerComposer + answer_question)

- Thêm `domain/agents/supervisor.py`: RewriteQuestion (symbol từ câu hỏi /
  Memory “mã đó”) + Supervisor routing (`agents_to_call`: price / news / eval).
- Thêm `domain/agents/answer_composer.py`: soạn câu trả lời, model routing,
  vòng guardrail dùng chung `output_checks` (không HITL).
- Thêm `application/answer_question.py`: Rewrite → route → gọi worker →
  compose → lưu hội thoại Memory; `hitl_used=False`, không tạo pending.
- `FakeMemoryStore` ghi conversation; `tests/test_answer_question.py`.

## 2026-09-16 — Review scan_symbol vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi luồng giám sát 1 mã / Confidence Gate / Gate 2 tạo pending):**
- Price+News → Classifier; NORMAL dừng không alert; ABNORMAL → Eval →
  Synthesis (guardrail) → Confidence Gate.
- Confidence cao + khớp ngưỡng → auto-send (Notifier), không Gate 1 pending.
- Confidence thấp / không khớp ngưỡng → Gate 1 `pending_approval` đúng nội dung.
- Đề xuất ngưỡng/mã → luôn Gate 2 pending, không áp dụng watchlist.

**Fails (liên quan feature này, đã sửa):**
- `Notifier.send` lỗi → crash toàn bộ scan → bắt lỗi, fallback Gate 1 pending.
- Thiếu assert/test ngưỡng từ `WatchlistStore`; thiếu xác nhận Gate 2 không
  `upsert` watchlist; thiếu assert auto-send không tạo Gate 1 pending.
- So sánh route abnormal bền hơn với string value.

**Missing (đúng kỳ vọng):**
- API `POST /scan`, approve/reject (`review_approval`), cron nhiều mã.

## 2026-09-16 — Phase 3: scan_symbol (Orchestrator + Confidence Gate)

### Công thức Confidence Gate (chốt)
- Auto-send khi `confidence >= 0.8` **và** `|change_pct| >= threshold_pct`
  (ngưỡng user / watchlist; mặc định 3%).
- Ngược lại → HITL Gate 1 (`pending_approval` trong MemoryStore).
- Có `proposed_threshold_pct` / `proposed_related_symbols` → **luôn** tạo
  Gate 2 pending (không có đường tắt), kể cả khi auto-send Gate 1.

### Thay đổi
- Thêm `application/scan_symbol.py`: Price+News song song → Classifier →
  (NORMAL dừng) / (ABNORMAL → Eval → Gate2? → Synthesis+Guardrail →
  Confidence Gate → Notifier hoặc Gate 1).
- `tests/test_scan_symbol.py`; `FakeMemoryStore` ghi `alert_events`;
  thêm `FakeNotifier`.

## 2026-09-16 — Review ConsoleNotifier vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Notifier / MVP “gửi cảnh báo”):**
- Log console + lưu DB (`append_alert_event`) đúng product-spec (không
  bắt buộc email/push).
- Gửi thành công → `FinalAlert.status=SENT` (“đã gửi”); event `kind=sent`
  để Notifier “ghi nhận” (test-plan e2e confidence cao).

**Fails (liên quan feature này, đã sửa):**
- `status=REJECTED` vẫn bị gửi + đổi thành SENT (trái “reject → không gửi”)
  → bỏ qua, chỉ warning, không ghi event.
- `append_alert_event` lỗi nhưng status đã = SENT (lệch DB) → ghi DB trước,
  chỉ set SENT khi persist OK.

**Missing (đúng kỳ vọng):**
- Wire scan/approve gọi `Notifier`; e2e POST /scan (Phase 4).

## 2026-09-16 — Phase 3: ConsoleNotifier

- Thêm `infra/notify/console_notifier.py`: implement `Notifier.send` — log
  console + `MemoryStore.append_alert_event` (kind=`sent`), set
  `FinalAlert.status=SENT`.
- `user_id` lấy từ `alert.metadata["user_id"]` hoặc mặc định constructor.
- `tests/test_console_notifier.py` — ghi DB SQLite tạm + assert log.

## 2026-09-16 — Review market_data vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi PriceSource/NewsSource):**
- Đúng Out of Scope MVP: 1 nguồn giá (`vnstock` VCI) + 1 nguồn tin CafeF;
  ports cho phép thêm nguồn sau.
- Lỗi/timeout: giá → `PriceQuote.error` (không raise); tin → `[]` (đúng
  contract `NewsSource`); CI dùng mock theo test-plan.
- CafeF: parse HTML, lọc `query` / `days`; HTTP lỗi không crash.

**Fails (liên quan feature này, đã sửa):**
- DataFrame không sắp theo `time` → lấy nhầm “giá mới nhất” → sort theo
  `time` khi có cột.
- Cột `Close` (hoa) bị coi là thiếu dữ liệu → chuẩn hoá tên cột về
  lowercase trước khi đọc `close`.
- Thiếu test: empty DF / raise → error; sort theo time; `Close`; lọc
  `days` CafeF.

**Missing (đúng kỳ vọng — chưa phải market_data):**
- Wire vào scan/chat/cron; Phase 5 “agent báo không lấy được dữ liệu” khi
  NewsSource trả `[]` do timeout (xử lý ở agent/orchestrator).

## 2026-09-16 — Phase 3: market_data (PriceSource / NewsSource)

### Quyết định nguồn dữ liệu
- **Giá:** `vnstock` `Quote.history` (source `VCI`) — lấy 2 phiên đóng cửa
  gần nhất để tính % thay đổi; không dùng API SSI/TCBS riêng.
- **Tin:** CafeF Ajax HTML
  (`Events_RelatedNews_New.aspx`) — không có API chính thức; parse `<li>`
  title/url/ngày; lỗi HTTP/timeout → trả `[]`.

### Thay đổi
- Thêm `infra/market_data/price_source.py` (`VnstockPriceSource`).
- Thêm `infra/market_data/news_source.py` (`CafefNewsSource` + parser HTML).
- Dependency: `vnstock>=3.0.0`, `pandas>=2.0.0` trong `pyproject.toml`.
- `tests/test_market_data.py` — parse/filter CafeF (mock HTTP), giá từ
  FakeQuote dataframe, symbol rỗng.

## 2026-09-16 — Review SQLite storage vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi storage / In Scope):**
- Có SQLite Watchlist / Price History / Memory đúng product-spec MVP.
- Hỗ trợ ghi preferences, hội thoại, alert events, reject (nền tảng HITL/
  chat trong test-plan).

**Fails (liên quan storage, đã sửa):**
- `record_rejection` không đọc lại được để xác nhận AC “lý do reject được
  ghi lại” → thêm `SqliteMemoryStore.list_rejections` + assert trong test.
- Thiếu CHECK `threshold_pct >= 0`; ép kiểu float cho OHLCV nullable.
- Test thêm case Gate 2 reject không đụng watchlist (giữ ngưỡng cũ).

**Missing (đúng kỳ vọng — chưa phải storage):**
- API approve/reject, scan/chat e2e, Notifier gửi cảnh báo.

## 2026-09-16 — Phase 3: SQLite storage (watchlist / price history / memory)

- Thêm `infra/storage/sqlite_db.py` (schema + connect).
- Implement `SqliteWatchlistStore`, `SqlitePriceHistoryStore` (+ `upsert_bars`),
  `SqliteMemoryStore` theo `domain/ports.py`.
- `tests/test_sqlite_stores.py` round-trip trên file DB tạm.

## 2026-09-16 — Review SynthesisAgent + Guardrail vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Synthesis + Guardrail / test-plan + AC guardrail):**
- Severity HIGH → model nặng; LOW → model nhẹ.
- “nên mua” → chặn + soạn lại (`draft_attempts > 1`).
- Số không có trong evidence → `check_output` fail.

**Fails (liên quan feature này, đã sửa):**
- Hết max attempts vẫn có thể phát hành body chưa sạch (reasoning chứa
  “nên bán”) → fallback chỉ evidence + kiểm guardrail lại.
- Composer raise / symbol rỗng chưa xử lý → bắt lỗi, trả kết quả rõ.
- Bổ sung case “nên bán” + assert output cuối luôn pass `check_output`.

**Missing (đúng kỳ vọng):**
- AC end-to-end scan/HITL/chat; LLM composer thật (hiện inject/heuristic).

## 2026-09-16 — Phase 3: SynthesisAgent + Guardrail output

- Thêm `domain/guardrails/output_checks.py`: chặn “nên mua/bán”; số liệu
  phải có trong evidence.
- Thêm `domain/agents/synthesis_agent.py`: `select_model` (light/heavy),
  soạn `FinalAlert`, vòng rewrite khi guardrail fail; đọc preferences từ
  `MemoryStore`.
- `FakeMemoryStore` + `tests/test_synthesis_agent.py` (routing model, rewrite
  khi có lời khuyên mua/bán, số không khớp evidence).

## 2026-09-16 — Review EvalAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi EvalAgent / test-plan):**
- Đủ data → không gọi `read_price_history`, có `Severity`.
- Mập mờ → gọi history; confidence thấp hơn khi lịch sử không ủng hộ
  (so sánh tương đối với case lịch sử ủng hộ).

**Fails (liên quan EvalAgent, đã sửa):**
- `read_history` raise làm mất Severity rõ → bắt riêng, vẫn trả Severity
  confidence thấp + evidence lỗi.
- Symbol rỗng / history rỗng sau khi request → hạ confidence rõ ràng.
- Test “thấp hơn” chỉ assert tuyệt đối → thêm so sánh
  opposed.confidence < supported.confidence.

**Missing (đúng kỳ vọng):**
- AC end-to-end product-spec (Gate 2 apply proposal, scan API…).
- LLM ReAct brain thật (hiện heuristic + inject).

## 2026-09-16 — Phase 3: EvalAgent

- Thêm `domain/agents/eval_agent.py`: `run_eval_agent` → `Severity`;
  `HeuristicEvalBrain` gọi `PriceHistoryStore.read_history` khi dữ liệu mập
  mờ; lịch sử không ủng hộ → hạ `confidence`; có thể đề xuất ngưỡng (Gate 2).
- `FakePriceHistoryStore` + `tests/test_eval_agent.py` (đủ data bỏ qua
  history; mập mờ → gọi history + confidence thấp).

## 2026-09-16 — Review Event Classifier vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Event Classifier / test-plan):**
- Biến động nhỏ + không tin xấu → `bình thường`.
- |%| lớn (tăng hoặc giảm) hoặc tin tiêu cực → `bất thường`.

**Fails (liên quan classifier, đã sửa):**
- Hint `"âm"` false-positive trong “đảm bảo”; phủ định “không giảm”
  vẫn bị bắt → bỏ hint mơ hồ, thêm chống negation; threshold <= 0 fallback 3.0.
- Brain raise → crash escalate → bắt lỗi, trả `NORMAL` (lọc rẻ, không gọi Eval).

**Missing (đúng kỳ vọng):**
- AC end-to-end `product-spec.md`; LLM classifier thật (hiện heuristic + inject).

## 2026-09-16 — Phase 3: Event Classifier

- Thêm `domain/agents/event_classifier.py`: `classify_event` →
  `RoutingDecision` (`bình thường` / `bất thường`); `HeuristicEventClassifier`
  (ngưỡng |%| hoặc tin tiêu cực); brain inject được cho LLM sau.
- `tests/test_event_classifier.py` theo test-plan (biến động nhỏ; |%| lớn;
  tin tiêu cực).

## 2026-09-16 — Review NewsAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi NewsAgent / test-plan):**
- Tin không liên quan bị lọc → `items == []`.
- Cần 2 lần gọi tool mới đủ tin → `tool_calls == 2`, dừng khi đủ;
  `max_steps` chặn lặp vô hạn.

**Fails (liên quan NewsAgent, đã sửa):**
- `fetch_news` raise giữa vòng → mất toàn bộ tin đã gather → bắt lỗi theo
  từng lần gọi, giữ tin đã lọc + `error` rõ.
- Chỉ `kind=="search"` mới gọi tool; symbol rỗng → lỗi rõ, không chạy loop.

**Missing (đúng kỳ vọng):**
- AC `product-spec.md` (scan/chat/HITL end-to-end).
- LLM brain thật (hiện inject `NewsAgentBrain` / heuristic) — wiring LLM
  thuộc bước sau.

## 2026-09-16 — Phase 3: NewsAgent + unit test

- Thêm `domain/agents/news_agent.py`: vòng lặp ReAct (search/finish) qua
  `NewsAgentBrain`, gọi `NewsSource.fetch_news`, lọc tin liên quan;
  `HeuristicNewsBrain` fallback không LLM; `max_steps` chống lặp vô hạn.
- `tests/fakes.FakeNewsSource` + `tests/test_news_agent.py` (lọc tin rác,
  gọi tool 2 lần rồi dừng, cap max_steps).

## 2026-09-16 — Review PriceAgent vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi PriceAgent / test-plan):**
- Tăng / giảm / đứng yên → `change_pct` đúng.
- `PriceSource` lỗi / thiếu `latest_close` → `PriceAgentResult` có `error`,
  không trả `None` cho toàn bộ kết quả.

**Fails (liên quan PriceAgent, đã sửa):**
- `PriceSource` raise exception → agent crash (trái “không crash”) → bọc
  try/except, trả `error` rõ.
- Thiếu test `prev_close` None + nguồn raise — đã thêm.

**Missing (đúng kỳ vọng):**
- Toàn bộ AC `product-spec.md` (scan API, HITL, chat, guardrail).
- Các agent/e2e khác trong `test-plan.md`.

## 2026-09-16 — Phase 3: PriceAgent + unit test

- Thêm `domain/agents/price_agent.py`: `run_price_agent` tính `change_pct`,
  trả `PriceAgentResult` rõ ràng khi lỗi / thiếu dữ liệu.
- Thêm `tests/test_price_agent.py` + `tests/fakes.FakePriceSource` (tăng/
  giảm/đứng yên + error).

## 2026-09-16 — Review `domain/ports.py` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi ports):**
- Đủ 6 interface checklist; `PriceQuote.error` hỗ trợ test-plan
  “không có dữ liệu / không trả None mập mờ”; `record_rejection` +
  `Notifier.send` khớp HITL / gửi cảnh báo; `read_history` khớp EvalAgent.

**Fails (liên quan ports, đã sửa):**
- `NewsSource` thiếu khung thời gian (agents: symbol + time window) → thêm
  `days`.
- `MemoryStore` thiếu lịch sử cảnh báo (agents kho dữ liệu) →
  `append_alert_event` / `list_alert_events`.
- `PriceBar.open` shadow builtin → đổi `open_price`.
- Docstring `PriceSource`: lỗi trả `PriceQuote` với `error`, không raise mơ hồ.

**Missing (đúng kỳ vọng — chưa implement infra/agents/API):**
- Toàn bộ AC `product-spec.md` và e2e/unit agent trong `test-plan.md`.

## 2026-09-16 — Phase 3: `domain/ports.py`

- Khai báo Protocol: `PriceSource`, `NewsSource`, `WatchlistStore`,
  `PriceHistoryStore`, `MemoryStore`, `Notifier`.
- DTO kèm port: `PriceQuote`, `NewsItem`, `PriceBar` (dataclass thuần).
- Chưa có implement infra — chỉ interface cho agent/fake test.

## 2026-09-16 — Review domain entities vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi entity):**
- Đủ 4 model checklist: `WatchlistItem`, `RoutingDecision`, `Severity`,
  `FinalAlert`; `EventRoute` khớp test-plan (“bình thường”/“bất thường”);
  `Severity` có đề xuất ngưỡng/mã (Gate 2); `AlertStatus` có
  pending_approval / sent / rejected (Gate 1).

**Fails (liên quan entity, đã sửa):**
- `FinalAlert` thiếu `id` + `reject_reason` — không biểu diễn được AC
  approve/reject (`/approvals/{id}`, lý do reject). Đã thêm.
- `WatchlistItem.symbol` / `FinalAlert.symbol` cho phép rỗng → `min_length=1`.

**Missing (đúng kỳ vọng — chưa phải entities):**
- Toàn bộ luồng AC/API/agent trong `product-spec.md` / `test-plan.md`
  (scan, chat, guardrail, cron…).

Không thêm entity/API mới ngoài chỉnh 4 model đã có.

## 2026-09-16 — Phase 3: domain entities

- Thêm `domain/entities/models.py`: `WatchlistItem`, `RoutingDecision`,
  `Severity`, `FinalAlert` (+ enum `EventRoute`, `SeverityLevel`,
  `AlertStatus`) — pydantic thuần, không import infra.
- Export qua `domain/entities/__init__.py`.

## 2026-09-16 — Review Phase 1 (re-check) vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 1):**
- Skeleton + `GET /health` → `{"status":"ok"}`; app title =
  `Portfolio Watch & Chat Agent`.
- Chỉ expose `/health` (+ docs mặc định FastAPI) — chưa có `/scan`, `/chat`,
  `/approvals`, `/watchlist` (đúng “chưa business features”).

**Fails:** không có lỗi Phase 1 mới so với lần review trước.

**Missing (đúng kỳ vọng — Phase 3+):**
- Toàn bộ acceptance criteria `product-spec.md`.
- Toàn bộ unit/e2e `test-plan.md`.

Không đổi code trong lần review này.

## 2026-09-16 — Phase 1 re-check (đã hoàn thành trước đó)

- Đọc lại AGENTS.md + specs: checklist Phase 1 toàn bộ `[x]`.
- Smoke-test lại: `GET /health` → `{"status":"ok"}`; `src/chatbot/` không
  còn; `pyproject.toml` + `src/portfolio_watch/` (settings, infra/llm, main)
  còn đủ.
- **Không viết lại / không thêm business features** — tránh đụng Phase 2 UI
  đã xong. Mục chưa làm tiếp theo là Phase 3.

## 2026-09-16 — Phase 2: xác nhận mở UI (3 khu vực, không lỗi console)

- Kiểm tra qua `python -m http.server` + Chrome headless: `#chat`,
  `#watchlist`, `#approvals` hiển thị; `style.css`/`app.js` 200.
- Phát hiện console error `GET /favicon.ico` 404 → thêm
  `<link rel="icon" href="data:,">` trong `index.html`.
- Re-check: 0 console error. Phase 2 UI checklist hoàn tất.

## 2026-09-16 — Review `web/style.css` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi CSS / In Scope frontend):**
- Product-spec: “1 trang đơn giản … không cần polish UI” — `style.css` chỉ
  làm 3 khu vực (chat / watchlist / approvals) dễ đọc; không over-design.

**Fails:** không có lỗi CSS liên quan feature này so với specs.

**Missing (đúng kỳ vọng — không thuộc CSS):**
- Toàn bộ acceptance criteria `product-spec.md` (scan, alert, HITL, chat API,
  guardrail).
- Toàn bộ cases `test-plan.md` (không có tiêu chí CSS/UI visual).

Không đổi code trong lần review này.

## 2026-09-16 — Phase 2: CSS tối thiểu (`web/style.css`)

- Thêm `web/style.css` (layout đơn giản: section, chat box, table, nút).
- `index.html` link stylesheet. Không polish UI.

## 2026-09-16 — Review `web/app.js` stubs vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi stub Phase 2):**
- Có hàm stub cho endpoint AC/test-plan sẽ dùng sau: `POST /scan`,
  `POST /chat`, `GET/POST approvals`, CRUD `/watchlist`.
- Chat submit + Approve/Reject chỉ `console.log` / `fetch` stub — chưa nối
  UI dữ liệu thật (đúng Phase 2).

**Fails (liên quan feature này, đã sửa):**
- `wireUiStubs()` tự gọi `getWatchlist()` + `getApprovals()` khi load → luôn
  lỗi mạng/CORS trên console (backend chưa có), xung đột mục Phase 2
  “không lỗi console”. Đã bỏ auto-fetch; gọi tay từ console khi cần.

**Missing (đúng kỳ vọng — không implement ở stub):**
- Toàn bộ acceptance criteria `product-spec.md` (luồng scan/chat/HITL thật,
  cập nhật trạng thái, guardrail).
- Toàn bộ e2e `test-plan.md` (`/scan`, `/chat`, approve/reject có side-effect).

Không thêm UI/API mới (vd. nút Quét ngay).

## 2026-09-16 — Phase 2: `web/app.js` (API stubs, log console)

- Thêm `web/app.js`: stub `fetch` cho Phase 4 (`/scan`, `/chat`, `/approvals`,
  approve/reject, CRUD `/watchlist`) — chỉ `console.log`, chưa cập nhật UI.
- `index.html`: nạp `app.js`; nút Approve/Reject gắn `data-*-id` để gọi stub.

## 2026-09-16 — Review `web/index.html` vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi UI tĩnh / In Scope frontend):**
- Đủ 3 khu vực product-spec yêu cầu: chat box, xem watchlist, danh sách
  cảnh báo chờ duyệt (Approve/Reject).

**Fails (lỗi liên quan feature này, đã sửa):**
- Form chat `type="submit"` mặc định reload trang khi bấm Gửi (file://).
  Thêm `onsubmit="return false;"` — chưa nối API (để Phase 2 mục `app.js`).

**Missing (đúng kỳ vọng — không thuộc HTML tĩnh):**
- Toàn bộ acceptance criteria `product-spec.md` (scan API, alert thật, HITL
  qua API, Chat API, guardrail).
- Toàn bộ cases `test-plan.md` (agents, gates, e2e `/scan` `/chat`).

Không thêm khu vực/UI mới (vd. nút Quét ngay) trong lần sửa này.

## 2026-09-16 — Phase 2: `web/index.html` (3 khu vực tĩnh)

- Tạo `web/index.html` với 3 section tĩnh: Chat (ô nhập + khung hội thoại),
  Watchlist (bảng mã + ngưỡng mẫu), Cảnh báo chờ duyệt (item mẫu +
  Approve/Reject). Chưa nối API, chưa có `app.js` / CSS riêng.

## 2026-09-16 — Review Phase 1 vs product-spec / test-plan

### Kết quả đối chiếu

**Passes (phạm vi Phase 1 / implementation-plan):**
- Khung `src/portfolio_watch/` + `pyproject.toml` + `infra/llm/` +
  `GET /health` → `{"status":"ok"}`.
- Settings có biến riêng project (watchlist, threshold, sources, sqlite).

**Fails (lỗi Phase 1, đã sửa):**
- `.env` cũ còn `APP_NAME=Vietnamese Legal Assistant` → FastAPI title /
  settings sai tên app. Đã đổi `APP_NAME` và bổ sung các key Phase 1 còn
  thiếu (`API_*`, `DEFAULT_*`, `PRICE_SOURCE`, `NEWS_SOURCE`, `SQLITE_PATH`,
  …) mà không đụng API keys.
- Port `8000` bị process uvicorn smoke-test trước chiếm → `python -m …`
  báo WinError 10013. Đã dừng process; khởi động lại `/health` OK.

**Missing (đúng kỳ vọng — thuộc phase sau, không implement ở đây):**
- Toàn bộ acceptance criteria trong `product-spec.md` (scan, watchlist
  alert, HITL approve/reject, Gate 2, Chat API, guardrail mua/bán).
- Toàn bộ unit/integration cases trong `test-plan.md` (agents, gates,
  `POST /scan`, `POST /chat`, cron).

Không thêm business features mới trong lần sửa này.

## 2026-09-16 — Phase 1: Project setup

- Xóa toàn bộ `src/chatbot/` (code cũ ReAct đơn-agent).
- Tạo khung `src/portfolio_watch/` (api / application / domain / infra /
  shared) + `__init__.py`.
- Thêm `pyproject.toml` (fastapi, uvicorn, langgraph, langchain-openai,
  pydantic-settings, openai, apscheduler).
- Thêm `shared/settings.py`, `shared/logging.py`, `.env.example` (bỏ RAG/
  embeddings; thêm watchlist, threshold, price/news source, sqlite path).
- Port `infra/llm/` từ `llm-engineer-demo/app/llm` (backends, client,
  resilience, params, completion) — đổi import sang `src.portfolio_watch`.
- `main.py`: FastAPI + `GET /health` → `{"status":"ok"}`.
- Gỡ service chatbot cũ khỏi `docker-compose.yml` (Docker demo = Phase 7).
- Cập nhật README lệnh chạy Phase 1.
- **Chưa có** business features (scan/chat/agents/UI).

## 2026-09-16 — AGENTS.md cho coding agent

- Viết lại `AGENTS.md` thành hướng dẫn ngắn cho Cursor agent (đọc specs trước,
  một phase/task mỗi lần, giữ app đơn giản, không thêm lib thừa, không đổi
  architecture nếu chưa cập nhật spec, cập nhật change-log + hướng dẫn test
  sau mỗi lần implement).
- Chuyển mô tả domain agents sang `specs/agents.md`; cập nhật tham chiếu trong
  `README.md`, `specs/product-spec.md`, `specs/implementation-plan.md`.

## 2026-09-16 — Khởi tạo spec (Spec-Driven Development)

- Đọc sơ đồ kiến trúc (`portfolio-watch-agent-explained.md` + `.mmd`/`.png`),
  khảo sát `llm-engineer-demo` (nguồn kỹ thuật tái dùng) và `AI_Face_checkin`
  (mẫu clean architecture: `api → application → domain → infra` + `shared`).
- Xác nhận với người dùng: code cũ trong `src/chatbot/` (ReAct đơn-agent,
  guardrails/eval rỗng, layer đặt tên `app/domain/infrastructure`) sẽ bị xóa
  và viết lại theo cấu trúc mới — chỉ tái dùng Ý TƯỞNG kỹ thuật (LLM client,
  model routing, guardrails, tracing), không giữ nguyên file.
- Viết 6 tài liệu spec ban đầu: `README.md`, `AGENTS.md`,
  `specs/product-spec.md`, `specs/implementation-plan.md`,
  `specs/test-plan.md`, `specs/change-log.md` (file này).
- **Chưa viết code implementation** — đây là bước dừng lại để review spec
  trước khi bắt đầu build theo `specs/implementation-plan.md`.

### Quyết định mở, cần chốt trước/khi implement

- Nguồn dữ liệu giá real-time cho mã VN (vnstock? SSI/TCBS public API?) —
  chưa khảo sát kỹ, ghi trong implementation-plan.md phần "Rủi ro".
- Cách lấy tin từ cafef (API chính thức hay scraping) — chưa xác nhận.
- Công thức cụ thể cho "độ tin cậy cao" ở Confidence Gate — sẽ chốt khi viết
  `synthesis_agent.py`.
