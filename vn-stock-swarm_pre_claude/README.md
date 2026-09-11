# VN Stock Swarm

Crawler chứng khoán Việt Nam (HOSE/HNX/UPCOM) triển khai theo **Swarm dị chủng**
(heterogeneous multi-agent) + **Router 2 tầng** (post-crawl) + **Hierarchical Query
Coordinator** (Orchestrator–Worker, 5 agent cùng cấp, có HITL bắt buộc khi ghi dữ liệu
mới). Đây là bản viết lại của `distributed-crawler-swarm` sau phản hồi: bản cũ chỉ có
một loại agent giống hệt nhau tự chia domain bằng hash — đó là **Partitioned Worker
Pool**, chưa phải Swarm đúng nghĩa. Swarm chỉ có ý nghĩa khi các agent **khác chuyên môn
thật** và **handoff cho nhau tuỳ tình huống**.

Toàn bộ sơ đồ kiến trúc chi tiết (SVG + Mermaid) nằm trong `swarm-handoff-map_6.html`
đi kèm project — README này tóm tắt lại 3 sơ đồ đó bằng chữ.

## Trả lời trực tiếp 2 câu hỏi

**"Chia crawl thành mấy loại agent khác nhau?"** — 5 loại: `ScoutAgent` (mặc định),
`RenderAgent` (trang JS nặng), `DocumentAgent` (PDF/DOCX), `ApiAgent` (JSON/API),
`StealthAgent` (site chặn bot mạnh).

**"Khi nào một agent handoff quyền điều khiển cho agent khác?"** — hai loại điều kiện:
*trước khi fetch* (đoán từ đuôi/path URL — `pre_route.py`), và *sau khi fetch* (theo tín
hiệu nội dung thật: Content-Type sai dự đoán, body rỗng kiểu SPA, hoặc bị chặn lặp lại —
`handoff.py`).

## Nguồn dữ liệu

HOSE/HNX/UPCOM. Bảng giá + tin tức: `cafef.vn`, `vietstock.vn`. Báo cáo tài chính (PDF):
trang IR từng công ty, hoặc `hnx.vn`/`hsx.vn`. Mã ví dụ để test: **VNM, HPG, FPT, VCB**.

## Kiến trúc — Sơ đồ 1: Swarm dị chủng & handoff động

```
                    URL mới phát hiện
                            │
        ┌───────────────────┼───────────────────┐
   .pdf │              mặc định (HTML)      /api/ │ .json
        ▼                   ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ DocumentAgent  │   │  ScoutAgent    │   │   ApiAgent     │
│ PDF báo cáo    │◄──┤ (đã có, HTML   ├──►│ JSON/API giá   │
│ tài chính      │   │  nhẹ, mặc định)│   │ real-time      │
└───────────────┘   └───────┬───────┘   └───────────────┘
  ▲ Content-Type PDF         │ SPA rỗng          │ 403/429 lặp lại
  │ ngoài dự đoán            ▼                    ▼ (cả domain)
  │                  ┌───────────────┐   ┌───────────────┐
  │                  │  RenderAgent   │   │  StealthAgent  │
  │                  │ headless       │   │ proxy rotation │
  │                  │ browser (SPA)  │   │ + pacing chậm  │
  │                  └───────────────┘   └───────────────┘
  └── mỗi loại agent tự chia domain nội bộ bằng rendezvous hashing ──┘
```

| Loại agent | Chuyên môn | Khi nào agent khác handoff cho nó |
|---|---|---|
| `ScoutAgent` | Fetch HTML nhẹ — bảng giá + tin tức (`cafef.vn`, `vietstock.vn`) | Mặc định — URL mới luôn thử ScoutAgent trước |
| `RenderAgent` | Headless browser (Playwright) — render bảng giá JS-nặng (SSI iBoard, TCBS) | ScoutAgent thấy body gần rỗng kiểu SPA shell |
| `DocumentAgent` | Trích text PDF báo cáo tài chính (pypdf) | Trước fetch: đuôi `.pdf`. Sau fetch: Content-Type PDF ngoài dự đoán |
| `ApiAgent` | JSON, pagination — API giá real-time (SSI/TCBS-style) | Trước fetch: path `/api/`, `.json`. Sau fetch: response là JSON ngoài dự đoán |
| `StealthAgent` | Proxy rotation, pacing chậm hơn (x5 mặc định) | ScoutAgent bị chặn (403/429) lặp lại N lần trên 1 domain → nhận cả domain |

