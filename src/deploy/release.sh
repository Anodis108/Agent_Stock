#!/usr/bin/env bash
# Release/rollback trên máy chủ — Module III, Bài 6, Section 4.
#
# Chạy TRÊN host (cd.yml gọi qua SSH). Tách khỏi YAML vì:
#   1. Rollback phải gõ tay được khi GitHub Actions sập: ./release.sh rollback
#   2. Bash trong file thì `bash -n` được; bash trong YAML khó test.
#
# Swarm khác demo legal-RAG: compose mount source (./src), không trỏ image tag
# `latest`. "Deploy" = checkout git SHA rồi recreate container. "Rollback" =
# checkout lại SHA last-known-good.
#
#   ./release.sh deploy <git_sha>
#   ./release.sh smoke [path_smoke.py]
#   ./release.sh rollback
#   ./release.sh status
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vn-stock-swarm}"
CURRENT_FILE="$APP_DIR/.current"
LKG_FILE="$APP_DIR/.lkg"
SMOKE_DEFAULT="$APP_DIR/src/deploy/smoke.py"

log() { echo "==> $*"; }
die() { echo "::error::$*" >&2; exit 1; }

wait_healthy() {
    local tries=${1:-45}
    for _ in $(seq "$tries"); do
        if curl -fsS --max-time 3 http://127.0.0.1:8000/health >/dev/null 2>&1 \
            && curl -fsS --max-time 3 http://127.0.0.1:8001/health >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

write_tag() {
    echo "$2" | tee "$1" >/dev/null
}

do_deploy() {
    local sha="$1"
    [ -n "$sha" ] || die "thiếu git SHA"

    cd "$APP_DIR"
    local old=""
    [ -f "$CURRENT_FILE" ] && old="$(cat "$CURRENT_FILE")"

    log "Deploy $sha (đang chạy: ${old:-chưa có})"

    if [ -n "$old" ] && [ "$old" != "$sha" ]; then
        write_tag "$LKG_FILE" "$old"
        log "Đã ghi last-known-good = $old"
    fi

    git fetch --all --tags
    git checkout --force "$sha"
    docker compose up -d --force-recreate backend ai_backend

    write_tag "$CURRENT_FILE" "$sha"

    if wait_healthy 45; then
        log "Healthy với $sha"
    else
        die "KHÔNG healthy sau ~90s với $sha (để CD chạy smoke rồi mới rollback)"
    fi
}

do_rollback() {
    [ -f "$LKG_FILE" ] || die "chưa có last-known-good — không rollback được"
    local lkg
    lkg="$(cat "$LKG_FILE")"
    [ -n "$lkg" ] || die "file .lkg rỗng"

    log "Rollback về last-known-good: $lkg"
    cd "$APP_DIR"
    git checkout --force "$lkg"
    docker compose up -d --force-recreate backend ai_backend
    write_tag "$CURRENT_FILE" "$lkg"
    wait_healthy 45 || die "Rollback xong nhưng vẫn không healthy"
    log "Đã rollback về $lkg"
}

do_smoke() {
    local src="${1:-$SMOKE_DEFAULT}"
    [ -f "$src" ] || die "không thấy $src"
    cd "$APP_DIR"
    PYTHONPATH=src python "$src" --url http://127.0.0.1:8000
}

do_status() {
    cd "$APP_DIR"
    echo "current = $(cat "$CURRENT_FILE" 2>/dev/null || echo '(chưa có)')"
    echo "lkg     = $(cat "$LKG_FILE" 2>/dev/null || echo '(chưa có)')"
    docker compose ps
}

case "${1:-}" in
    deploy)   shift; do_deploy "${1:-}" ;;
    smoke)    shift; do_smoke "${1:-}" ;;
    rollback) do_rollback ;;
    status)   do_status ;;
    *) die "dùng: $0 {deploy <sha>|smoke [path]|rollback|status}" ;;
esac
