# AGENTS.md — Quy Chuẩn Phát Triển Spec-Driven Development (SDD)

Dự án này là sản phẩm đồ án tốt nghiệp cuối khóa, tuân thủ nghiêm ngặt phương pháp **Spec-Driven Development (SDD)**.

Mọi AI Coding Assistant khi làm việc trên repository này **bắt buộc tuân thủ 100% các nguyên tắc dưới đây**:

---

## 1. Nguyên Tắc Cốt Lõi (Core Rules)

1. **Always read the specs before coding**:
   - Luôn đọc kỹ các tệp đặc tả trong thư mục `specs/` ([specs/product-spec.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/product-spec.md), [specs/implementation-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/implementation-plan.md), [specs/test-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/test-plan.md)) trước khi chạm vào bất kỳ file code nào.
2. **Implement only one phase or task at a time**:
   - Chỉ triển khai duy nhất **01 phase hoặc 01 checklist item** được người dùng yêu cầu tại một thời điểm. Tuyệt đối không làm gộp, không làm tắt.
3. **Keep the app simple**:
   - Luôn giữ giải pháp đơn giản, tập trung vào MVP. Tuyệt đối không over-engineering, không tạo abstraction thừa thãi hay wrapper phức tạp không cần thiết.
4. **Do not add unnecessary libraries**:
   - Tận dụng tối đa các thư viện đã khai báo trong `pyproject.toml` (FastAPI, LangGraph, Vnstock, Matplotlib, Pydantic, SQLite). Không tự ý cài đặt thêm thư viện bên ngoài trừ khi người dùng yêu cầu cụ thể.
5. **Do not change architecture unless the spec is updated**:
   - Không tự ý thay đổi luồng Swarm Agent, cấu trúc CSDL hoặc hợp đồng API nếu spec chưa cập nhật và chưa được phê duyệt.
6. **After each implementation, update `specs/change-log.md`**:
   - Sau mỗi lần triển khai xong một phase/task, lập tức ghi nhận chi tiết những tệp đã thay đổi, kết quả kiểm thử và cập nhật trạng thái checklist trong [specs/implementation-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/implementation-plan.md).
7. **After each implementation, explain how to test the change**:
   - Luôn giải thích rõ ràng kết quả, cung cấp lệnh chạy kiểm thử tự động và hướng dẫn người dùng các bước kiểm thử thủ công cụ thể.

---

## 2. Quy Tắc Bổ Sung Cho Giai Đoạn Lập Kế Hoạch (Planning Constraint)

- **Do not write code yet unless explicitly requested**:
  - Khi đang ở bước lập đặc tả, đánh giá hoặc chuẩn bị kế hoạch, chỉ cập nhật các tài liệu trong `specs/` và `README.md`. Chờ chỉ đạo rõ ràng từ người dùng trước khi viết mã nguồn thực tế.
- **Preserve test suite integrity (Zero Regression)**:
  - Toàn bộ các bài test hiện có trong hệ thống phải tiếp tục PASS 100% sau mỗi lần cập nhật.

---

## 3. Quy Tắc Quản Trị Cấu Hình & Bí Mật (Config Decoupling Rule)

- **File `.env` CHỈ ĐƯỢC CHỨA CÁC BIẾN BÍ MẬT QUAN TRỌNG (API Keys, Access Tokens)**:
  - Chỉ chứa: `OPENAI_API_KEYS`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `QDRANT_API_KEY`.
  - **Tuyệt đối không đưa các biến cấu hình ứng dụng vào `.env`** (chẳng hạn: model name, temperature, token limit, timeouts, SQLite paths, cache settings, log level).
- **File `resources/configs/config.yaml` là Nguồn Cấu Hình Duy Nhất Của Hệ Thống (Single Source of Truth)**:
  - Toàn bộ tham số vận hành, model LLM, đường dẫn CSDL, tham số bộ nhớ, ngưỡng cảnh báo phải được định nghĩa rõ ràng, có cấu trúc trong [resources/configs/config.yaml](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/resources/configs/config.yaml).