**Domain ownership** trong mỗi loại agent dùng *rendezvous (HRW) hashing* (`hashing.py`)
— mỗi loại agent có tập "nodes alive" **riêng** (`membership.py`, namespaced theo
`agent_type`), vì một `ScoutAgent` và một `DocumentAgent` không bao giờ tranh nhau cùng
domain.

**Gossip stream** cũng namespaced theo loại: `url:discovered:{agent_type}` thay vì 1
stream chung — `pre_route.guess_agent_type()` quyết định publish vào stream nào. Handoff
= publish lại URL vào stream của agent đích + ack message hiện tại.

## Kiến trúc — Sơ đồ 2: hai tầng Router sau khi crawl

"Nhìn 1 item, phân loại, định tuyến sang đúng 1 handler" là **Router pattern**. Có 2 tầng
nối tiếp:

```
fetch_page(url) → RawResponse
        │
        ▼
┌───────────────┐   theo Content-Type + sniff nội dung
│ ContentRouter │   (router.py)
└───────┬───────┘   Sitemap · Pdf · Json · Html · Binary
        ▼
   RouteResult (title, links, metadata)
        │
        ▼
┌───────────────┐   giá → time-series; tin → match mã CP
│  Sink Router   │   (sink_router.py)
└───────┬───────┘
        ▼
┌─────────────┬──────────────────┬─────────────┐
│  Giá CP     │  Tin tức theo mã  │  Tin chung   │
│(time-series)│ (staging, chờ    │ (không match)│
│             │  HITL duyệt)     │              │
└─────────────┴──────────────────┴─────────────┘
```

`ContentRouter` (tầng 1) chọn parser theo loại nội dung. `SinkRouter` (tầng 2) chọn *bảng
lưu trữ* theo ý nghĩa nghiệp vụ: kết quả từ `ApiAgent`/handler JSON luôn là giá; kết quả
HTML được so khớp keyword (`stock_symbols.py`) với danh sách mã CP + tên công ty — match
được ≥1 mã → *Tin tức theo mã*; không match được mã nào → *Tin chung* (hợp lệ, không phải
lỗi — ví dụ tin vĩ mô).

Dữ liệu được lưu vào **SQLite** (`sink_store.py`). Bảng `prices` và `news_general` ghi
thẳng lúc crawl. Tin theo mã thì **không** — nó vào bảng staging `news_pending` trước;
chỉ "thăng cấp" sang bảng `news` chính thức sau khi qua HITL của `DBAgent` (xem Sơ đồ 3d
bên dưới). Nếu tin theo mã được ghi thẳng như giá, bước duyệt của con người sẽ không bao
giờ có gì để duyệt — mâu thuẫn với chính mục đích tồn tại của HITL. `ResultStore` (JSONL)
vẫn ghi song song làm audit trail thô cho mọi trang đã crawl.

## Kiến trúc — Sơ đồ 3d: Hierarchical Query Coordinator, 5 agent + HITL

Khác Router (luôn chọn đúng 1 nhánh cố định), `QueryCoordinator` (`query/coordinator.py`)
là hub duy nhất điều phối **5 agent cùng cấp** (`query/agents/`) theo **2 đợt cố định**,
đúng thứ tự phụ thuộc dữ liệu — không agent nào nói thẳng với agent khác:

```
User hỏi
  │  parse ticker + intent
  ▼
ĐỢT 1 — song song (asyncio.gather)
  ├─ PriceAgent   tìm giá biến động, gọi Swarm nếu giá cũ, tính %
  ├─ NewsAgent    chỉ search tin (Swarm → ContentRouter → SinkRouter), KHÔNG chấm sentiment
  └─ DBAgent(đọc) lịch sử giá + tin ĐÃ DUYỆT — luôn tự động, không HITL
  │
  ▼  hub gói Price + News lại
ĐỢT 2a — EvalAgent   sentiment 3 lớp theo từ khoá, đủ-bằng-chứng?, giá có khớp tin?
  │
  ▼  DBAgent có tin MỚI (ở news_pending, chưa duyệt)?
  │     có → DỪNG, trả status="pending_approval" — chờ POST /approve
  │     không → chạy tiếp luôn
  ▼
ĐỢT 2b — SynthesisAgent   ghép 4 báo cáo thành câu trả lời có cấu trúc, không tự chấm lại
  │
  ▼
Hub trả lời user + trace đầy đủ (mọi ý truy được về đúng 1 agent)
```

