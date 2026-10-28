"""Biến kết quả chạy graph thành steps[] cho timeline UI / trajectory eval."""

from __future__ import annotations

from typing import Any

# Mô tả tĩnh hiển thị trên Live Inspector (không đổi theo request)
_INFO = {
    "guardrail": "[Rule Engine] Regex & Zero-Tolerance Policy: Chặn Prompt Injection, Out-of-scope, Cổ phiếu quốc tế.",
    "refusal": "[Safety Fallback Engine] Phản hồi từ chối chuẩn mực khi câu hỏi vi phạm chính sách an toàn hoặc nằm ngoài phạm vi chứng khoán VN.",
    "greeting": "[Greeting Fast-Path] Phản hồi chào hỏi thân thiện và giới thiệu các năng lực của trợ lý Portfolio Watch.",
    "price": "[Tool Worker] Vnstock API: Truy xuất dữ liệu thời gian thực (giá khớp lệnh, giá đóng cửa close, % biến động và lịch sử giá kỹ thuật).",
    "draw": "[Visualization Worker] DrawAgent: Biểu đồ nến / đường giá / so sánh (Matplotlib) và sơ đồ Mermaid.",
    "gate": "[Human-in-the-Loop] scan_tools thực thi update_watchlist — graph dừng trước node này (interrupt_before) chờ người dùng duyệt.",
    "guardrail_output": "[Output Guardrail] Cấm khuyên mua/bán chắc chắn, số liệu phải khớp evidence; vi phạm → soạn lại (tối đa 3 lượt) hoặc viết lại an toàn.",
    "supervisor": "[LLM Supervisor] chat_supervisor đọc nhiệm vụ + ghi chú worker, chọn worker kế tiếp hoặc 'done'.",
    "portfolio": "[Node] portfolio_watch: Quản lý danh mục nắm giữ, định giá NAV, Unrealized P&L và danh sách theo dõi Watchlist.",
    "answer": "[Final Answer] Tổng hợp task + notes từ worker, stream token (tạm bỏ guardrail_output).",
}

_PROMPT_FALLBACK = {
    "rewrite_question": "[Prompt] Chuẩn hóa câu hỏi, coreference resolution, trích xuất mã cổ phiếu và phân rã ý định.",
    "diagram_plan": "[Diagram Engine] Lên kế hoạch và tạo mã Mermaid biểu diễn luồng quan hệ doanh nghiệp hoặc dữ liệu.",
    "news_agent_react": "[Tool Worker] Vnstock News API / ReAct: Thu thập tin tức doanh nghiệp, sự kiện tài chính, công bố thông tin gần nhất.",
    "eval_severity": "[Risk Engine] Đánh giá mức độ nghiêm trọng (high/medium/low/none) của tin tức và biến động giá đối với doanh nghiệp.",
    "answer_compose": "[Prompt] Tổng hợp câu trả lời dựa trên facts thu thập từ các worker, tuân thủ guardrail tài chính.",
    "event_classification": "[Event Classifier] Phân loại sự kiện định lượng / định tính từ dữ liệu quét biến động thị trường.",
    "synthesis_alert": "[Synthesis Engine] Tổng hợp thông tin từ Price/News/Eval để soạn thảo cảnh báo danh mục đầu tư.",
}


def _registry_prompt(name: str) -> str:
    fallback = _PROMPT_FALLBACK.get(name, name)
    try:
        from ai_backend.infra.llm.prompt_registry import registry

        p = registry().get(name, "production")
        return f"[{p.name} v{p.version} - Model: {p.model}]\n\n{p.template}"
    except Exception:
        return fallback


def _g(obj: Any, key: str, default: Any = None) -> Any:
    return getattr(obj, key, default) if obj is not None else default