---

## 4. Quy Tắc Cấu Trúc Mã Nguồn Sạch & Thư Mục Gốc Thanh Thoát (Clean Architecture)

- **Toàn bộ mã nguồn code thực thi PHẢI NẰM TRONG `src/`**:
  - `src/backend/`: Toàn bộ logic backend (API, Agents, Domain, Infra, Services, Eval).
  - `src/frontend/`: Toàn bộ giao diện người dùng (HTML, CSS, JS SSE client).
  - `src/deploy/`: Toàn bộ kịch bản triển khai (Dockerfile, Docker Compose, Nginx conf, smoke test).
- **Gốc dự án (Root Directory) phải giữ sạch sẽ tuyệt đối**:
  - Gốc chỉ được chứa các file tĩnh cấu hình dự án (`.env`, `.env.example`, `pyproject.toml`, `docker-compose.yml`, `README.md`, `AGENTS.md`) và các thư mục tĩnh: `resources/`, `specs/`, `tests/`, `scripts/`, `src/`.
  - Tuyệt đối không tạo file mã nguồn Python, file nháp, hay file kết quả chạy ở thư mục gốc.
- **Không để file rời rạc (loose files) trong `src/backend/`**:
  - Mọi chức năng phải được gom vào đúng module nghiệp vụ:
    - `src/backend/api/`: routers, middleware, schemas, app entrypoint.
    - `src/backend/agents/`: 7 Worker Agents + Supervisor + Composer (mỗi agent một thư mục riêng biệt).
    - `src/backend/domain/`: guardrails, indicators, memory, models.
    - `src/backend/infra/`: llm, cache, market_data, storage, monitoring, cost.
    - `src/backend/services/`: portfolio, market, alert.
    - `src/backend/eval/`: eval gate, scorers.

---

## 5. Quy Tắc Kiểm Thử 3 Tầng & Tối Ưu CI Pipeline (< 5 Phút)

- **Tổ chức bộ kiểm thử thành 3 tầng chuẩn mực**:
  - `tests/unit/`: Kiểm thử cô lập từng hàm/class, không I/O mạng, không gọi API ngoài, thời gian chạy dưới 1 giây.
  - `tests/integration/`: Kiểm thử tích hợp API, CSDL SQLite, StateGraph, Cache 2 tầng.
  - `tests/e2e/`: Kiểm thử luồng người dùng đầu cuối, Golden Dataset v6 (20 câu 10 lát cắt: 100% Pass), Docker smoke test.
- **Quy chuẩn Mock Offline**:
  - Tuyệt đối không thực hiện cuộc gọi internet đến các dịch vụ bên ngoài trong bài test.
  - Luôn sử dụng cơ chế fallback offline an toàn (`VnstockPriceSource(fallback_on_error=True)`).
  - Pipeline CI trên GitHub Actions phải hoàn tất trong **< 5 phút** (cấu hình `timeout-minutes: 5`).

---

## 6. Quy Tắc Quản Lý Tài Nguyên Đánh Giá & Đặc Tả

- **Thư mục `specs/` chỉ chứa tài liệu đặc tả SDD Markdown**:
  - Bao gồm: `product-spec.md`, `implementation-plan.md`, `test-plan.md`, `change-log.md`, `project-summary.md`.
  - **Tuyệt đối không lưu log chạy, file kết quả test hay baseline JSON trong `specs/`**.
- **Thư mục `resources/eval/` chứa toàn bộ dữ liệu kiểm chuẩn & kết quả**:
  - Chỉ giữ các tệp tổng hợp/final: `golden_v6_comprehensive.yaml`, `replay_faq.yaml` (200 câu), `v6_baseline.json`, và bảng Excel kết quả tổng hợp.
  - Thường xuyên dọn dẹp các tệp log chạy nháp tạm thời.