| Agent | Nhiệm vụ | Chạy khi nào |
|---|---|---|
| `PriceAgent` | Đọc độ mới giá trong SinkStore; cũ thì gọi Swarm (Sơ đồ 1) crawl lại; tính % biến động | Đợt 1, song song |
| `NewsAgent` | Gọi Swarm crawl tin, đọc lại tin thô (đã duyệt + đang chờ duyệt) — không tự đánh giá | Đợt 1, song song |
| `DBAgent` | ĐỌC lịch sử tự động; GHI chỉ soạn `PendingWrite`, chờ HITL mới commit | Đợt 1 (đọc) + sau `/approve` (ghi) |
| `EvalAgent` | Sentiment từng tin (tiêu cực/tích cực/trung lập theo từ khoá), đủ bằng chứng?, giá có khớp thiên hướng tin không | Đợt 2a, sau khi có Price + News |
| `SynthesisAgent` | Ghép 4 báo cáo thành câu trả lời tiếng Việt có cấu trúc + trace | Đợt 2b, sau khi có Eval |

### HITL — 2 endpoint

`POST /ask` chạy hết đợt 1 + đợt 2a. Nếu `DBAgent.prepare_pending_writes()` phát hiện có
tin trong `news_pending` chưa từng qua duyệt, Coordinator **dừng trước Synthesis**, trả
`status="pending_approval"` kèm `request_id` + danh sách `pending_writes`. Client gọi tiếp
`POST /approve` với `{request_id, approve}`:

- `approve=True` → `DBAgent.commit_pending_writes()` thăng cấp tin từ `news_pending` sang
  `news` chính thức, rồi Coordinator chạy nốt Synthesis, trả câu trả lời hoàn chỉnh.
- `approve=False` → chỉ log, không ghi gì cả — Coordinator vẫn chạy Synthesis với dữ liệu
  đã có, trả lời user bình thường (từ chối không chặn luồng hỏi–đáp).

Nếu không có gì cần ghi (chỉ đọc), `/ask` chạy thẳng 1 lượt và trả `status="answered"`
ngay — không bắt người dùng duyệt việc không tồn tại.

State của 1 request đang chờ duyệt (`_pending_requests`) sống **trong bộ nhớ tiến trình**
của `QueryCoordinator`, dọn theo TTL (`PENDING_APPROVAL_TTL_SECONDS`) — xem mục "Giới hạn
đã biết".

Ví dụ trace (mã HPG, câu hỏi "Tại sao giá HPG giảm hôm nay?", đã có tin mới chờ duyệt):

```json
{
  "status": "pending_approval",
  "request_id": "a1b2c3...",
  "symbol": "HPG",
  "pending_writes": [
    {"symbols": ["HPG"], "title": "HPG giảm sàn phiên sáng", "url": "https://cafef.vn/..."}
  ],
  "trace": [
    {"step": "extract_symbol", "detail": "mã: HPG"},
    {"step": "price_agent", "detail": "giá cập nhật 180s trước → dùng luôn, không crawl lại"},
    {"step": "news_agent", "detail": "chưa có tin gần đây → đã gọi Swarm crawl + match mã mới"},
    {"step": "db_agent_read", "detail": "đọc 5 phiên giá + 0 tin đã lưu (tự động)"},
    {"step": "db_agent_write", "detail": "1 tin mới cần ghi → chờ HITL duyệt qua POST /approve"}
  ]
}
```

## Chạy thử

```bash
cp .env.example .env
docker compose up --build
```

Seed URL nạp qua service `seed-loader` (chạy 1 lần, tự phân loại agent qua
`pre_route.guess_agent_type`). Kết quả crawl thô ghi vào `./data/results.jsonl`, dữ liệu
theo sink ghi vào `./data/sink.db` (SQLite). Log JSON structured ra stdout mỗi agent.

Hỏi–đáp qua HTTP (luồng đầy đủ, có tin mới cần duyệt):

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Tại sao giá HPG giảm hôm nay?"}'
# → {"status": "pending_approval", "request_id": "...", ...}

