"""AST Import Boundary Checker for Clean Architecture Microservices.

Kiểm tra ranh giới phân lập giữa các khối:
1. `src/web_backend` KHÔNG import từ `src/ai_backend`.
2. `src/web_backend` KHÔNG import `openai`, `langgraph`, `langchain`.
3. `src/web_backend` KHÔNG import từ thư mục cũ đã xóa `src/backend`.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check_boundaries() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    root_dir = Path(__file__).resolve().parent.parent
    web_backend_dir = root_dir / "src" / "web_backend"

    if not web_backend_dir.exists():
        print(f"[ERROR] Không tìm thấy thư mục {web_backend_dir}")
        return 1

    forbidden_roots = {"ai_backend", "openai", "langgraph", "langchain", "backend"}
    violations: list[str] = []
    scanned_files = 0

    for py_file in web_backend_dir.rglob("*.py"):
        scanned_files += 1
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as exc:
            violations.append(f"Lỗi cú pháp tại {py_file}: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    if top_level in forbidden_roots:
                        rel_path = py_file.relative_to(root_dir)
                        violations.append(
                            f"{rel_path}:{node.lineno} -> import {alias.name} (cấm '{top_level}')"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_level = node.module.split(".")[0]
                    if top_level in forbidden_roots:
                        rel_path = py_file.relative_to(root_dir)
                        violations.append(
                            f"{rel_path}:{node.lineno} -> from {node.module} import ... (cấm '{top_level}')"
                        )

    print(f"=== KIỂM TRA RANH GIỚI IMPORT (AST BOUNDARY CHECK) ===")
    print(f"- Thư mục quét: {web_backend_dir}")
    print(f"- Số file Python đã quét: {scanned_files}")
    print(f"- Các module bị cấm: {', '.join(sorted(forbidden_roots))}")

    if violations:
        print(f"\n[FAIL] Phát hiện {len(violations)} vi phạm ranh giới:")
        for v in violations:
            print(f"  [X] {v}")
        return 1

    print("\n[PASS] 100% sạch sẽ! Không phát hiện vi phạm ranh giới nào trong src/web_backend.")
    return 0


if __name__ == "__main__":
    sys.exit(check_boundaries())
