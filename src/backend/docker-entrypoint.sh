#!/bin/sh
set -e
# Volume /app/data có thể mount với owner root — sửa quyền trước khi chạy appuser.
# /app/src mount read-only → appuser cần HOME/config ghi được (vnstock, matplotlib).
if [ -d /app/data ]; then
  mkdir -p /app/data/.config /app/data/.matplotlib /app/data/charts 2>/dev/null || true
  chown -R appuser:appuser /app/data 2>/dev/null || true
fi
# gosu đặt HOME theo passwd (/app, read-only) — ép lại thư mục ghi được trên volume.
APP_HOME="${HOME:-/app/data}"
APP_XDG="${XDG_CONFIG_HOME:-/app/data/.config}"
APP_MPL="${MPLCONFIGDIR:-/app/data/.matplotlib}"
exec gosu appuser env HOME="$APP_HOME" XDG_CONFIG_HOME="$APP_XDG" MPLCONFIGDIR="$APP_MPL" "$@"
