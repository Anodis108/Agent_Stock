# Incident Playbook: Provider Outage

## Triệu chứng

- HTTP 429/503 từ OpenAI/Ollama/vLLM
- Log: `RateLimitError`, `APIConnectionError`, `All keys exhausted`
- Latency P95 > 30s, error rate > 5%
- Eval gate CI fail do timeout

## Phát hiện nhanh

```bash
curl -s http://localhost:8000/health
PYTHONPATH=src python scripts/drill_fallback_provider.py
```

Langfuse: filter traces `level=ERROR` last 1h.

## Nguyên nhân thường gặp

1. API key hết quota / bị revoke
2. Primary backend (openai) outage
3. Ollama/vLLM container crash (Docker)
4. Network / DNS trên VM

## Hành động khẩn cấp (10 phút)

### 1. Fallback provider chain

Đặt trong `.env`:

```env
LLM_FALLBACK_BACKENDS=ollama,openai
LLM_BACKEND=openai
```

Restart API:

```bash
docker compose restart api
```

### 2. Key rotation

Thêm key dự phòng vào `OPENAI_API_KEYS` (comma-separated). Pool tự rotate.

### 3. Local Ollama (nếu cloud down)

```bash
docker compose --profile ollama up -d ollama
# .env: LLM_BACKEND=ollama LLM_BASE_URL=http://ollama:11434/v1
```

### 4. Giảm tải

- Bật exact + semantic cache (`EXACT_CACHE_ENABLED=true`)
- Giảm `LLM_MODEL_CASCADE` — chỉ dùng 1 model nhẹ
- Tạm tắt eval gate trên PR nếu CI block (chỉ khi emergency)

## Drill định kỳ

```bash
PYTHONPATH=src python scripts/drill_fallback_provider.py
PYTHONPATH=src python scripts/drill_cost_alert.py
```

Chạy hàng tuần trên staging.

## Rollback LKG (GitHub Actions cd.yml)

1. Actions → CD workflow → run gần nhất → artifact `lkg-eval-cache`
2. Hoặc checkout tag/commit LKG: `git checkout <last-green-sha>`
3. `docker compose up --build -d`

## Escalation

- Cả primary + fallback fail > 15 phút → thông báo user maintenance
- Chi phí spike do retry loop → xem `incident-playbook-cost-spike.md`
