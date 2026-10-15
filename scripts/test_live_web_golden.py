#!/usr/bin/env python3
"""Script kiểm thử thực tế live web product VN Stock Swarm với toàn bộ bộ Golden Set v6."""

import json
import sys
import time
import urllib.request
import urllib.error
import yaml
from pathlib import Path

# Cấu hình UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "resources" / "eval" / "golden_dataset.yaml"
WEB_URL = "http://127.0.0.1:8000/chat"


def post_web_chat(question: str, user_id: str = "default", timeout: float = 60.0) -> dict:
    """Gửi câu hỏi trực tiếp tới Web Backend (port 8000) qua HTTP POST."""
    payload = json.dumps({"question": question, "user_id": user_id}).encode("utf-8")
    req = urllib.request.Request(
        WEB_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        elapsed = round(time.perf_counter() - t0, 2)
        data = json.loads(resp.read().decode("utf-8"))
        data["_elapsed_s"] = elapsed
        return data


def run_live_golden_eval():
    print("=" * 80)
    print("🚀 BẮT ĐẦU KIỂM THỬ THỰC TẾ LIVE WEB PRODUCT VỚI TOÀN BỘ BỘ GOLDEN SET V6")
    print(f"Target URL: {WEB_URL}")
    print(f"Golden Dataset: {GOLDEN_PATH}")
    print("=" * 80)

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    cases = doc.get("cases", [])
    total = len(cases)
    passed = 0
    failed = 0
    results = []

    for idx, case in enumerate(cases, 1):
        cid = case["id"]
        q = case["question"]
        slice_type = case.get("slice", {}).get("type", "unknown")
        must_inc = case.get("must_include", [])
        must_not_inc = case.get("must_not_include", [])

        print(f"\n[{idx}/{total}] [{slice_type.upper()}] Case ID: {cid}")
        print(f"  ❓ Câu hỏi: {q}")

        try:
            resp = post_web_chat(q)
            ans = resp.get("answer", "")
            route = resp.get("route", "")
            elapsed = resp.get("_elapsed_s", 0)
            ans_lower = ans.lower()

            # Kiểm tra must_include
            missing_inc = [inc for inc in must_inc if inc.lower() not in ans_lower]

            # Kiểm tra must_not_include
            violating_not_inc = [not_inc for not_inc in must_not_inc if not_inc.lower() in ans_lower]

            errors = []
            if not ans.strip():
                errors.append("Câu trả lời rỗng!")
            if "hệ thống chat chưa được cấu hình" in ans_lower:
                errors.append("Lỗi cấu hình chat (chưa nhận được backend AI)!")
            if missing_inc:
                errors.append(f"Thiếu từ bắt buộc: {missing_inc}")
            if violating_not_inc:
                errors.append(f"Chứa từ cấm: {violating_not_inc}")

            is_ok = len(errors) == 0
            if is_ok:
                passed += 1
                status_str = "✅ PASS"
            else:
                failed += 1
                status_str = "❌ FAIL"

            print(f"  {status_str} (⏱ {elapsed}s | Route: {route})")
            ans_preview = ans.replace("\n", " ")[:160] + ("..." if len(ans) > 160 else "")
            print(f"  💬 Trả lời: {ans_preview}")
            if errors:
                for err in errors:
                    print(f"     ⚠️ {err}")

            results.append({
                "id": cid,
                "slice": slice_type,
                "question": q,
                "passed": is_ok,
                "elapsed_s": elapsed,
                "route": route,
                "errors": errors,
                "answer": ans,
            })

        except Exception as exc:
            failed += 1
            print(f"  ❌ EXCEPTION: {exc}")
            results.append({
                "id": cid,
                "slice": slice_type,
                "question": q,
                "passed": False,
                "elapsed_s": 0,
                "route": "error",
                "errors": [str(exc)],
                "answer": "",
            })

    print("\n" + "=" * 80)
    print("📊 TỔNG HỢP KẾT QUẢ KIỂM THỬ THỰC TẾ TRÊN WEB PRODUCT")
    print(f"  Tổng số câu hỏi : {total}")
    print(f"  Đạt chuẩn (PASS): {passed}/{total} ({round(passed / total * 100, 1)}%)")
    print(f"  Thất bại  (FAIL): {failed}/{total}")
    print("=" * 80)

    # Chi tiết theo slice
    slices = {}
    for r in results:
        s = r["slice"]
        slices.setdefault(s, {"total": 0, "pass": 0})
        slices[s]["total"] += 1
        if r["passed"]:
            slices[s]["pass"] += 1

    for s, stats in sorted(slices.items()):
        pct = round(stats["pass"] / stats["total"] * 100, 1)
        print(f"  - Slice {s.ljust(15)}: {stats['pass']}/{stats['total']} ({pct}%)")

    return results, passed, failed


if __name__ == "__main__":
    _, p, f = run_live_golden_eval()
    sys.exit(0 if f == 0 else 1)