curl -X POST http://localhost:8080/approve \
  -H "Content-Type: application/json" \
  -d '{"request_id": "...", "approve": true}'
# → {"status": "answered", "answer": "...", ...}
```

`render` (RenderAgent) build bằng `Dockerfile.render` (base
`mcr.microsoft.com/playwright/python`, browser binaries có sẵn) — image riêng, nặng hơn,
tách khỏi các agent còn lại để `scout`/`document`/`api`/`stealth`/`query-api` dùng chung
một image nhẹ (`Dockerfile`).

## Cấu trúc code

```
src/
  config.py             # Settings (pydantic) — freshness threshold, render/stealth/HITL TTL
  logging_config.py      # Structured logging (structlog)
  hashing.py               # Rendezvous hashing cho domain ownership
  membership.py             # Heartbeat + danh sách agent sống, namespaced theo agent_type
  redis_client.py            # Kết nối Redis (async)
  dedup.py                     # Dedup URL bằng SADD nguyên tử
  robots.py                      # Fetch & cache robots.txt
  rate_limiter.py                  # Politeness per-domain, hỗ trợ pace_multiplier (StealthAgent)
  fetcher.py                         # HTTP fetch thô (RawResponse)
  render_fetcher.py                    # Playwright headless fetch — trả về RawResponse
  urls.py                                # registered_domain + origin
  pre_route.py                             # Định tuyến trước-fetch: URL → loại agent
  handoff.py                                 # Quyết định handoff sau-fetch + Redis state
  router.py                                    # ContentRouter tầng 1 — 5 handler
  sink_router.py                                 # SinkRouter tầng 2 — phân loại giá/tin/tin chung
  stock_symbols.py                                 # Danh sách mã CP + keyword match
  storage.py                                         # ResultStore — JSONL audit log
  sink_store.py                                        # SinkStore — SQLite (prices/news/news_pending/news_general)
  agents/
    base.py                                             # BaseCrawlerAgent — vòng lặp chung, handoff, sink routing
    scout.py / render.py / document.py / api.py / stealth.py   # 5 loại agent cụ thể (Sơ đồ 1)
  query/
    coordinator.py                                         # QueryCoordinator — hub Hierarchical, 2 đợt (Sơ đồ 3d)
    api.py                                                   # FastAPI: POST /ask, POST /approve
    agents/
      _polling.py                                              # poll-có-timeout dùng chung
      price_agent.py / news_agent.py / eval_agent.py /            # 5 agent cùng cấp
      db_agent.py / synthesis_agent.py
  seed_loader.py                                             # Publish seed, tự phân loại agent type
  main.py                                                      # Entrypoint — chọn agent theo AGENT_TYPE env
tests/                                                          # fakeredis + httpx.MockTransport/ASGITransport
  test_query_agents/                                             # Test riêng từng agent tầng Hierarchical
```

## Giới hạn đã biết / hướng mở rộng

- `stock_symbols.py` chỉ có 4 mã demo (VNM, HPG, FPT, VCB) — mở rộng danh sách alias là đủ,
  không cần đổi logic `match_symbols`.
- Cơ chế chờ crawl mới của Price/NewsAgent là polling có timeout (không dùng Pub/Sub) —
  đơn giản, đủ cho demo trực tiếp, nhưng lãng phí một chút CPU so với event-driven.
- State HITL (`_pending_requests` trong `QueryCoordinator`) sống **trong bộ nhớ tiến
  trình** — không sống sót qua restart, không chia sẻ giữa nhiều tiến trình `query-api`.
  Chấp nhận được cho demo Q&A đơn tiến trình; triển khai thật cần chuyển sang Redis/DB.
- `EvalAgent` chấm sentiment bằng khớp từ khoá đơn giản (danh sách cố định trong
  `eval_agent.py`) cho mục đích demo, không phải mô hình NLP thật.
- `StealthAgent` chỉ rotate qua danh sách proxy cấu hình tĩnh (`STEALTH_PROXIES`) và giảm tốc
  độ — không giải CAPTCHA, không giả lập fingerprint trình duyệt nâng cao.
- `RenderAgent` cần browser binaries của Playwright (image riêng `Dockerfile.render`) — không
  chạy được trong image chính, cần build/pull riêng.
