#!/bin/sh
set -e
# Volume /app/data có thể mount với owner root — sửa quyền trước khi chạy appuser.
if [ -d /app/data ]; then
  chown -R appuser:appuser /app/data 2>/dev/null || true
fi
exec gosu appuser "$@"