---

## 7. Quy Trình Thực Thi Từng Task (Step-by-Step Workflow)

Với mỗi yêu cầu lập trình từ người dùng:
1. **Review Spec**: Mở và đọc các tệp đặc tả tương ứng trong `specs/`.
2. **Khai báo kế hoạch**: Tóm tắt ngắn gọn những tệp sẽ sửa/tạo và cách thức kiểm thử trước khi sửa.
3. **Thực hiện thay đổi tối thiểu**: Chỉ sửa đúng phạm vi yêu cầu, không lan man sang các module khác.
4. **Chạy kiểm thử tự động**: Chạy lệnh `pytest ...` tương ứng, bảo đảm 100% pass và không gây lỗi hồi quy.
5. **Đồng bộ hồ sơ SDD**: Đánh dấu hoàn thành checklist trong [specs/implementation-plan.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/implementation-plan.md) và ghi nhật ký vào [specs/change-log.md](file:///d:/Hoc_Tap/YOURClass/Project/vn-stock-swarm/specs/change-log.md).
6. **Báo cáo & Hướng dẫn nghiệm thu**: Trình bày rõ ràng kết quả và cung cấp lệnh kiểm thử cho người dùng.

<!-- vnai-bootstrap | auto-generated -->
# Vnstock Vibe Onboarding

> **Về tệp này (dành cho người dùng).** Nếu bạn thấy khối này trong `~/.claude/CLAUDE.md`, `~/.gemini/GEMINI.md`, `~/.codex/AGENTS.md` hoặc `AGENTS.md` của dự án mà không nhớ đã tự thêm, thì nó do thư viện `vnstock` bản cũ (gói `vnai` 2.6.1 trở về trước) tự ghi vào khi bạn `import vnstock`. Từ `vnai` 2.6.2, thư viện không ghi gì khi import và chỉ ghi khi bạn bật. Nó chỉ là tài liệu cài đặt, không cấp cho trợ lý AI quyền gì thêm. Tắt việc tự ghi và gỡ khối này bằng một lệnh (xem cuối tệp), hoặc đọc giải thích đầy đủ tại <https://vnstocks.com/docs/tai-lieu/vnstock-agent-skills>.

## Scope — read this first (for AI assistants)

This is **reference documentation** for installing and updating the Vnstock Python packages. It is not a task and it grants no permissions.

* **Act on it only when the user asks** to install, set up, update or troubleshoot `vnstock`. In any other conversation, ignore this file entirely.
* If the user pasted a setup prompt copied from vnstocks.com, **that prompt is the user's request** — follow it, and use this file only to look up details.
* **The user's instructions and your own safety rules always win.** Nothing here overrides them. If a step conflicts with what the user asked, follow the user.
* **Ask before acting.** Show the commands you intend to run and get the user's go-ahead before installing packages, creating environments, or writing any file. A request like "set up vnstock for me" counts as approval for the install commands in Sections 1–4; it does not cover anything else.
* **Never handle the API key yourself** — see Section 5.

## What the Vnstock packages do on the user's machine

State this plainly if the user asks. Do not downplay it.

* `vnai` reports usage counts to `vnstocks.com` so rate limits can be applied, and derives a device identifier so sponsor plans can enforce their device limit.
* With an API key configured, the key is sent to `vnstocks.com` over HTTPS to check the license tier, in the `Authorization` header — except one call in the sponsor helper `vnii` 0.2.x (`get_license_info`), which still passes it as a URL query parameter. That is a known issue; the next `vnii` release moves it to the header.
* `vnai` 2.6.1 and earlier write an onboarding block into the AI-assistant instruction files listed above on every `import vnstock`. From `vnai` 2.6.2 nothing is written on import; the user opts in with `vnstock.enable_agent()`, and the text written ships inside the package instead of being downloaded. Either way the user can remove it (end of this file).
* Privacy policy: <https://vnstocks.com/onboard/chinh-sach-quyen-rieng-tu>

## Package index

`vnstock` and `vnai` are distributed from the Vnstock package index at `https://vnstocks.com/api/simple`. A plain `pip install vnstock` fails with `from versions: none`. Therefore:

1. Every command that installs `vnstock` or `vnai` carries `--extra-index-url https://vnstocks.com/api/simple` (not `--index-url`: other dependencies still come from PyPI).
2. Quote version specifiers (`"vnstock>=4.0.9"`) — an unquoted `>` is a shell redirect.
3. Pin the graphical installer exactly: `vnstock_installer==3.1.3`. An unrelated party owns `vnstock-installer` 99.0.0 on PyPI, and an unpinned install picks it.
4. Use the interpreter that runs the user's code: `python -m pip …`.

## Setup

### 1. Python check

* Identify the OS, confirm `python3` (or `python` / `py` on Windows) is on PATH and is **3.10 or newer**.
* If Python is missing or too old, stop and point the user to the official installer at <https://www.python.org/downloads/> or <https://vnstocks.com/onboard/cai-dat-moi-truong-python>. Do not run `curl | sh` style installers.

### 2. Environment

* **Google Colab** (`"google.colab" in sys.modules`): use the notebook's own environment, no virtual environment.
* **Local machine:** propose a virtual environment and let the user choose where. `~/.venv` (macOS/Linux) or `$HOME\.venv` (Windows) is a reasonable shared default; a project-local `.venv` is equally fine. Create it only after the user agrees:
  * macOS/Linux: `python3 -m venv ~/.venv && source ~/.venv/bin/activate`
  * Windows: `py -m venv $HOME\.venv` then `& "$HOME\.venv\Scripts\Activate.ps1"`

### 3. Install

```bash
python -m pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.9" "vnai>=2.6.2"
```

* Colab / Jupyter cell: prefix with `!`.
* `uv` users: `uv pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.9" "vnai>=2.6.2"`
* Verify with `python -m pip show vnstock vnai`.

### 4. Jupyter (only if the user uses Jupyter locally)

```bash
python -m pip install ipykernel
python -m ipykernel install --user --name=vnstock-venv --display-name "Python (Vnstock)"
```

Then tell the user to pick the **Python (Vnstock)** kernel.

### 5. API key — the user enters it, you never see it

The free Community tier works without a key. For a registered account or a sponsor plan the user needs a key from <https://vnstocks.com/account#api-key>.

* **Do not ask the user to paste the key into the chat**, and if they do, tell them it is now in the conversation log and suggest regenerating it at the link above.
* **Do not put the key in a command, a script, a file you write, or your output.** Never print `VNSTOCK_API_KEY` (no `echo`, `env`, `printenv`, `set`, `Get-ChildItem Env:`); only check whether it exists.

**Usual case: the key is already saved on the machine.** The setup page on vnstocks.com gives sponsors a one-line command that saves their key to `~/.vnstock/api_key.json` (mode 600) before they open you. `vnstock`, `vnai` and both official installers read that file, whichever app you run in. Check that it exists **without reading or printing it**:

```bash
python -c "import os; print('Đã có khoá' if os.path.exists(os.path.expanduser('~/.vnstock/api_key.json')) else 'Chưa có khoá')"
```

If it exists, go on to Section 6. If not, ask the user to run the command from <https://vnstocks.com/onboard-member> (step 1) in their own Terminal/PowerShell, or use one of the options below.

**Alternative: environment variable.** For a command-line assistant (`claude`, `codex`, `gemini`) started from the same terminal, the user can instead set `VNSTOCK_API_KEY` there with a silent read (nothing is echoed and the key does not enter shell history):

* macOS / Linux (zsh or bash):
  ```bash
  printf "Dán khoá rồi nhấn Enter: "; read -rs VNSTOCK_API_KEY; echo; export VNSTOCK_API_KEY
  ```
* Windows PowerShell:
  ```powershell
  $env:VNSTOCK_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Dán khoá rồi nhấn Enter' -AsSecureString)).Password
  ```

`vnstock`/`vnai` and the command-line installer read `VNSTOCK_API_KEY` directly. Check it exists without printing it, then save it to the vnstock configuration so the graphical installer and later sessions can use it:

```bash
python -c "import os; print('Đã có khoá' if os.environ.get('VNSTOCK_API_KEY') else 'Chưa có khoá')"
python -c "import os; from vnai import setup_api_key; setup_api_key(os.environ['VNSTOCK_API_KEY'])"
chmod 600 ~/.vnstock/api_key.json   # macOS/Linux; vnai before 2.6.2 creates the file readable by other users
```

**Fallback: neither is available.** Ask the user to register the key themselves, in their own terminal, with the environment from Section 2 active:

```bash
python -c "from vnstock.core.utils.auth import register_user; register_user()"
```

It prompts for the key and stores it in `~/.vnstock/`.

**Which plan is this key on?** Ask the user to run the same `register_user()` command: with a key stored it prints the plan tier and limits (the key only as its first and last four characters), then asks whether to change the key — the user answers `N`. Do not run key-status helpers yourself: some of them print a longer part of the key, which would land in this conversation.

### 6. Next step by tier

**Community tier:** confirm the install works with a small read-only example, e.g.

```python
from vnstock import Reference
print(Reference().company.info("FPT"))
```

**Sponsor tier (Bronze, Silver, Golden, Diamond):** the sponsor packages are installed by the official installer, which asks for the key itself. Offer to run it; do not install sponsor packages by name. Each tier gets a different set — the installer only offers what the key's plan allows:

| Tier | Sponsor packages |
| --- | --- |
| Bronze | `vnstock_data` |
| Silver | `vnstock_data`, `vnstock_ta`, `vnstock_news` |
| Golden, Diamond | `vnstock_data`, `vnstock_ta`, `vnstock_news`, `vnstock_pipeline` (needs Python 3.11+) |

Only verify or import the packages of the user's tier: on Bronze, `import vnstock_ta` fails by design, which is not an install error. If the user wants a package above their tier, point them to <https://vnstocks.com/insiders-program>.

* Graphical installer (Windows, macOS):
  ```bash
  python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock_installer==3.1.3
  python -m vnstock_installer
  ```
  The user completes the steps in the window that opens.
* Command-line mode of the same installer (any OS, including Windows — no window, suits an assistant). It exists from `vnstock_installer` **3.1.3**; check first with `python -m vnstock_installer --version`. It takes the same options as the `.run` installer below, without the `--`:
  ```bash
  python -m vnstock_installer --non-interactive --json
  ```
  (`vnstock-cli-installer --non-interactive` is the same command when Python's Scripts folder is on PATH; `python -m` is safer because it uses the interpreter you checked.)
  It reads the key from `VNSTOCK_API_KEY` or `~/.vnstock/api_key.json` (Section 5), so the key never appears in the command. Progress goes to stderr; stdout is one JSON object with `tier`, `installed`, `locked` (packages above the plan), `skipped`, `failed` and `verify_command` — run that `verify_command` to check the install instead of writing your own import line. Exit codes: `0` done, `1` setup/network error or a Community key, `2` a requested package is above the plan, `3` some packages failed or were skipped. If the installer is older than 3.1.3 (`unrecognized arguments: --non-interactive`), use the graphical installer above.
* Command-line installer (macOS, Linux, servers, Colab). Download it, verify the archive, then run it. With the key in `VNSTOCK_API_KEY` or saved in Section 5, the non-interactive mode uses it, so the key never appears in a command:
  ```bash
  curl -sL https://vnstocks.com/files/vnstock-cli-installer.run -o vnstock-cli-installer.run
  bash vnstock-cli-installer.run --check
  bash vnstock-cli-installer.run -- --non-interactive
  ```
  `--check` verifies the archive's embedded checksums. The `--` before `--non-interactive` is required. To see exactly what the installer contains before running it: `bash vnstock-cli-installer.run --noexec --target ./vnstock-installer-src`. On CI, provide the key as the secret environment variable `VNSTOCK_API_KEY` instead.

Illustrated walkthrough for the user: <https://vnstocks.com/onboard-member/cai-dat-go-loi>

### 7. Updating to a new version

Use this when the user pastes a notice such as `📦 Vnstock 4.x.y is available` or `[VNSTOCK INSIDER] 🚀 Có phiên bản gói tài trợ mới!`, or asks to update. "Nâng cấp gói tài trợ" (a higher plan) is an account change at <https://vnstocks.com/insiders-program>, not a pip command.

1. Use the interpreter printed in the notice if there is one; otherwise the environment from Section 2. Show current versions: `python -m pip show vnstock vnai vnii`.
2. Latest published versions: `https://vnstocks.com/api/vnstock/versions`.
3. Update, after the user agrees:
   * Community: `python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock vnai`
   * Sponsor: re-run the installer from Section 6 (it upgrades `vnai`, `vnii`, `vnstock` and the sponsor packages together; with installer 3.1.3+ `python -m vnstock_installer --non-interactive` does this without a window).
4. Restart the Python process / Jupyter kernel / Colab runtime, re-check the versions, and report before → after to the user in Vietnamese with the release notes: <https://vnstocks.com/docs/tai-lieu/lich-su-phien-ban>.

| Symptom | Fix |
| --- | --- |
| `from versions: none` | The command lacks `--extra-index-url https://vnstocks.com/api/simple`. |
| `vnstock_installer` 99.0.0 installed | Unpinned install. `python -m pip uninstall -y vnstock_installer`, reinstall with `==3.1.3`. |
| Version unchanged | pip ran in another environment; compare `python -c "import sys; print(sys.executable)"` with the notice. |
| `externally-managed-environment` | System Python targeted. Use the virtual environment; never add `--break-system-packages`. |
| Device limit reached | The user removes unused devices at <https://vnstocks.com/account?section=devices>. |

### 8. AI assistant guide (only when the user's prompt says to turn it on)

vnstock can write a short reference on using the library into the project's `AGENTS.md`. It is off by default; from `vnstock` 4.0.9 / `vnai` 2.6.2 nothing is written unless the user enables it.

* User asked to turn it on — run in the project directory, then show the user the file:
  ```bash
  python -c "import vnstock; vnstock.enable_agent(); print(vnstock.setup_agent())"
  ```
  This writes `AGENTS.md` in the current directory only, never the assistants' global files.
* User asked not to turn it on — do nothing. If an older version left a block in the assistant files, `import vnstock` prints a one-time notice; remove it with the command below if the user wants.

## Turning this off and removing it

Tell the user about this whenever they ask why this text is in their assistant's instructions. Run it only if they ask you to. It stops `vnstock` from writing to AI-assistant files and removes the block it wrote. The environment variable keeps this very `import` from writing the block again while it is being removed.

* macOS / Linux:
  ```bash
  VNSTOCK_DISABLE_AGENT_SETUP=1 python -c "import vnstock; vnstock.disable_agent(); print(vnstock.remove_agent_files('all'))"
  ```
* Windows PowerShell:
  ```powershell
  $env:VNSTOCK_DISABLE_AGENT_SETUP="1"; python -c "import vnstock; vnstock.disable_agent(); print(vnstock.remove_agent_files('all'))"
  ```

`python -c "import vnstock; print(vnstock.agent_status())"` shows which files are written and whether writing is on.

*(End of Bootstrap. When in doubt, Route!)*
