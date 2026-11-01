# Deploy — Module III, Bài 5 & 6 (Cloud Deployment + CI/CD)

Runbook triển khai **vn-stock-swarm**. Khác `llm-engineer-demo/deploy` ở chỗ
swarm **không bootstrap GCP Compute Engine** (AGENTS: không gọi `gcloud`): chạy
local Docker Compose trên Windows, public URL bằng Cloudflare Tunnel / ngrok.
Đường SSH host (`cd.yml` + `release.sh`) là tuỳ chọn, tắt mặc định.

> Bối cảnh lựa chọn hạ tầng (Bài 5 — Cloud Landscape), cách swarm chọn:

| | Compute Engine | Cloud Run | Local compose + Tunnel | GKE |
|---|---|---|---|---|
| Dùng khi | VM liên tục, nginx/TLS tự quản | Stateless scale-to-zero | Máy nhà / lab, không mở port modem | Nhiều service orchestration |
| Ở đây | Tuỳ chọn qua `cd.yml` + SSH | ❌ stateful (postgres/qdrant/volume) | ✅ mặc định (`release.ps1` + `publish.ps1`) | quá mức |

## Hai đường ống CI — chọn một (giống demo)

| | `deploy.yml` (demo) | `cd.yml` (production) |
|---|---|---|
| Chạy ở đâu | GitHub runner + `docker compose` | SSH host + `release.sh` |
| LKG | Actions cache `src/deploy/lkg` | File `.lkg` trên host |
| Setup | Không cần VM | Clone repo trên host + SSH key |
| Mặc định | **bật** (sau CI xanh) | **tắt** (`ENABLE_SSH_DEPLOY=true`) |

**Chỉ một đường gắn vào cùng một máy production.** Xem `.github/README.md`.

Phân chia trách nhiệm (cùng ý demo `deploy.sh` vs pipeline):

- **Bootstrap / vận hành local:** `release.ps1`, `publish.ps1`, nginx — làm tay hoặc
  script trên máy bạn.
- **Mỗi lần CI xanh:** `deploy.yml` (runner) hoặc `cd.yml` (SSH) — đưa bản mới lên,
  smoke, rollback.

## Cấu trúc thư mục

```
src/deploy/
├── README.md                 # file này
├── smoke.py                  # smoke: /health → /chat (câu FPT), tuỳ chọn SSE
├── release.sh                # TRÊN host Linux: deploy <sha> / smoke / rollback / status
├── release.ps1               # TRÊN Windows local: up / smoke / rollback / status
├── publish.ps1               # Cloudflare Tunnel → HTTPS public vào nginx :80
├── nginx.conf                # reverse proxy; proxy_buffering off cho /chat & /api/
├── nginx-portfolio-watch.conf
└── docker-entrypoint.sh      # quyền volume /app/data trong container
```

**Không có** (có ở demo, swarm cố ý bỏ): `deploy.sh` / `startup.sh` /
`llm-app.service` / Secret Manager GCP — vì không dùng GCE bootstrap.

## Mapping sang demo

| Demo (`deploy/`) | Swarm (`src/deploy/`) | Giống / khác |
|---|---|---|
| `smoke.py` | `smoke.py` | Giống vai trò; swarm hỏi FPT, không ingest Qdrant |
| `release.sh` | `release.sh` + `release.ps1` | Giống API deploy/smoke/rollback/status; swarm checkout **git SHA** (compose mount source), demo đổi **image tag** |
| `nginx.conf` | `nginx.conf` | Giống: chỉ `:80`, `proxy_buffering off` cho SSE |
| `deploy.sh` (bootstrap GCE) | `publish.ps1` (Tunnel) | Cùng mục “có URL HTTPS”; khác hạ tầng |
| `llm-app.service` | `docker compose` + `restart: unless-stopped` | Compose thay systemd |
| `DEMO-CICD.md` | (chưa) | Có thể thêm sau khi drill lớp |

## Vòng lặp hằng ngày (khi dùng `deploy.yml`)

```
git push main
  └─ ci.yml           prompt lint → ruff → pytest
       └─ deploy.yml  (chỉ khi ci xanh)
            ├─ docker compose build/up backend trên runner
            ├─ smoke.py --url http://localhost:8000
            ├─ ghi LKG SHA vào cache
            └─ if smoke fail → checkout LKG → compose lại → smoke
```

Ba nguyên tắc (giống demo):

1. **Chỉ deploy khi CI xanh** — `workflow_run`, không `on: push` trần.
2. **Promote theo smoke**, không chỉ `/health` — câu FPT phải có tín hiệu hợp lệ.
3. **Rollback có đích** — LKG ghi trước / khôi phục khi smoke đỏ.

## Local nhanh (Windows)

```powershell
# Lên stack + health
powershell -File src/deploy/release.ps1 up

# Smoke
powershell -File src/deploy/release.ps1 smoke -Url "http://127.0.0.1:8000"

# Public HTTPS qua Tunnel (nginx :80)
powershell -File src/deploy/publish.ps1

# Rollback prompt + recreate + smoke
powershell -File src/deploy/release.ps1 rollback
```

## SSH production (`cd.yml`)

1. Trên host: clone repo vào `/opt/vn-stock-swarm` (hoặc `APP_DIR`), cài Docker Compose.
2. GitHub: secret `VM_SSH_KEY`; vars `VM_HOST`, `VM_USER`, `ENABLE_SSH_DEPLOY=true`.
3. Pipeline: `release.sh deploy <sha>` → smoke → rollback nếu fail.

Rollback tay khi Actions sập:

```bash
sudo APP_DIR=/opt/vn-stock-swarm /opt/vn-stock-swarm/release.sh rollback
sudo APP_DIR=/opt/vn-stock-swarm /opt/vn-stock-swarm/release.sh status
```

## Secret

Swarm local: `.env` từ `.env.example` (không commit key). Docker image **không**
bake secret (Dockerfile chỉ `requirements.txt`). Đường GCE Secret Manager của
demo **chưa** gắn — nếu sau này lên VM GCP, làm theo Bài 5 như demo.
