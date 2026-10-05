#!/usr/bin/env python3
"""Runner đánh giá toàn diện tổng hợp Golden v5 và Golden v6 và xuất báo cáo Excel (.xlsx).

Tạo file Excel chuyên nghiệp với 2 sheets:
1. Tong_Hop_Danh_Gia: Bảng chi tiết toàn bộ 60 cases (STT, Dataset, Case ID, Slice, Câu hỏi,
   Câu trả lời, Pass/Fail, Pipeline Trace, Độ trễ, Tokens, Observation/Giá/Tin, Đánh giá câu trả lời).
2. Tong_Quan_Dashboard: Thống kê tổng hợp KPI, Pass Rate, phân rã theo Dataset & Slice, Token & Latency.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(5):
        if (p / "specs").is_dir() or (p / "pyproject.toml").is_file():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[3]


ROOT = _find_project_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from backend.api.deps import get_app_deps
from backend.eval.run import (
    GOLDEN_V5_PATH,
    GOLDEN_V6_PATH,
    CaseEvalResult,
    eval_one_case,
    load_golden_dataset,
    make_answer_fn,
)
from backend.eval.run_detailed import (
    CachedNewsSource,
    CachedPriceSource,
    TokenTracker,
    _hooked_chat_parsed,
    _tracker,
    extract_pipeline_trace,
    install_completion_hooks,
    uninstall_completion_hooks,
)
from backend.shared.settings import settings


def extract_observations(steps: list[dict], case_output: str) -> str:
    """Trích xuất các dữ liệu quan sát được từ pipeline steps (thị giá, tin tức, chart, route, ...)."""
    obs_parts: list[str] = []
    prices: list[str] = []
    news_titles: list[str] = []
    chart_info: str | None = None
    route_info: str | None = None
    entities: list[str] = []

    for s in steps:
        name = s.get("name") or s.get("tool") or ""
        out = s.get("output") or {}
        inp = s.get("input") or {}

        if name == "rewrite_question":
            sym = out.get("symbol")
            syms = out.get("symbols") or []
            all_syms = set([sym] + list(syms)) if sym else set(syms)
            all_syms = [x for x in all_syms if x]
            if all_syms:
                entities.extend(all_syms)

        elif name == "supervisor":
            route = out.get("route")
            agents = out.get("agents")
            if route:
                route_info = f"Route: {route} (Gọi: {', '.join(agents) if agents else 'none'})"

        elif name == "price_agent":
            sym = inp.get("symbol") or out.get("symbol")
            close = out.get("latest_close") or out.get("price") or out.get("close")
            chg = out.get("change_pct")
            detail = s.get("detail", "")
            if close is not None:
                chg_str = f" ({chg:+.2f}%)" if chg is not None else ""
                prices.append(f"{sym}: {close}{chg_str}")
            elif detail and "close=" in detail:
                prices.append(detail)

        elif name == "news_agent":
            items = out.get("news") or out.get("articles") or []
            if isinstance(items, list) and items:
                news_titles.append(f"{len(items)} tin tức doanh nghiệp")
            elif s.get("detail"):
                news_titles.append(str(s.get("detail"))[:60])

        elif name == "chart_agent":
            if out.get("success"):
                chart_info = f"Biểu đồ kỹ thuật: {out.get('url') or 'Đã tạo file PNG'}"
            elif out.get("error"):
                chart_info = f"Lỗi biểu đồ: {out.get('error')}"

        elif name == "portfolio_watch_agent":
            nav = out.get("nav")
            wl_cnt = out.get("watchlist_count")
            p_parts = []
            if nav is not None:
                p_parts.append(f"NAV={nav:,.0f}đ")
            if wl_cnt is not None:
                p_parts.append(f"Watchlist={wl_cnt} mã")
            if p_parts:
                obs_parts.append("Danh mục: " + ", ".join(p_parts))

    if entities:
        unique_syms = sorted(list(set(entities)))
        obs_parts.append(f"Mã trích xuất: {', '.join(unique_syms)}")
    if route_info:
        obs_parts.append(route_info)
    if prices:
        obs_parts.append("Thị giá quan sát: " + "; ".join(prices))
    if news_titles:
        obs_parts.append("Tin tức: " + "; ".join(news_titles))
    if chart_info:
        obs_parts.append(chart_info)

    if not obs_parts:
        return "Không ghi nhận dữ liệu ngoại vi (xử lý trực tiếp)."
    return " | ".join(obs_parts)


def format_evaluation_details(c: dict, res: CaseEvalResult) -> str:
    """Tổng hợp chi tiết đánh giá câu trả lời (Rule check, LLM judge, lý do)."""
    reasons: list[str] = []

    # Rule-based check
    must_inc = c.get("must_include") or []
    must_not = c.get("must_not_include") or []
    rule_ok = res.rule.passed

    rule_parts = []
    if must_inc:
        if res.rule.missing:
            rule_parts.append(f"Thiếu từ bắt buộc: {res.rule.missing}")
        else:
            rule_parts.append(f"Đã có đủ từ khóa: {must_inc}")
    if must_not:
        if res.rule.forbidden_found:
            rule_parts.append(f"Vi phạm từ cấm: {res.rule.forbidden_found}")
        else:
            rule_parts.append(f"Không dính từ cấm: {must_not}")

    if rule_parts:
        reasons.append("Kiểm tra từ khóa: " + "; ".join(rule_parts))

    # LLM Judge check
    judge = res.judge
    if hasattr(judge, "skipped") and not judge.skipped and judge.score:
        sc = judge.score
        c_val = getattr(sc, "correctness", "N/A")
        comp_val = getattr(sc, "completeness", "N/A")
        g_val = getattr(sc, "grounding", "N/A")
        ov_val = getattr(sc, "overall", None)
        ov_str = f" | Tổng điểm: {ov_val:.1f}/5" if ov_val is not None else ""
        judge_info = f"LLM Judge: [Chính xác: {c_val}/5, Đầy đủ: {comp_val}/5, Căn cứ: {g_val}/5{ov_str}]"
        if getattr(sc, "reasoning", ""):
            judge_info += f" - Nhận xét: {sc.reasoning}"
        reasons.append(judge_info)
    elif hasattr(judge, "skip_reason") and judge.skip_reason:
        reasons.append(f"LLM Judge: Bỏ qua ({judge.skip_reason})")

    # Task success check
    ts = res.task_success
    if ts and not ts.skipped and ts.result:
        ts_ok = ts.result.success
        reasons.append(f"Task Success: {'Đạt' if ts_ok else 'Không đạt'} ({ts.result.reasoning or ''})")

    # Final conclusion
    status_str = "ĐẠT CHUẨN (PASS)" if res.passed else "KHÔNG ĐẠT (FAIL)"
    reasons.append(f"Kết luận: {status_str}")

    return "\n".join(reasons)


def run_all_evaluations(
    limit: int | None = None,
    delay: float = 0.3,
    skip_judge: bool = False,
) -> list[dict[str, Any]]:
    """Tải và chạy đánh giá toàn bộ các câu hỏi từ cả golden_v5 và golden_v6."""
    deps = get_app_deps()
    cached_price = CachedPriceSource(deps.price_source)
    cached_news = CachedNewsSource(deps.news_source)

    # Load v5
    v5_path = GOLDEN_V5_PATH if GOLDEN_V5_PATH.is_file() else (ROOT / "resources" / "eval" / "golden_v5.yaml")
    v6_path = GOLDEN_V6_PATH if GOLDEN_V6_PATH.is_file() else (ROOT / "resources" / "eval" / "golden_v6_comprehensive.yaml")

    data_v5 = load_golden_dataset(v5_path)
    data_v6 = load_golden_dataset(v6_path)

    cases_v5 = data_v5.get("cases") or []
    cases_v6 = data_v6.get("cases") or []

    all_cases: list[tuple[str, dict]] = []
    for c in cases_v5:
        all_cases.append(("Golden v5", c))
    for c in cases_v6:
        all_cases.append(("Golden v6", c))

    if limit is not None and limit > 0:
        all_cases = all_cases[:limit]

    total = len(all_cases)
    print(f"================================================================")
    print(f" BẮT ĐẦU CHẠY ĐÁNH GIÁ TỔNG HỢP {total} CASES (V5: {len(cases_v5)}, V6: {len(cases_v6)})")
    print(f" Model: {settings.llm_model} | Judge: {'Bỏ qua' if skip_judge else 'Kích hoạt'}")
    print(f"================================================================\n")

    results: list[dict[str, Any]] = []
    install_completion_hooks()
    t_start_all = time.perf_counter()

    try:
        for idx, (ds_name, case) in enumerate(all_cases, 1):
            cid = case.get("id", f"case_{idx}")
            slice_type = (case.get("slice") or {}).get("type", "unknown")
            question = case.get("question", "")

            print(f"[{idx:02d}/{total:02d}] ({ds_name}) {cid} [{slice_type}]: {question[:45]}...", end=" ", flush=True)

            _tracker.reset()
            t0 = time.perf_counter()

            fn = make_answer_fn(
                price_source=cached_price,
                news_source=cached_news,
                history_store=deps.history_store,
                memory_store=deps.memory_store,
                user_id=f"eval-{cid}",
            )

            def tracked_answer_fn(q: str) -> str:
                _tracker.active_stage = "app"
                out = fn(q)
                _tracker.mark_first_token()
                tracked_answer_fn.last_steps = getattr(fn, "last_steps", [])
                return out

            tracked_answer_fn.last_steps = []

            def tracked_chat_parsed(*args, **kwargs):
                _tracker.active_stage = "eval_judge"
                return _hooked_chat_parsed(*args, **kwargs)

            res = eval_one_case(
                case,
                answer_fn=tracked_answer_fn,
                chat_parsed_fn=tracked_chat_parsed,
                agent_eval_parsed_fn=tracked_chat_parsed,
                skip_judge=skip_judge,
                skip_agent_eval=True,
            )

            elapsed = time.perf_counter() - t0
            ttft = (_tracker.first_token_time - t0) if _tracker.first_token_time is not None else elapsed
            ttft = min(ttft, elapsed)

            trace_str = extract_pipeline_trace(res.steps)
            observations_str = extract_observations(res.steps, res.output)
            evaluation_notes = format_evaluation_details(case, res)

            status_str = "PASS" if res.passed else "FAIL"
            print(f"➔ {status_str} ({elapsed:.2f}s | {_tracker.total_tokens} tokens)")

            row_data = {
                "stt": idx,
                "dataset": ds_name,
                "case_id": cid,
                "slice": slice_type,
                "question": question,
                "expected": case.get("expected", ""),
                "answer": res.output,
                "passed": res.passed,
                "status": status_str,
                "pipeline_trace": trace_str,
                "latency_s": round(elapsed, 2),
                "ttft_s": round(ttft, 2),
                "prompt_tokens": _tracker.total_prompt_tokens,
                "completion_tokens": _tracker.total_completion_tokens,
                "total_tokens": _tracker.total_tokens,
                "cost_usd": round(_tracker.total_cost_usd, 6),
                "cost_vnd": round(_tracker.total_cost_vnd, 0),
                "observations": observations_str,
                "evaluation_notes": evaluation_notes,
                "error": res.error,
            }
            results.append(row_data)

            if delay > 0 and idx < total:
                time.sleep(delay)

    finally:
        uninstall_completion_hooks()

    total_time = time.perf_counter() - t_start_all
    passed_count = sum(1 for r in results if r["passed"])
    pass_rate = (passed_count / len(results)) * 100.0 if results else 0.0

    print(f"\n================================================================")
    print(f" HOÀN TẤT: {passed_count}/{len(results)} PASS ({pass_rate:.1f}%) trong {total_time:.1f}s")
    print(f"================================================================\n")
    return results


def export_to_excel(results: list[dict[str, Any]], output_path: Path) -> None:
    """Tạo bảng Excel (.xlsx) chuyên nghiệp với định dạng styling chuẩn mực."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # Sheet 1: Tổng hợp chi tiết
    ws_detail = wb.active
    ws_detail.title = "Tong_Hop_Danh_Gia"
    ws_detail.views.sheetView[0].showGridLines = True

    # Palette màu
    COLOR_HEADER_BG = "1E3A8A"       # Xanh navy đậm
    COLOR_HEADER_TXT = "FFFFFF"      # Trắng
    COLOR_PASS_BG = "D1FAE5"         # Xanh ngọc pastel
    COLOR_PASS_TXT = "065F46"        # Xanh lá đậm
    COLOR_FAIL_BG = "FEE2E2"         # Đỏ pastel
    COLOR_FAIL_TXT = "991B1B"        # Đỏ đậm
    COLOR_ZEBRA_BG = "F8FAFC"        # Xám bạc siêu nhạt
    COLOR_BORDER = "CBD5E1"          # Viền xám

    font_header = Font(name="Arial", size=11, bold=True, color=COLOR_HEADER_TXT)
    font_body = Font(name="Arial", size=10)
    font_bold = Font(name="Arial", size=10, bold=True)
    font_pass = Font(name="Arial", size=10, bold=True, color=COLOR_PASS_TXT)
    font_fail = Font(name="Arial", size=10, bold=True, color=COLOR_FAIL_TXT)

    fill_header = PatternFill(start_color=COLOR_HEADER_BG, end_color=COLOR_HEADER_BG, fill_type="solid")
    fill_pass = PatternFill(start_color=COLOR_PASS_BG, end_color=COLOR_PASS_BG, fill_type="solid")
    fill_fail = PatternFill(start_color=COLOR_FAIL_BG, end_color=COLOR_FAIL_BG, fill_type="solid")
    fill_zebra = PatternFill(start_color=COLOR_ZEBRA_BG, end_color=COLOR_ZEBRA_BG, fill_type="solid")

    thin_border_side = Side(border_style="thin", color=COLOR_BORDER)
    thin_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="top", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="top", wrap_text=True)

    headers = [
        ("STT", 6, align_center),
        ("Dataset", 13, align_center),
        ("Case ID", 16, align_center),
        ("Lát cắt (Slice)", 15, align_center),
        ("Câu hỏi", 38, align_left),
        ("Câu trả lời thực tế", 55, align_left),
        ("Kết quả (Pass/Fail)", 18, align_center),
        ("Pipeline Trace (Chuỗi Agent)", 30, align_left),
        ("Độ trễ (TTFT / E2E)", 18, align_center),
        ("Tokens (P / C / Tot)", 20, align_center),
        ("Chi phí (VNĐ)", 15, align_center),
        ("Chi phí (USD)", 16, align_center),
        ("Observation & Dữ liệu quan sát", 40, align_left),
        ("Đánh giá câu trả lời (Chi tiết tiêu chí)", 50, align_left),
    ]

    # Ghi Header
    for col_idx, (h_name, width, align) in enumerate(headers, 1):
        cell = ws_detail.cell(row=1, column=col_idx, value=h_name)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
        col_letter = get_column_letter(col_idx)
        ws_detail.column_dimensions[col_letter].width = width

    ws_detail.row_dimensions[1].height = 32

    # Ghi Dữ liệu từng dòng
    for row_idx, r in enumerate(results, 2):
        stt = r["stt"]
        ds = r["dataset"]
        cid = r["case_id"]
        sl = r["slice"]
        q = r["question"]
        ans = r["answer"]
        status = r["status"]
        trace = r["pipeline_trace"]
        latency_str = f"{r['ttft_s']:.2f}s / {r['latency_s']:.2f}s"
        tokens_str = f"{r['prompt_tokens']:,} / {r['completion_tokens']:,} ({r['total_tokens']:,})"
        cost_vnd_str = f"{r.get('cost_vnd', 0):,.0f} đ"
        cost_usd_str = f"${r.get('cost_usd', 0):.5f}"
        obs = r["observations"]
        eval_notes = r["evaluation_notes"]

        row_values = [
            (stt, align_center, font_body),
            (ds, align_center, font_bold),
            (cid, align_center, font_body),
            (sl, align_center, font_body),
            (q, align_left, font_body),
            (ans, align_left, font_body),
            (status, align_center, font_pass if r["passed"] else font_fail),
            (trace, align_left, font_body),
            (latency_str, align_center, font_body),
            (tokens_str, align_center, font_body),
            (cost_vnd_str, align_center, font_bold),
            (cost_usd_str, align_center, font_body),
            (obs, align_left, font_body),
            (eval_notes, align_left, font_body),
        ]

        is_even = (row_idx % 2 == 0)
        row_fill = fill_zebra if is_even else None

        for col_idx, (val, align, font) in enumerate(row_values, 1):
            cell = ws_detail.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font
            cell.alignment = align
            cell.border = thin_border
            if col_idx == 7:  # Cột Pass/Fail
                cell.fill = fill_pass if r["passed"] else fill_fail
            elif row_fill:
                cell.fill = row_fill

        ws_detail.row_dimensions[row_idx].height = 48

    ws_detail.freeze_panes = "A2"

    # =========================================================================
    # Sheet 2: Thống kê Dashboard
    # =========================================================================
    ws_dash = wb.create_sheet(title="Tong_Quan_Dashboard")
    ws_dash.views.sheetView[0].showGridLines = True

    title_font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
    section_font = Font(name="Arial", size=11, bold=True, color="0F172A")
    kpi_val_font = Font(name="Arial", size=18, bold=True, color="1E3A8A")
    kpi_sub_font = Font(name="Arial", size=9, color="64748B")

    ws_dash.column_dimensions["A"].width = 5
    ws_dash.column_dimensions["B"].width = 28
    ws_dash.column_dimensions["C"].width = 18
    ws_dash.column_dimensions["D"].width = 18
    ws_dash.column_dimensions["E"].width = 18
    ws_dash.column_dimensions["F"].width = 24

    ws_dash.cell(row=2, column=2, value="BÁO CÁO ĐÁNH GIÁ HỆ THỐNG MULTI-AGENT VN-STOCK-SWARM").font = title_font
    ws_dash.cell(row=3, column=2, value=f"Thời gian đánh giá: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Model: {settings.llm_model}").font = kpi_sub_font

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r["passed"])
    failed_cases = total_cases - passed_cases
    pass_rate = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0

    avg_e2e = sum(r["latency_s"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_ttft = sum(r["ttft_s"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_tokens = sum(r["total_tokens"] for r in results) / total_cases if total_cases > 0 else 0
    total_cost_vnd = sum(r["cost_vnd"] for r in results)
    total_cost_usd = sum(r["cost_usd"] for r in results)

    # Khối KPIs
    kpi_boxes = [
        (5, 2, "TỔNG SỐ TEST CASES", f"{total_cases} cases", "v5 (40) + v6 (20)"),
        (5, 3, "SỐ CASE ĐẠT (PASS)", f"{passed_cases} cases", f"Tỷ lệ: {pass_rate:.1f}%"),
        (5, 4, "SỐ CASE KHÔNG ĐẠT", f"{failed_cases} cases", f"Tỷ lệ: {100-pass_rate:.1f}%"),
        (5, 5, "ĐỘ TRỄ TRUNG BÌNH", f"{avg_e2e:.2f}s", f"TTFT: {avg_ttft:.2f}s"),
        (5, 6, "CHI PHÍ ƯỚC TÍNH", f"{total_cost_vnd:,.0f} đ", f"${total_cost_usd:.4f}"),
    ]

    for r_start, col, title, val, sub in kpi_boxes:
        ws_dash.cell(row=r_start, column=col, value=title).font = Font(name="Arial", size=9, bold=True, color="475569")
        ws_dash.cell(row=r_start + 1, column=col, value=val).font = kpi_val_font
        ws_dash.cell(row=r_start + 2, column=col, value=sub).font = kpi_sub_font
        for r_box in range(r_start, r_start + 3):
            ws_dash.cell(row=r_box, column=col).border = thin_border
            ws_dash.cell(row=r_box, column=col).fill = fill_zebra

    # Bảng Phân rã theo Dataset
    ws_dash.cell(row=9, column=2, value="1. Phân Tích Theo Dataset").font = section_font
    ds_headers = ["Dataset", "Tổng Cases", "Đạt (Pass)", "Không Đạt", "Tỷ lệ Pass %"]
    for c_i, h in enumerate(ds_headers, 2):
        c = ws_dash.cell(row=10, column=c_i, value=h)
        c.font = font_header
        c.fill = fill_header
        c.border = thin_border
        c.alignment = align_center

    row_ds = 11
    for ds_name in ["Golden v5", "Golden v6"]:
        sub_r = [r for r in results if r["dataset"] == ds_name]
        tot_sub = len(sub_r)
        pass_sub = sum(1 for r in sub_r if r["passed"])
        fail_sub = tot_sub - pass_sub
        rate_sub = (pass_sub / tot_sub * 100.0) if tot_sub > 0 else 0.0

        ws_dash.cell(row=row_ds, column=2, value=ds_name).font = font_bold
        ws_dash.cell(row=row_ds, column=3, value=tot_sub).alignment = align_center
        ws_dash.cell(row=row_ds, column=4, value=pass_sub).alignment = align_center
        ws_dash.cell(row=row_ds, column=5, value=fail_sub).alignment = align_center
        ws_dash.cell(row=row_ds, column=6, value=f"{rate_sub:.1f}%").alignment = align_center

        for c_i in range(2, 7):
            ws_dash.cell(row=row_ds, column=c_i).border = thin_border
        row_ds += 1

    # Bảng Phân rã theo Slice Type
    ws_dash.cell(row=row_ds + 1, column=2, value="2. Phân Tích Theo Lát Cắt Nghiệp Vụ (Slice Type)").font = section_font
    sl_row = row_ds + 2
    sl_headers = ["Lát cắt (Slice)", "Tổng Cases", "Đạt (Pass)", "Không Đạt", "Tỷ lệ Pass %"]
    for c_i, h in enumerate(sl_headers, 2):
        c = ws_dash.cell(row=sl_row, column=c_i, value=h)
        c.font = font_header
        c.fill = fill_header
        c.border = thin_border
        c.alignment = align_center

    all_slices = sorted(list(set(r["slice"] for r in results)))
    sl_row += 1
    for sl_name in all_slices:
        sub_sl = [r for r in results if r["slice"] == sl_name]
        tot_sl = len(sub_sl)
        pass_sl = sum(1 for r in sub_sl if r["passed"])
        fail_sl = tot_sl - pass_sl
        rate_sl = (pass_sl / tot_sl * 100.0) if tot_sl > 0 else 0.0

        ws_dash.cell(row=sl_row, column=2, value=sl_name).font = font_body
        ws_dash.cell(row=sl_row, column=3, value=tot_sl).alignment = align_center
        ws_dash.cell(row=sl_row, column=4, value=pass_sl).alignment = align_center
        ws_dash.cell(row=sl_row, column=5, value=fail_sl).alignment = align_center
        c_rate = ws_dash.cell(row=sl_row, column=6, value=f"{rate_sl:.1f}%")
        c_rate.alignment = align_center
        c_rate.font = font_pass if rate_sl == 100.0 else (font_fail if rate_sl < 80.0 else font_bold)

        for c_i in range(2, 7):
            ws_dash.cell(row=sl_row, column=c_i).border = thin_border
        sl_row += 1

    wb.save(output_path)
    print(f"Đã lưu thành công file Excel báo cáo: {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chạy test tổng hợp golden_v5 + golden_v6 và xuất Excel")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số case chạy")
    parser.add_argument("--delay", type=float, default=0.2, help="Độ trễ giữa các case (giây)")
    parser.add_argument("--skip-judge", action="store_true", help="Bỏ qua LLM Judge để chạy siêu tốc")
    default_out_dir = Path("/app/data") if Path("/app/data").is_dir() else (ROOT / "resources" / "eval")
    parser.add_argument(
        "--output-xlsx",
        type=Path,
        default=default_out_dir / "danh_gia_golden_v5_v6.xlsx",
        help="Đường dẫn file Excel đầu ra",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=default_out_dir / "danh_gia_golden_v5_v6.json",
        help="Đường dẫn file JSON đầu ra",
    )

    parser.add_argument(
        "--from-json",
        type=Path,
        default=None,
        help="Đọc dữ liệu từ file JSON có sẵn để render lại Excel nhanh chóng",
    )

    args = parser.parse_args(argv)

    if args.from_json and args.from_json.is_file():
        print(f"Đọc dữ liệu có sẵn từ: {args.from_json}")
        with open(args.from_json, encoding="utf-8") as f:
            results = json.load(f)
    else:
        results = run_all_evaluations(
            limit=args.limit,
            delay=args.delay,
            skip_judge=args.skip_judge,
        )

        # Xuất JSON
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Đã lưu kết quả JSON: {args.output_json}")

    # Xuất Excel
    export_to_excel(results, args.output_xlsx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