class _Steps:
    """Builder nhỏ: append step có id tăng dần."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(
        self,
        name: str,
        status: str,
        detail: str | None = None,
        *,
        input: Any = None,
        output: Any = None,
        duration_s: float | None = None,
        static_info: Any = None,
    ) -> None:
        step: dict[str, Any] = {"id": str(len(self.items) + 1), "name": name, "status": status}
        if duration_s is not None:
            step["duration_s"] = round(float(duration_s), 3)
            step["duration_ms"] = int(round(float(duration_s) * 1000))
        if detail is not None:
            step["detail"] = detail
        if input is not None:
            step["input"] = input
        if static_info is not None:
            step["static_info"] = static_info
        if output is not None:
            step["output"] = output
        self.items.append(step)


_OUT_KEYS = (
    "guardrail_result", "question", "rewritten", "next_agent", "prices", "news", "eval_result", "chart_result",
    "diagram_result", "portfolio_watch_result", "answer", "answer_kind", "event_routing", "symbol", "alert", "messages",
)


def build_steps_from_chunks(
    chunks: list[dict],
    final_error: str | None = None,
    timings: dict[str, float] | None = None,
) -> list[dict]:
    """Build steps[] từ LangGraph stream(stream_mode="updates") — chat và scan."""
    steps = _Steps()
    timings = timings or {}
    last_rewritten = None
    last_symbol: str | None = None
    dur = timings.get

    def handle(node: str, out: dict[str, Any]) -> None:
        nonlocal last_rewritten, last_symbol
        # Update của 1 node chỉ có vài key → mặc định None cho mọi key bên dưới đọc
        out = {**dict.fromkeys(_OUT_KEYS), **(out or {})}

        if node == "guardrail_input":
            res = out["guardrail_result"]
            safe = _g(res, "is_safe", True) if res else True
            cat = _g(res, "category", "safe") if res else "safe"
            reason = _g(res, "reason", "") if res else ""
            steps.add(
                "guardrail_input",
                "done" if safe else "blocked",
                f"{cat}: {reason}",
                input={"question": out["question"]},
                output={"is_safe": safe, "category": cat, "reason": reason},
                duration_s=dur("guardrail_input"),
                static_info=_INFO["guardrail"],
            )

        elif node == "rewrite_question":
            rw = out["rewritten"]
            if not rw:
                return
            last_rewritten, last_symbol = rw, rw.symbol
            steps.add(
                "rewrite_question",
                "done",
                rw.rewritten or rw.original or None,
                input={"question": rw.original or ""},
                output={
                    "rewritten": rw.rewritten or "",
                    "symbol": rw.symbol,
                    "symbols": list(rw.symbols or []),
                },
                duration_s=dur("rewrite_question"),
                static_info=_registry_prompt("rewrite_question"),
            )

        elif node == "chat_supervisor":
            nxt = out["next_agent"]
            if not nxt:
                return
            q = _g(last_rewritten, "rewritten") or _g(last_rewritten, "original") or ""
            steps.add(
                "supervisor",
                "done",
                f"→ {nxt}",
                input={"question": q},
                output={"next_agent": nxt},
                duration_s=dur("chat_supervisor"),
                static_info=_INFO["supervisor"],
            )

        elif node == "price_agent":
            prices = out["prices"] or []
            w_dur = dur("price_agent")
            for p in prices:
                if p is None:
                    continue
                err = f" err={p.error}" if p.error else ""
                steps.add(
                    "price_agent",
                    "error" if p.error else "done",
                    f"{p.symbol} close={p.latest_close} chg={p.change_pct}{err}",
                    input={"symbol": p.symbol},
                    output={
                        "symbol": p.symbol,
                        "latest_close": p.latest_close,
                        "change_pct": p.change_pct,
                        "error": p.error,
                    },
                    duration_s=w_dur,
                    static_info=_INFO["price"],
                )

        elif node == "news_agent":
            news_list = out["news"] or []
            w_dur = dur("news_agent")
            info = _registry_prompt("news_agent_react")
            for item in news_list:
                if item is None:
                    continue
                sym = _g(item, "symbol") or last_symbol or ""
                err = f" err={item.error}" if item.error else ""
                n_items = len(item.items or [])
                steps.add(
                    "news_agent",
                    "error" if item.error else "done",
                    f"items={n_items}{err}",
                    input={"symbol": sym},
                    output={"symbol": sym, "items_count": n_items, "error": item.error},
                    duration_s=w_dur,
                    static_info=info,
                )

        elif node == "eval_agent":
            ev = out["eval_result"]
            if ev is None:
                return
            sym = _g(ev, "symbol") or last_symbol or ""
            steps.add(
                "eval_agent",
                "done",
                str(ev.severity),
                input={"symbol": sym},
                output={
                    "severity": str(ev.severity),
                    "confidence": _g(ev.severity, "confidence"),
                },
                duration_s=dur("eval_agent"),
                static_info=_registry_prompt("eval_severity"),
            )

        elif node == "draw_agent":
            chart, diagram = out["chart_result"], out["diagram_result"]
            if diagram is not None:
                steps.add(
                    "draw_agent",
                    "done",
                    "diagram rendered",
                    input={"kind": "diagram", "symbol": last_symbol or ""},
                    output={
                        "diagram_pending": _g(diagram, "diagram_pending", True),
                        "mermaid": _g(diagram, "mermaid"),
                        "graph_json": _g(diagram, "graph_json"),
                    },
                    duration_s=dur("draw_agent"),
                    static_info=_registry_prompt("diagram_plan"),
                )
            if chart is not None:
                url, err = _g(chart, "url"), _g(chart, "error")
                syms = _g(chart, "symbols") or ([last_symbol] if last_symbol else [])
                steps.add(
                    "draw_agent",
                    "done" if _g(chart, "success", True) else "error",
                    url or (f"err={err}" if err else "chart generated"),
                    input={"kind": "chart", "symbols": syms},
                    output={
                        "success": _g(chart, "success", True),
                        "url": url,
                        "chart_type": _g(chart, "chart_type", "price_history"),
                        "error": err,
                    },
                    duration_s=dur("draw_agent"),
                    static_info=_INFO["draw"],
                )

        elif node == "portfolio_watch":
            pw = out["portfolio_watch_result"]
            if pw is None:
                return
            nav = pw["summary"]["total_nav"] if pw["summary"] else None
            wl_cnt = len(pw["watchlist"])
            detail = f"intent={pw['intent']}"
            if nav is not None:
                detail += f" NAV={nav:,.0f} VND"
            if wl_cnt:
                detail += f" watchlist={wl_cnt} mã"
            steps.add(
                "portfolio_watch",
                "error" if pw["error"] else "done",
                detail,
                input={"user_id": pw["user_id"], "intent": pw["intent"]},
                output={"total_nav": nav, "watchlist_count": wl_cnt, "error": pw["error"]},
                duration_s=dur("portfolio_watch"),
                static_info=_INFO["portfolio"],
            )

        elif node == "answer":
            ans = out["answer"] or ""
            kind = out["answer_kind"] or "final_answer"
            info = {
                "refusal": _INFO["refusal"],
                "greeting": _INFO["greeting"],
            }.get(kind) or _INFO["answer"] or "[Answer] Tổng hợp task + notes (stream)."
            steps.add(
                "answer",
                "done",
                f"[{kind}] {ans[:200]}" if ans else f"[{kind}]",
                input={"kind": kind, "symbol": last_symbol},
                output={"answer": ans[:300]},
                duration_s=dur("answer"),
                static_info=info,
            )

        elif node == "event_classifier":
            routing = out["event_routing"]
            if not routing:
                return
            route = str(getattr(routing.route, "value", routing.route))
            reason = f" — {routing.reason}" if routing.reason else ""
            steps.add(
                "event_classifier",
                "done",
                f"{route}{reason}",
                input={"symbol": out["symbol"] or ""},
                output={"route": route, "reason": routing.reason or ""},
                duration_s=dur("event_classifier"),
                static_info=_registry_prompt("event_classification"),
            )

        elif node == "synthesis_agent":
            alert = out["alert"]
            if not alert:
                return
            steps.add(
                "synthesis_agent",
                "done",
                "alert composed",
                input={"symbol": _g(alert, "symbol", "")},
                output={
                    "alert_id": _g(alert, "id"),
                    "title": _g(alert, "title", ""),
                    "status": str(_g(alert, "status", "")),
                },
                duration_s=dur("synthesis_agent"),
                static_info=_registry_prompt("synthesis_alert"),
            )

        elif node == "scan_tools":
            # Chỉ có chunk khi người dùng ĐÃ DUYỆT (tool chạy thật); từ chối thì ToolMessage chèn qua update_state
            for msg in out["messages"] or []:
                steps.add(
                    "scan_tools",
                    "done",
                    f"{msg.name}: {msg.content}",
                    input={"tool": msg.name},
                    output={"result": str(msg.content)},
                    duration_s=dur("scan_tools"),
                    static_info=_INFO["gate"],
                )

    for chunk in chunks:
        for node_name, output in chunk.items():
            handle(node_name, output or {})

    if final_error:
        is_scan = any("event_classifier" in c for c in chunks if isinstance(c, dict))
        steps.add(
            "scan" if is_scan else "chat",
            "error",
            final_error,
            input={"error": final_error},
            output={"error": final_error},
        )
    return steps.items

